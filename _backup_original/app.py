# -*- coding: utf-8 -*-
"""
HỆ THỐNG ĐIỀU PHỐI & TỐI ƯU TUYẾN — HÒA PHÁT LOGISTICS (app.py)
==============================================================
Trung tâm điều phối web động (Control Tower) gồm 8 module:
  1. Nhập dữ liệu & ánh xạ      5. Tài chính P&L
  2. Kiểm định dữ liệu          6. Phát hiện sự cố & xử lý case động
  3. Kế hoạch tuyến & bản đồ    7. Nhật ký & lưu vết
  4. Ghép chuyến quay đầu       8. Trợ lý điều phối AI (Gemini)

Phân tách rõ:
  • Routing/optimization engine (hpl_engine.py, engine_ext.py): gán xe, lập tuyến,
    tính chi phí, xử lý ràng buộc vận hành.
  • AI tạo sinh Gemini (gemini_ai.py): đọc/ánh xạ dữ liệu, giải thích, trợ lý hỏi đáp.

Chạy:
    pip install -r requirements.txt
    python app.py
    Mở http://localhost:8000
"""

import os
import json
from datetime import datetime


# --- Nạp biến môi trường từ file .env (không cần thư viện ngoài) ---
def _load_dotenv():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k, v = k.strip(), v.strip().strip('"').strip("'")
                if k and k not in os.environ:
                    os.environ[k] = v
    except Exception:
        pass


_load_dotenv()

from flask import Flask, render_template, request, jsonify, send_file

import hpl_engine as eng
import engine_ext as ext
import gemini_ai as ai
import excel_report as report

BASE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE, "data")
LOG_PATH = os.path.join(DATA_DIR, "incident_log.json")
DEMO_STATIC = os.path.join(DATA_DIR, "1. HPL_AI_Dispatching_Simulated_Data_VRPTW.xlsx")
DEMO_DYNAMIC = os.path.join(DATA_DIR, "2. HPL_AI_Dispatching_Dynamic_Cases_VRPTW.xlsx")

app = Flask(__name__)
app.secret_key = "hpl-dispatching-2026"
app.config["MAX_CONTENT_LENGTH"] = 32 * 1024 * 1024

STORE = {
    "static": None, "dynamic": None,
    "working": {},                # {sid: [order dict]} bản làm việc, sửa trực tiếp
    "new_backhaul_orders": [],     # đơn bổ sung cho chuyến quay đầu
    "_routes": None, "_unassigned": None, "_scenario": None,
    "_financial": None, "_backhaul_gain": 0,
    "_preset": "can_bang", "_weights": ext.preset_weights("can_bang"), "_radius": 30,
    "incidents": [],               # sự cố đang theo dõi
    "constraints": ext.load_constraints(),
    "_inc_seq": 0,
}
ext.apply_constraints(STORE["constraints"])


# ============================================================
# Tiện ích lưu vết (Module 7)
# ============================================================
def _load_log():
    try:
        with open(LOG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _save_log(log):
    try:
        with open(LOG_PATH, "w", encoding="utf-8") as f:
            json.dump(log, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def _append_log(entry):
    log = _load_log()
    entry.setdefault("ts", datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
    entry.setdefault("user", "Điều phối viên")
    log.insert(0, entry)
    _save_log(log)
    return entry


# ============================================================
# Bản làm việc của đơn hàng (cho phép sửa trực tiếp)
# ============================================================
def _working_orders(sid):
    """Trả về bản làm việc của kịch bản — sao chép từ dữ liệu gốc lần đầu truy cập."""
    d = STORE["static"]
    if not d:
        return None, None
    if not sid or sid not in d["scenarios"]:
        sid = next(iter(d["scenarios"]), None)
    if sid is None:
        return [], None
    if sid not in STORE["working"]:
        STORE["working"][sid] = [dict(o) for o in d["scenarios"][sid]]
    return STORE["working"][sid], sid


EDITABLE_NUM = {"weight_kg", "volume_m3", "revenue", "direct_km",
                "pickup_lat", "pickup_lon", "delivery_lat", "delivery_lon",
                "drop_tw_start", "drop_tw_end", "pickup_tw_start", "pickup_tw_end"}


# ============================================================
# Auto-load dữ liệu mẫu khi khởi động
# ============================================================
def _autoload():
    for path, kind in [(DEMO_STATIC, "static"), (DEMO_DYNAMIC, "dynamic")]:
        try:
            if os.path.exists(path):
                with open(path, "rb") as f:
                    STORE[kind] = eng.parse_workbook(f.read())["data"]
        except Exception as e:
            print("autoload error:", kind, e)


_autoload()


# ============================================================
# Trang chính + trạng thái
# ============================================================
@app.route("/")
def index():
    return render_template("dashboard.html")


@app.route("/api/status")
def api_status():
    d = STORE["static"]; dy = STORE["dynamic"]
    st = ai.ai_status()
    return jsonify({
        "static_loaded": d is not None,
        "dynamic_loaded": dy is not None,
        "scenarios": (list(d["scenarios"].keys()) if d else []),
        "fleet": (len(d["fleet"]) if d else 0),
        "dynamic_cases": (len(dy["cases"]) if dy else 0),
        "ai_provider": st["provider"], "ai_online": st["online"],
        "log_count": len(_load_log()),
        "incident_count": len([i for i in STORE["incidents"] if i.get("status") != "Hoàn tất"]),
        "constraint_window": ext.constraint_window_text(STORE["constraints"]),
        "presets": [{"key": k, "ten": v["ten"]} for k, v in ext.PRESETS.items()],
        "preset": STORE["_preset"], "weights": STORE["_weights"], "radius": STORE["_radius"],
        "backhaul_orders": len(STORE["new_backhaul_orders"]),
    })


# ============================================================
# MODULE 1 — Nhập dữ liệu & ánh xạ
# ============================================================
def _import_payload(parsed, filename):
    d = parsed["data"]
    if parsed["kind"] == "static":
        STORE["static"] = d
        STORE["working"] = {}
        scenarios = {sid: len(o) for sid, o in d["scenarios"].items()}
        headers = d.get("raw_order_headers") or []
        match = ai.map_columns(headers)
        return {
            "kind": "static", "filename": filename,
            "fleet": len(d["fleet"]), "scenarios": scenarios,
            "depots": len(d["depots"]), "zones": len(d["zones"]),
            "ai_mapping": match["mapping"], "ai_source": match["source"],
            "ai_matched": match.get("matched"), "ai_total": match.get("total"),
            "message": (f"Đã nạp dữ liệu tĩnh: {len(d['fleet'])} xe, "
                        f"{sum(scenarios.values())} đơn ({len(scenarios)} kịch bản)."),
        }
    else:
        STORE["dynamic"] = d
        return {
            "kind": "dynamic", "filename": filename,
            "cases": len(d["cases"]), "vehicles": len(d["vehicles"]),
            "candidates": len(d["candidates"]), "orders_live": len(d["orders"]),
            "ai_mapping": {}, "ai_source": "—",
            "message": (f"Đã nạp dữ liệu động: {len(d['cases'])} case sự cố, "
                        f"{len(d['vehicles'])} xe đang hoạt động."),
        }


@app.route("/api/import", methods=["POST"])
def api_import():
    if "file" not in request.files:
        return jsonify({"error": "Chưa chọn file Excel để tải lên."}), 400
    f = request.files["file"]
    if not f.filename.lower().endswith((".xlsx", ".xlsm")):
        return jsonify({"error": "Định dạng phải là .xlsx hoặc .xlsm."}), 400
    kind_hint = request.form.get("kind", "auto")
    try:
        raw = f.read()
        parsed = eng.parse_workbook(raw)
    except Exception as e:
        return jsonify({"error": f"Không đọc được file Excel: {e}"}), 500
    # File đơn bổ sung quay đầu: dùng schema tĩnh nhưng nạp vào danh sách backhaul
    if kind_hint == "backhaul" and parsed["kind"] == "static":
        added = _ingest_backhaul_from_static(parsed["data"])
        return jsonify({"kind": "backhaul", "filename": f.filename,
                        "added": added, "total": len(STORE["new_backhaul_orders"]),
                        "message": f"Đã nạp {added} đơn bổ sung cho chuyến quay đầu."})
    return jsonify(_import_payload(parsed, f.filename))


def _ingest_backhaul_from_static(d):
    added = 0
    for sid, orders in d.get("scenarios", {}).items():
        for o in orders:
            if o.get("pickup_lat") and o.get("delivery_lat"):
                STORE["new_backhaul_orders"].append({
                    "order_id": o.get("order_id"), "customer": o.get("customer"),
                    "pickup_name": o.get("pickup_name"), "delivery_name": o.get("delivery_name"),
                    "pickup_lat": o.get("pickup_lat"), "pickup_lon": o.get("pickup_lon"),
                    "delivery_lat": o.get("delivery_lat"), "delivery_lon": o.get("delivery_lon"),
                    "weight_kg": o.get("weight_kg"), "volume_m3": o.get("volume_m3"),
                    "min_vehicle": o.get("min_vehicle"), "revenue": o.get("revenue"),
                    "inner_city": o.get("inner_city"),
                    "drop_tw_start": o.get("drop_tw_start"), "drop_tw_end": o.get("drop_tw_end"),
                    "source": "Excel bổ sung",
                })
                added += 1
    return added


@app.route("/api/load_demo", methods=["POST"])
def api_load_demo():
    out = {}
    if os.path.exists(DEMO_STATIC):
        with open(DEMO_STATIC, "rb") as f:
            out["static"] = _import_payload(eng.parse_workbook(f.read()), os.path.basename(DEMO_STATIC))
    if os.path.exists(DEMO_DYNAMIC):
        with open(DEMO_DYNAMIC, "rb") as f:
            out["dynamic"] = _import_payload(eng.parse_workbook(f.read()), os.path.basename(DEMO_DYNAMIC))
    return jsonify(out)


@app.route("/api/preview")
def api_preview():
    sid = request.args.get("scenario", "")
    orders, sid = _working_orders(sid)
    if orders is None:
        return jsonify({"error": "Chưa nạp dữ liệu tĩnh."}), 400
    cols = [
        ("order_id", "Mã đơn"), ("customer", "Khách hàng"), ("corridor", "Hành lang"),
        ("pickup_name", "Điểm lấy"), ("delivery_name", "Điểm trả"),
        ("weight_kg", "KL (kg)"), ("volume_m3", "Thể tích (m³)"),
        ("min_vehicle", "Loại xe"), ("priority", "Ưu tiên"),
        ("drop_tw_start", "Giao từ"), ("drop_tw_end", "Giao đến"),
        ("revenue", "Doanh thu"), ("note", "Ghi chú điều phối"),
    ]
    rows = []
    for o in orders:
        row = {k: o.get(k) for k, _ in cols}
        row["drop_tw_start"] = eng.min_to_hhmm(o.get("drop_tw_start"))
        row["drop_tw_end"] = eng.min_to_hhmm(o.get("drop_tw_end"))
        rows.append(row)
    return jsonify({"scenario": sid, "columns": cols, "rows": rows})


@app.route("/api/order/update", methods=["POST"])
def api_order_update():
    p = request.get_json(silent=True) or {}
    sid = p.get("scenario")
    orders, sid = _working_orders(sid)
    if orders is None:
        return jsonify({"error": "Chưa nạp dữ liệu tĩnh."}), 400
    o = next((x for x in orders if str(x.get("order_id")) == str(p.get("order_id"))), None)
    if not o:
        return jsonify({"error": "Không tìm thấy đơn."}), 404
    field, value = p.get("field"), p.get("value")
    if field in ("drop_tw_start", "drop_tw_end", "pickup_tw_start", "pickup_tw_end"):
        o[field] = eng.time_to_min(value)
    elif field in EDITABLE_NUM:
        o[field] = eng._f(value)
    else:
        o[field] = value
    _append_log({"case_id": "EDIT", "source": "Chỉnh sửa thủ công", "order_id": o.get("order_id"),
                 "event_type": "Cập nhật dữ liệu đơn", "decision": f"Sửa {field} = {value}",
                 "vehicle": "—", "status": "Đã cập nhật", "note": p.get("note", "")})
    return jsonify({"ok": True})


@app.route("/api/order/add", methods=["POST"])
def api_order_add():
    p = request.get_json(silent=True) or {}
    sid = p.get("scenario")
    orders, sid = _working_orders(sid)
    if orders is None:
        return jsonify({"error": "Chưa nạp dữ liệu tĩnh."}), 400
    o = eng._norm_static_order({
        "Order_ID": p.get("order_id") or f"M{datetime.now().strftime('%H%M%S')}",
        "Customer_Name": p.get("customer"), "Corridor": p.get("corridor"),
        "Pickup_Name": p.get("pickup_name"), "Delivery_Name": p.get("delivery_name"),
        "Pickup_Lat": p.get("pickup_lat"), "Pickup_Lon": p.get("pickup_lon"),
        "Delivery_Lat": p.get("delivery_lat"), "Delivery_Lon": p.get("delivery_lon"),
        "Weight_kg": p.get("weight_kg"), "Volume_m3": p.get("volume_m3"),
        "Min_Vehicle_Type": p.get("min_vehicle"), "Freight_Revenue_VND": p.get("revenue"),
        "Drop_TW_Start": p.get("drop_tw_start"), "Drop_TW_End": p.get("drop_tw_end"),
        "Customer_Priority": p.get("priority"),
    })
    orders.append(o)
    _append_log({"case_id": "ADD", "source": "Nhập thủ công", "order_id": o.get("order_id"),
                 "event_type": "Thêm đơn mới", "decision": "Thêm đơn nhập tay",
                 "vehicle": "—", "status": "Đã thêm"})
    return jsonify({"ok": True, "order_id": o.get("order_id")})


@app.route("/api/order/delete", methods=["POST"])
def api_order_delete():
    p = request.get_json(silent=True) or {}
    orders, sid = _working_orders(p.get("scenario"))
    if orders is None:
        return jsonify({"error": "Chưa nạp dữ liệu tĩnh."}), 400
    before = len(orders)
    STORE["working"][sid] = [o for o in orders if str(o.get("order_id")) != str(p.get("order_id"))]
    return jsonify({"ok": True, "removed": before - len(STORE["working"][sid])})


# ============================================================
# MODULE 2 — Kiểm định dữ liệu & năng lực
# ============================================================
def _validated(sid):
    orders, sid = _working_orders(sid)
    if orders is None:
        return None, None, None
    validated = eng.validate_orders(orders)
    return validated, sid, orders


@app.route("/api/validate")
def api_validate():
    sid = request.args.get("scenario", "")
    validated, sid, _ = _validated(sid)
    if validated is None:
        return jsonify({"error": "Chưa nạp dữ liệu tĩnh. Hãy nhập dữ liệu ở Module 1."}), 400
    d = STORE["static"]
    cap = eng.capacity_scenario(validated, d["fleet"], d.get("solutions"), sid)
    n_err = sum(1 for o in validated if o["computed_status"] == "ERROR")
    n_rev = sum(1 for o in validated if o["computed_status"] == "REVIEW")
    summary = {"total_orders": len(validated), "error_orders": n_err, "review_orders": n_rev,
               "scenario": cap["scenario"]}
    narrative = ai.summarize_data(summary)
    rows = [{
        "order_id": o["order_id"], "customer": o["customer"], "corridor": o["corridor"],
        "weight_kg": o["weight_kg"], "volume_m3": o["volume_m3"],
        "min_vehicle": o["min_vehicle"], "priority": o["priority"],
        "inner_city": o["inner_city"], "revenue": o["revenue"],
        "pickup_name": o["pickup_name"], "delivery_name": o["delivery_name"],
        "pickup_lat": o["pickup_lat"], "pickup_lon": o["pickup_lon"],
        "delivery_lat": o["delivery_lat"], "delivery_lon": o["delivery_lon"],
        "drop_tw": f"{eng.min_to_hhmm(o['drop_tw_start'])}-{eng.min_to_hhmm(o['drop_tw_end'])}",
        "status": ext.lifecycle_status(o), "raw_status": o["computed_status"],
        "issues": o["issues"], "note": o.get("note", ""),
        "incident_hint": o["incident_hint"],
    } for o in validated]
    return jsonify({"scenario": cap, "summary": summary, "orders": rows,
                    "ai_narrative": narrative["text"], "ai_source": narrative["source"]})


# ============================================================
# MODULE 3 — Kế hoạch tuyến & bản đồ
# ============================================================
@app.route("/api/optimize", methods=["POST"])
def api_optimize():
    p = request.get_json(silent=True) or {}
    sid = p.get("scenario", "")
    preset = p.get("preset", STORE["_preset"])
    weights = p.get("weights") or ext.preset_weights(preset)
    radius = eng._f(p.get("radius", STORE["_radius"]), 30)
    STORE["_preset"], STORE["_weights"], STORE["_radius"] = preset, weights, radius

    validated, sid, _ = _validated(sid)
    if validated is None:
        return jsonify({"error": "Chưa nạp dữ liệu tĩnh."}), 400
    d = STORE["static"]
    routes, unassigned = ext.solve_preset(validated, d["fleet"], d.get("depots"), weights, radius)
    if not routes:
        # fallback dùng VRPTW lõi (OR-Tools/greedy) nếu preset không xếp được
        res = eng.solve_vrptw(validated, d["fleet"], d.get("depots"))
        routes, unassigned = res.get("routes", []), res.get("unassigned", [])
    # tính P&L gắn vào từng tuyến để dùng cho bản đồ & trợ lý
    fin = ext.financials_detailed(routes, d["fleet"], _fin_params())
    pnl_map = {pp["vehicle_id"]: pp for pp in fin["per_route"]}
    for r in routes:
        r["pnl"] = pnl_map.get(r["vehicle_id"], {})

    STORE["_routes"], STORE["_unassigned"], STORE["_scenario"] = routes, unassigned, sid

    routes_out = []
    for r in routes:
        pnl = r.get("pnl", {})
        routes_out.append({
            "vehicle_id": r["vehicle_id"], "plate": r.get("plate"),
            "vehicle_type": r["vehicle_type"], "driver": r.get("driver"),
            "corridor": r.get("corridor"), "n_orders": r["n_orders"],
            "orders": r["orders"], "distance_km": r["distance_km"],
            "total_weight": r["total_weight"], "total_volume": r["total_volume"],
            "fill_weight_pct": r["fill_weight_pct"], "fill_volume_pct": r["fill_volume_pct"],
            "revenue": pnl.get("revenue_total"), "cost": pnl.get("total_cost"),
            "profit": pnl.get("profit"), "margin": pnl.get("margin"),
            "risk_late": pnl.get("risk_late"),
            "stops": r["stops"],
        })
    una = _unassigned_rows(unassigned, d["fleet"])
    return jsonify({"engine": "Routing engine (gán theo preset trọng số)",
                    "scenario": sid, "preset": preset, "weights": weights,
                    "n_vehicles_used": len(routes),
                    "n_orders_assigned": sum(r["n_orders"] for r in routes),
                    "n_orders_total": len(validated),
                    "n_unassigned": len(unassigned),
                    "routes": routes_out, "unassigned": una})


def _unassigned_rows(unassigned, fleet):
    out = []
    for o in unassigned:
        reason, sug = ext.unassigned_reason(o, fleet)
        out.append({
            "order_id": o["order_id"], "pickup_name": o.get("pickup_name"),
            "delivery_name": o.get("delivery_name"),
            "pickup_lat": o.get("pickup_lat"), "pickup_lon": o.get("pickup_lon"),
            "delivery_lat": o.get("delivery_lat"), "delivery_lon": o.get("delivery_lon"),
            "tw": f"{eng.min_to_hhmm(o.get('drop_tw_start'))}-{eng.min_to_hhmm(o.get('drop_tw_end'))}",
            "weight_kg": o.get("weight_kg"), "min_vehicle": o.get("min_vehicle"),
            "reason": reason, "suggestion": sug, "incident_hint": o.get("incident_hint"),
        })
    return out


@app.route("/api/map_data")
def api_map_data():
    d = STORE["static"]
    if not d:
        return jsonify({"depots": [], "routes": [], "unassigned": []})
    depots = [{"name": dp["name"], "lat": dp["lat"], "lon": dp["lon"],
               "type": dp["type"], "province": dp["province"]} for dp in d["depots"]]
    palette = ["#0B3D91", "#E2231A", "#1B7A2F", "#B8860B", "#6A1B9A", "#0277BD",
               "#C2185B", "#00838F", "#5D4037", "#455A64", "#283593", "#AD1457"]
    routes = []
    for i, r in enumerate(STORE.get("_routes") or []):
        routes.append({
            "vehicle_id": r["vehicle_id"], "vehicle_type": r["vehicle_type"],
            "driver": r.get("driver"), "corridor": r.get("corridor"),
            "color": palette[i % len(palette)], "n_orders": r["n_orders"],
            "distance_km": r["distance_km"], "orders": r.get("orders"),
            "risk_late": (r.get("pnl") or {}).get("risk_late"),
            "stops": [{"type": s["type"], "name": s.get("name"), "lat": s["lat"],
                       "lon": s["lon"], "order_id": s.get("order_id")} for s in r["stops"]],
        })
    una = []
    for o in (STORE.get("_unassigned") or []):
        reason, _ = ext.unassigned_reason(o, d["fleet"])
        if o.get("delivery_lat"):
            una.append({"order_id": o["order_id"], "lat": o["delivery_lat"],
                        "lon": o["delivery_lon"], "name": o.get("delivery_name"),
                        "reason": reason})
    return jsonify({"depots": depots, "routes": routes, "unassigned": una,
                    "scenario": STORE.get("_scenario")})


# ============================================================
# MODULE 4 — Ghép chuyến quay đầu (từ đơn bổ sung MỚI)
# ============================================================
@app.route("/api/backhaul/orders", methods=["GET", "POST", "DELETE"])
def api_backhaul_orders():
    if request.method == "POST":
        p = request.get_json(silent=True) or {}
        STORE["new_backhaul_orders"].append({
            "order_id": p.get("order_id") or f"BK{datetime.now().strftime('%H%M%S')}",
            "customer": p.get("customer"),
            "pickup_name": p.get("pickup_name"), "delivery_name": p.get("delivery_name"),
            "pickup_lat": eng._f(p.get("pickup_lat")), "pickup_lon": eng._f(p.get("pickup_lon")),
            "delivery_lat": eng._f(p.get("delivery_lat")), "delivery_lon": eng._f(p.get("delivery_lon")),
            "weight_kg": eng._f(p.get("weight_kg")), "volume_m3": eng._f(p.get("volume_m3")),
            "min_vehicle": p.get("min_vehicle"), "revenue": eng._f(p.get("revenue")),
            "inner_city": bool(p.get("inner_city")),
            "drop_tw_start": eng.time_to_min(p.get("drop_tw_start"), 0),
            "drop_tw_end": eng.time_to_min(p.get("drop_tw_end"), 1440),
            "source": "Nhập thủ công",
        })
        return jsonify({"ok": True, "total": len(STORE["new_backhaul_orders"])})
    if request.method == "DELETE":
        oid = (request.get_json(silent=True) or {}).get("order_id")
        STORE["new_backhaul_orders"] = [o for o in STORE["new_backhaul_orders"]
                                        if str(o.get("order_id")) != str(oid)]
        return jsonify({"ok": True, "total": len(STORE["new_backhaul_orders"])})
    return jsonify({"orders": STORE["new_backhaul_orders"]})


@app.route("/api/backhaul")
def api_backhaul():
    d = STORE["static"]
    routes = STORE.get("_routes")
    if not d or not routes:
        return jsonify({"error": "Hãy chạy Kế hoạch tuyến (Module 3) trước."}), 400
    if not STORE["new_backhaul_orders"]:
        return jsonify({"results": [], "n_matched": 0, "total_gain": 0,
                        "empty_km_avoided": 0, "n_new_orders": 0, "n_routes": len(routes),
                        "message": "Chưa có đơn bổ sung. Hãy thêm đơn ghép chiều về ở khối bên trái."})
    res = ext.backhaul_new_orders(routes, STORE["new_backhaul_orders"], d["fleet"],
                                  _fin_params(), r_pickup=STORE["_radius"] or 30)
    return jsonify(res)


@app.route("/api/backhaul/accept", methods=["POST"])
def api_backhaul_accept():
    p = request.get_json(silent=True) or {}
    STORE["_backhaul_gain"] = eng._f(p.get("gain"))
    _append_log({"case_id": "BACKHAUL", "source": "Ghép chuyến quay đầu",
                 "order_id": p.get("order_id", "—"), "event_type": "Ghép chiều về",
                 "decision": f"Chấp nhận ghép đơn {p.get('order_id','')} cho xe {p.get('vehicle_id','')}",
                 "vehicle": p.get("vehicle_id", "—"), "status": "Đã áp dụng",
                 "note": f"Lợi nhuận bổ sung ~{int(eng._f(p.get('gain'))):,}đ".replace(",", ".")})
    return jsonify({"ok": True, "backhaul_gain": STORE["_backhaul_gain"]})


# ============================================================
# MODULE 5 — Tài chính P&L
# ============================================================
def _fin_params(override=None):
    pr = dict(ext.DEFAULT_PARAMS)
    if STORE["static"]:
        pr["gia_nhien_lieu"] = eng._f(STORE["static"]["cost"].get("Diesel_Price"), pr["gia_nhien_lieu"])
    if override:
        for k, v in override.items():
            if v is not None and k in pr:
                pr[k] = eng._f(v)
    return pr


def _incident_costs():
    """Tổng hợp chi phí phát sinh từ các sự cố đã chốt phương án."""
    costs = []
    for inc in STORE["incidents"]:
        if inc.get("cost_breakdown"):
            costs.append(inc["cost_breakdown"])
    return costs


@app.route("/api/financial", methods=["POST"])
def api_financial():
    d = STORE["static"]
    routes = STORE.get("_routes")
    if not d or not routes:
        return jsonify({"error": "Hãy chạy Kế hoạch tuyến (Module 3) trước khi tính tài chính."}), 400
    params = _fin_params((request.get_json(silent=True) or {}).get("params"))
    res = ext.financials_detailed(routes, d["fleet"], params,
                                  incident_costs=_incident_costs(),
                                  backhaul_gain=STORE.get("_backhaul_gain", 0))
    # gắn lại pnl vào route cho bản đồ/trợ lý
    pnl_map = {pp["vehicle_id"]: pp for pp in res["per_route"]}
    for r in routes:
        r["pnl"] = pnl_map.get(r["vehicle_id"], r.get("pnl"))
    STORE["_financial"] = res
    orders, _ = _working_orders(STORE.get("_scenario"))
    base = ext.baseline_margin(eng.validate_orders(orders or []), d["fleet"], d.get("depots"), params)
    res["baseline_margin"] = base
    res["uplift_pp"] = round(res["totals"]["margin"] - base, 1)
    return jsonify({"financial": res, "params": params})


# ============================================================
# MODULE 6 — Phát hiện sự cố & xử lý case động
# ============================================================
def _live_fleet():
    dy = STORE["dynamic"]; d = STORE["static"]
    if dy and dy["vehicles"]:
        live = [{**v, "remain_ton": v.get("remain_ton", v.get("max_ton", 0)),
                 "remain_m3": v.get("remain_m3", v.get("max_m3", 0))} for v in dy["vehicles"]]
        return live, dy["params"]
    if d:
        live = [{"vehicle_id": v["vehicle_id"], "vehicle_type": v["vehicle_type"],
                 "lat": v["lat"], "lon": v["lon"], "driver": v.get("driver_name"),
                 "status": v.get("status", "Available"),
                 "max_ton": v["max_weight_kg"] / 1000.0, "max_m3": v["max_volume_m3"],
                 "remain_ton": v["max_weight_kg"] / 1000.0, "remain_m3": v["max_volume_m3"],
                 "can_reroute": True} for v in d["fleet"]]
        return live, {"Search_Radius_Min": 0, "Search_Radius_Max": STORE["_radius"] or 30,
                      "Average_Recovery_Speed": 35, "Transfer_Service_Time": 20}
    return [], {}


@app.route("/api/incident/from_order", methods=["POST"])
def api_incident_from_order():
    p = request.get_json(silent=True) or {}
    order_id = p.get("order_id")
    event_type = p.get("event_type")
    sid = p.get("scenario") or STORE.get("_scenario")
    validated, sid, _ = _validated(sid)
    if validated is None:
        return jsonify({"error": "Chưa nạp dữ liệu tĩnh."}), 400
    o = next((x for x in validated if str(x["order_id"]) == str(order_id)), None)
    if not o:
        return jsonify({"error": f"Không tìm thấy đơn {order_id}."}), 404

    live, params = _live_fleet()
    params = dict(params)
    params["Search_Radius_Min"] = 0
    params["Search_Radius_Max"] = STORE["_radius"] or 30
    incident = eng.incident_from_static_order(o, live, params)
    if event_type:
        incident["event_type"] = event_type
    et = incident["event_type"]
    rec = incident.get("recommended_vehicle")
    opt = ext.incident_options(et, {
        "rec_vehicle": (rec["vehicle"] if rec else None),
        "dist_km": (rec["dist_km"] if rec else 0),
        "eta_min": (rec["eta_min"] if rec else 35),
    })
    analysis = ai.incident_analysis(
        {"order_id": order_id, "event_type": et, "customer": incident.get("customer"),
         "delivery_name": incident.get("delivery_name"), "corridor": incident.get("corridor")},
        opt["options"])

    STORE["_inc_seq"] += 1
    case_id = f"SC-{datetime.now().strftime('%H%M%S')}-{STORE['_inc_seq']}"
    # tuyến/xe liên quan
    route = next((r for r in (STORE.get("_routes") or [])
                  if order_id in (r.get("orders") or [])), None)
    inc_record = {
        "case_id": case_id, "order_id": order_id, "event_type": et,
        "priority": ("Cao" if o["computed_status"] == "ERROR" else "Trung bình"),
        "ts": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        "customer": incident.get("customer"), "delivery_name": incident.get("delivery_name"),
        "corridor": incident.get("corridor"),
        "vehicle": (route["vehicle_id"] if route else (rec["vehicle"] if rec else "—")),
        "driver": (route.get("driver") if route else None),
        "route_id": (route["vehicle_id"] if route else "—"),
        "status": "Đang xử lý", "decision": None, "note": "",
        "incident": incident, "options": opt["options"], "soft_skills": opt["soft_skills"],
        "analysis": analysis["text"], "analysis_source": analysis["source"],
        "cost_breakdown": None,
    }
    # thay thế nếu đã có sự cố mở cho cùng đơn
    STORE["incidents"] = [i for i in STORE["incidents"]
                          if not (i["order_id"] == order_id and i["status"] == "Đang xử lý")]
    STORE["incidents"].insert(0, inc_record)

    _append_log({"case_id": case_id, "source": "Đơn kế hoạch tĩnh", "order_id": order_id,
                 "event_type": et, "decision": "Mở phiên xử lý sự cố",
                 "vehicle": inc_record["vehicle"], "status": "Đang xử lý"})
    return jsonify({"incident": inc_record})


@app.route("/api/incidents")
def api_incidents():
    active = [i for i in STORE["incidents"] if i.get("status") != "Hoàn tất"]
    return jsonify({"incidents": [{
        "case_id": i["case_id"], "order_id": i["order_id"], "event_type": i["event_type"],
        "priority": i["priority"], "ts": i["ts"], "vehicle": i["vehicle"],
        "driver": i.get("driver"), "route_id": i.get("route_id"),
        "status": i["status"], "decision": i.get("decision"),
    } for i in active], "types": ext.INCIDENT_TYPES})


@app.route("/api/incident/<case_id>")
def api_incident_detail(case_id):
    inc = next((i for i in STORE["incidents"] if i["case_id"] == case_id), None)
    if not inc:
        return jsonify({"error": "Không tìm thấy sự cố."}), 404
    return jsonify({"incident": inc})


@app.route("/api/incident/resolve", methods=["POST"])
def api_incident_resolve():
    p = request.get_json(silent=True) or {}
    inc = next((i for i in STORE["incidents"] if i["case_id"] == p.get("case_id")), None)
    if not inc:
        return jsonify({"error": "Không tìm thấy sự cố."}), 404
    opt = p.get("option") or {}
    inc["decision"] = opt.get("ten") or p.get("decision") or "Đã chọn phương án"
    inc["note"] = p.get("note", "")
    inc["status"] = "Đã xử lý sự cố"
    cost = eng._f(opt.get("tac_dong_chi_phi"))
    inc["cost_breakdown"] = _bucket_cost(inc["event_type"], cost)
    # cập nhật lại P&L nếu đã tính
    if STORE.get("_financial") and STORE.get("_routes"):
        STORE["_financial"] = ext.financials_detailed(
            STORE["_routes"], STORE["static"]["fleet"], _fin_params(),
            incident_costs=_incident_costs(), backhaul_gain=STORE.get("_backhaul_gain", 0))
    _append_log({"case_id": inc["case_id"], "source": "Đơn kế hoạch tĩnh",
                 "order_id": inc["order_id"], "event_type": inc["event_type"],
                 "decision": inc["decision"], "vehicle": inc["vehicle"],
                 "status": "Đã xử lý sự cố", "note": inc["note"],
                 "profit_protected": eng._f(opt.get("tac_dong_pnl"))})
    return jsonify({"ok": True, "incident_cost": inc["cost_breakdown"]})


def _bucket_cost(event_type, cost):
    et = (event_type or "").lower()
    b = {"xe_thay_the": 0, "chuyen_tai": 0, "cho": 0, "phat_tre": 0,
         "nhien_lieu_di_vong": 0, "khac": 0}
    if "hỏng" in et or "thiếu xe" in et:
        b["xe_thay_the"] = cost
    elif "cấm tải" in et:
        b["chuyen_tai"] = cost
    elif "tắc" in et:
        b["nhien_lieu_di_vong"] = cost
    elif "trễ" in et or "đổi giờ" in et:
        b["cho"] = cost
    else:
        b["khac"] = cost
    return b


@app.route("/api/incident/complete", methods=["POST"])
def api_incident_complete():
    p = request.get_json(silent=True) or {}
    inc = next((i for i in STORE["incidents"] if i["case_id"] == p.get("case_id")), None)
    if not inc:
        return jsonify({"error": "Không tìm thấy sự cố."}), 404
    inc["status"] = "Hoàn tất"
    _append_log({"case_id": inc["case_id"], "source": "Đơn kế hoạch tĩnh",
                 "order_id": inc["order_id"], "event_type": inc["event_type"],
                 "decision": inc.get("decision") or "—", "vehicle": inc["vehicle"],
                 "status": "Hoàn tất — chuyển vào nhật ký",
                 "note": p.get("reason", "Đánh dấu hoàn tất, lưu vết tại nhật ký")})
    return jsonify({"ok": True})


# Dữ liệu động từ file (case mô phỏng)
@app.route("/api/dynamic")
def api_dynamic():
    d = STORE["dynamic"]
    if not d:
        return jsonify({"error": "Chưa nạp dữ liệu động."}), 400
    plans = [eng.build_dynamic_plan(c, d["candidates"], d["params"],
                                    d["workflow"].get(c["case_id"]),
                                    d["playbook"].get(c["case_id"]),
                                    d["risks"].get(c["case_id"])) for c in d["cases"]]
    return jsonify({"cases": plans, "params": d["params"]})


# ============================================================
# MODULE 7 — Nhật ký & lưu vết
# ============================================================
@app.route("/api/log")
def api_log():
    return jsonify({"log": _load_log()})


@app.route("/api/log/delete", methods=["POST"])
def api_log_delete():
    p = request.get_json(silent=True) or {}
    idx = p.get("index")
    log = _load_log()
    if isinstance(idx, int) and 0 <= idx < len(log):
        log.pop(idx)
        _save_log(log)
        return jsonify({"ok": True})
    return jsonify({"error": "Chỉ số dòng không hợp lệ."}), 400


@app.route("/api/log/clear", methods=["POST"])
def api_log_clear():
    _save_log([])
    return jsonify({"ok": True})


# ============================================================
# MODULE 8 — Trợ lý điều phối AI (Gemini)
# ============================================================
@app.route("/api/assistant", methods=["POST"])
def api_assistant():
    p = request.get_json(silent=True) or {}
    q = (p.get("question") or "").strip()
    if not q:
        return jsonify({"error": "Vui lòng nhập câu hỏi."}), 400
    ctx = ext.build_ai_context(STORE)
    ans = ai.assistant_answer(q, ctx)
    return jsonify({"answer": ans["text"], "source": ans["source"]})


# ============================================================
# Ràng buộc vận hành (cấm tải/cấm đường)
# ============================================================
@app.route("/api/constraints", methods=["GET", "POST"])
def api_constraints():
    if request.method == "POST":
        p = request.get_json(silent=True) or {}
        items = p.get("items")
        if not isinstance(items, list):
            return jsonify({"error": "Dữ liệu ràng buộc không hợp lệ."}), 400
        STORE["constraints"] = ext.save_constraints(items)
        return jsonify({"ok": True, "items": STORE["constraints"],
                        "window": ext.constraint_window_text(STORE["constraints"])})
    return jsonify({"items": STORE["constraints"],
                    "window": ext.constraint_window_text(STORE["constraints"])})


# ============================================================
# MODULE — Xuất Excel
# ============================================================
@app.route("/api/export")
def api_export():
    d = STORE["static"]
    routes = STORE.get("_routes") or []
    fin = STORE.get("_financial")
    if not fin and routes:
        fin = ext.financials_detailed(routes, d["fleet"], _fin_params(),
                                      incident_costs=_incident_costs(),
                                      backhaul_gain=STORE.get("_backhaul_gain", 0))
    # kiểm định để xuất sheet kiểm định
    validation = []
    sid = STORE.get("_scenario")
    if d:
        validated, sid, _ = _validated(sid)
        for o in (validated or []):
            validation.append({
                "order_id": o["order_id"], "customer": o["customer"], "corridor": o["corridor"],
                "weight_kg": o["weight_kg"], "min_vehicle": o["min_vehicle"],
                "drop_tw": f"{eng.min_to_hhmm(o['drop_tw_start'])}-{eng.min_to_hhmm(o['drop_tw_end'])}",
                "status_vi": ext.lifecycle_status(o), "issues": o["issues"], "note": o.get("note", ""),
            })
    unassigned = _unassigned_rows(STORE.get("_unassigned") or [], (d["fleet"] if d else []))
    payload = {
        "routes": routes, "unassigned": unassigned, "validation": validation,
        "financial": fin or {"per_route": [], "totals": {}},
        "incidents": [{k: i.get(k) for k in
                       ("case_id", "order_id", "event_type", "priority", "ts", "vehicle",
                        "route_id", "status", "decision")} for i in STORE["incidents"]],
        "log": _load_log(),
        "meta": {"scenario": sid, "engine": "Routing engine (preset trọng số)"},
    }
    try:
        buf = report.build_report(payload)
        fname = f"HPL_BaoCao_DieuPhoi_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        return send_file(buf, as_attachment=True, download_name=fname,
                         mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    except Exception as e:
        return jsonify({"error": f"Lỗi xuất Excel: {e}"}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
