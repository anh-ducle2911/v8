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
import ai_matcher as matcher
import fuel_price as fuel
import excel_report as report

BASE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE, "data")
LOG_PATH = os.path.join(DATA_DIR, "incident_log.json")
DEMO_STATIC = os.path.join(DATA_DIR, "1. HPL_AI_Dispatching_Simulated_Data_VRPTW.xlsx")
DEMO_DYNAMIC = os.path.join(DATA_DIR, "2. HPL_AI_Dispatching_Dynamic_Cases_VRPTW.xlsx")

app = Flask(__name__)
app.secret_key = "hpl-dispatching-2026"
app.config["MAX_CONTENT_LENGTH"] = 32 * 1024 * 1024
app.config["TEMPLATES_AUTO_RELOAD"] = True

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
    # --- Engine Hybrid + auto-optimize (Mục 1–5) ---
    "_auto_optimize": True,        # tự tối ưu lại khi có đơn mới (bật/tắt qua /api/config)
    "_solver_mode": eng.SOLVER_MODE,            # greedy | ortools | hybrid (mặc định hybrid)
    "_solver_time_limit": eng.SOLVER_TIME_LIMIT_SEC,  # giây cho metaheuristic
    "_last_opt_info": None,        # thông tin lần tối ưu gần nhất (engine/mode/thời gian)
    "_incidents_seeded": False,    # đã nạp sự cố từ file Excel/auto-gen chưa (Mục 12)
    "_incidents_excel_total": 0,   # tổng số sự cố có trong file Excel động
}
ext.apply_constraints(STORE["constraints"])

OPT_LOG_PATH = os.path.join(DATA_DIR, "optimization_log.json")

# Trạng thái tuyến: tuyến "đóng băng" KHÔNG bị tối ưu lại (Mục 3).
FROZEN_ROUTE_STATES = {"locked", "in_progress", "completed"}


def _frozen_route(r):
    return str((r or {}).get("status", "assigned")).strip().lower() in FROZEN_ROUTE_STATES


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
# Nhật ký TỐI ƯU (Optimization Log — Mục 5)
# ============================================================
REASON_VI = {
    "manual": "Người dùng bấm tối ưu thủ công",
    "new_order": "Thêm đơn mới (nhập tay)",
    "delete_order": "Xóa đơn khỏi danh sách",
    "import_excel": "Nhập đơn từ Excel",
    "fuel_refresh": "Cập nhật giá nhiên liệu",
}


def _load_opt_log():
    try:
        with open(OPT_LOG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _append_opt_log(reason, info, all_routes, frozen, new_routes, unassigned, fleet, sid):
    """Ghi 1 bản ghi tối ưu đầy đủ trường theo yêu cầu Mục 5:
    thời điểm · lý do · engine + lý do fallback · số đơn tối ưu · số đơn chưa gán
    + lý do · tuyến thay đổi/giữ nguyên."""
    info = info or {}
    una_reasons = []
    for o in (unassigned or [])[:50]:
        reason_txt, _ = ext.unassigned_reason(o, fleet)
        una_reasons.append({"order_id": o.get("order_id"), "reason": reason_txt})
    entry = {
        "ts": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        "scenario": sid,
        "reason": reason,
        "reason_vi": REASON_VI.get(reason, reason),
        "engine": info.get("engine"),
        "mode": info.get("mode"),
        "time_limit_sec": info.get("time_limit_sec"),
        "elapsed_sec": info.get("elapsed_sec"),
        "improved": info.get("improved"),
        "fallback": info.get("fallback"),
        "n_orders_optimized": info.get("n_final_assigned", 0),
        "n_seed_assigned": info.get("n_seed_assigned", 0),
        "n_unassigned": len(unassigned or []),
        "unassigned_reasons": una_reasons,
        "routes_changed": [r["vehicle_id"] for r in (new_routes or [])],
        "routes_kept_frozen": [{"vehicle_id": r["vehicle_id"], "status": r.get("status")}
                               for r in (frozen or [])],
        "n_routes_total": len(all_routes or []),
    }
    log = _load_opt_log()
    log.insert(0, entry)
    log = log[:300]   # giữ tối đa 300 bản ghi
    try:
        with open(OPT_LOG_PATH, "w", encoding="utf-8") as f:
            json.dump(log, f, ensure_ascii=False, indent=2)
    except Exception:
        pass
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
        "fuel": fuel.get_fuel_price_for_ai(),
        "standby": _standby_summary(),
    })


def _standby_summary():
    """Số xe đang giữ standby (xe khả dụng chưa dùng trong kế hoạch). Mục tiêu 3–5 xe."""
    d = STORE["static"]
    if not d:
        return {"count": 0, "target": "3–5", "ok": False, "total_avail": 0}
    avail = eng._avail_fleet(d["fleet"])
    used = {r["vehicle_id"] for r in (STORE.get("_routes") or [])}
    n = max(0, len(avail) - len(used))
    return {"count": n, "target": "3–5", "ok": n >= 3, "total_avail": len(avail)}


# ============================================================
# MODULE 1 — Nhập dữ liệu & ánh xạ
# ============================================================
def _import_payload(parsed, filename):
    d = parsed["data"]
    if parsed["kind"] == "static":
        STORE["static"] = d
        STORE["working"] = {}
        # Dữ liệu mới -> kế hoạch cũ trở nên lỗi thời, xóa để tránh trộn tuyến cũ.
        STORE["_routes"], STORE["_unassigned"], STORE["_financial"] = None, None, None
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
        # Nạp lại file động -> nạp lại danh sách sự cố từ Excel (Mục 12).
        STORE["_incidents_seeded"] = False
        STORE["incidents"] = [i for i in STORE["incidents"]
                              if i.get("source") not in ("Excel động", "Tự sinh (đơn gắn cờ)", "Tự sinh (mẫu)")]
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
    raw = f.read()
    # File đơn bổ sung quay đầu (Module 4): ưu tiên parser backhaul 3 trường hợp,
    # nếu không khớp thì thử schema tĩnh (S1/S2/S3) như trước để không mất tương thích.
    if kind_hint == "backhaul":
        added = 0
        try:
            bk_orders = eng.parse_backhaul_workbook(raw)
            for o in bk_orders:
                STORE["new_backhaul_orders"].append(o)
            added = len(bk_orders)
        except Exception:
            added = 0
        if not added:
            try:
                parsed = eng.parse_workbook(raw)
                if parsed["kind"] == "static":
                    added = _ingest_backhaul_from_static(parsed["data"])
            except Exception as e:
                return jsonify({"error": f"Không đọc được file đơn bổ sung: {e}"}), 500
        return jsonify({"kind": "backhaul", "filename": f.filename,
                        "added": added, "total": len(STORE["new_backhaul_orders"]),
                        "message": f"Đã nạp {added} đơn bổ sung cho chuyến quay đầu."})
    had_plan = bool(STORE.get("_routes"))
    try:
        parsed = eng.parse_workbook(raw)
    except Exception as e:
        return jsonify({"error": f"Không đọc được file Excel: {e}"}), 500
    payload = _import_payload(parsed, f.filename)
    # Upload đơn mới (Excel) + đang bật auto_optimize + đã có kế hoạch -> tự tối ưu lại (Mục 2,4).
    if parsed["kind"] == "static" and had_plan and STORE.get("_auto_optimize"):
        ok, _ = _run_optimize(reason="import_excel")
        payload["reoptimized"] = bool(ok)
    return jsonify(payload)


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
        ("order_id", "Mã đơn"), ("customer", "Khách hàng"), ("corridor", "Tuyến"),
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
    reoptimized = _maybe_auto_optimize("new_order", sid=sid)
    return jsonify({"ok": True, "order_id": o.get("order_id"), "reoptimized": reoptimized})


@app.route("/api/order/delete", methods=["POST"])
def api_order_delete():
    p = request.get_json(silent=True) or {}
    orders, sid = _working_orders(p.get("scenario"))
    if orders is None:
        return jsonify({"error": "Chưa nạp dữ liệu tĩnh."}), 400
    before = len(orders)
    STORE["working"][sid] = [o for o in orders if str(o.get("order_id")) != str(p.get("order_id"))]
    reoptimized = _maybe_auto_optimize("delete_order", sid=sid)
    return jsonify({"ok": True, "removed": before - len(STORE["working"][sid]),
                    "reoptimized": reoptimized})


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
    return jsonify({"scenario": cap, "summary": summary, "orders": rows})


# ============================================================
# MODULE 3 — Kế hoạch tuyến & bản đồ
# ============================================================
def _run_optimize(sid=None, preset=None, weights=None, radius=None,
                  reason="manual", mode=None, time_limit=None):
    """Lõi tối ưu HYBRID dùng chung cho cả tối ưu thủ công lẫn auto-trigger.
    GIỮ NGUYÊN tuyến đã khóa/đang chạy/hoàn tất (Mục 3): chỉ tối ưu lại các đơn
    chưa được khóa. Cập nhật STORE + ghi nhật ký tối ưu. Trả (ok, error)."""
    validated, sid, _ = _validated(sid if sid is not None else STORE.get("_scenario"))
    if validated is None:
        return False, "Chưa nạp dữ liệu tĩnh."
    d = STORE["static"]
    preset = preset or STORE["_preset"]
    weights = weights or STORE["_weights"] or ext.preset_weights(preset)
    radius = eng._f(radius if radius is not None else STORE["_radius"], 30)
    mode = mode or STORE.get("_solver_mode")
    time_limit = int(time_limit or STORE.get("_solver_time_limit") or eng.SOLVER_TIME_LIMIT_SEC)

    # --- Đóng băng tuyến đã khóa / đang chạy / hoàn tất ---
    # CHỈ giữ tuyến đóng băng nếu thuộc ĐÚNG kịch bản đang tối ưu (tránh rò tuyến
    # của kịch bản khác sang kế hoạch hiện tại khi đổi kịch bản).
    prev = (STORE.get("_routes") or []) if STORE.get("_scenario") == sid else []
    frozen = [r for r in prev if _frozen_route(r)]
    frozen_vehicle_ids = {r.get("vehicle_id") for r in frozen}
    frozen_order_ids = {str(oid) for r in frozen for oid in (r.get("orders") or [])}

    fleet_pool = [v for v in d["fleet"] if v["vehicle_id"] not in frozen_vehicle_ids]
    orders_pool = [o for o in validated if str(o["order_id"]) not in frozen_order_ids]

    new_routes, unassigned, info = ext.solve_hybrid(
        orders_pool, fleet_pool, d.get("depots"), weights, radius, mode, time_limit)
    for r in new_routes:
        r.setdefault("status", "assigned")

    all_routes = list(frozen) + list(new_routes)

    # P&L gắn vào từng tuyến (cho bản đồ, trợ lý, KPI)
    fin = ext.financials_detailed(all_routes, d["fleet"], _fin_params())
    pnl_map = {pp["vehicle_id"]: pp for pp in fin["per_route"]}
    for r in all_routes:
        r["pnl"] = pnl_map.get(r["vehicle_id"], r.get("pnl", {}))

    # Timeline ETA chỉ dựng lại cho tuyến MỚI (tuyến đóng băng giữ timeline cũ)
    fmap = {v["vehicle_id"]: v for v in d["fleet"]}
    for r in new_routes:
        r["timeline"] = ext.route_timeline(r, fmap.get(r["vehicle_id"], {}))

    STORE["_routes"], STORE["_unassigned"], STORE["_scenario"] = all_routes, unassigned, sid
    STORE["_preset"], STORE["_weights"], STORE["_radius"] = preset, weights, radius
    STORE["_last_opt_info"] = info
    STORE["_financial"] = None  # buộc tính lại P&L theo kế hoạch mới khi mở Module 5

    _append_opt_log(reason, info, all_routes, frozen, new_routes, unassigned, d["fleet"], sid)
    return True, None


def _route_out(r):
    pnl = r.get("pnl", {}) or {}
    last_del = next((s for s in reversed(r.get("stops") or []) if s.get("type") == "delivery"), None)
    return {
        "vehicle_id": r["vehicle_id"], "plate": r.get("plate"),
        "vehicle_type": r["vehicle_type"], "driver": r.get("driver"),
        "corridor": r.get("corridor"), "n_orders": r["n_orders"],
        "orders": r["orders"], "distance_km": r["distance_km"],
        "empty_km": r.get("empty_km"),
        "total_weight": r["total_weight"], "total_volume": r["total_volume"],
        "fill_weight_pct": r["fill_weight_pct"], "fill_volume_pct": r["fill_volume_pct"],
        "revenue": pnl.get("revenue_total"), "cost": pnl.get("total_cost"),
        "profit": pnl.get("profit"), "margin": pnl.get("margin"),
        "risk_late": pnl.get("risk_late"),
        "has_backhaul": bool(r.get("has_backhaul")),
        "status": r.get("status", "assigned"),
        "locked": _frozen_route(r),
        "end_name": (last_del or {}).get("name"),
        "depot_end": r["stops"][-1].get("name") if r.get("stops") else None,
        "timeline": r.get("timeline"),
        "stops": r["stops"],
    }


def _optimize_payload():
    """Gói dữ liệu kế hoạch hiện tại trong STORE thành payload cho frontend (KPI + tuyến)."""
    d = STORE["static"]
    routes = STORE.get("_routes") or []
    unassigned = STORE.get("_unassigned") or []
    info = STORE.get("_last_opt_info") or {}
    fleet = d["fleet"] if d else []
    validated, _, _ = _validated(STORE.get("_scenario")) if d else (None, None, None)
    n_total = len(validated) if validated else sum(r["n_orders"] for r in routes) + len(unassigned)

    fin = ext.financials_detailed(routes, fleet, _fin_params()) if routes else {"totals": {}}
    t = fin.get("totals", {})
    standby = _standby_summary()
    return {
        "engine": info.get("engine") or "Hybrid Routing Engine (Greedy seed → OR-Tools)",
        "engine_mode": info.get("mode") or STORE.get("_solver_mode"),
        "time_limit_sec": info.get("time_limit_sec"),
        "elapsed_sec": info.get("elapsed_sec"),
        "improved": info.get("improved"),
        "fallback": info.get("fallback"),
        "auto_optimize": STORE.get("_auto_optimize"),
        "scenario": STORE.get("_scenario"), "preset": STORE.get("_preset"),
        "weights": STORE.get("_weights"),
        "n_vehicles_used": len(routes),
        "n_orders_assigned": sum(r["n_orders"] for r in routes),
        "n_orders_total": n_total,
        "n_unassigned": len(unassigned),
        "n_standby": standby["count"], "standby_ok": standby["ok"],
        "total_km": t.get("total_km", 0), "empty_km": t.get("empty_km", 0),
        "empty_km_pct": t.get("empty_km_pct", 0),
        "revenue_total": t.get("revenue_total", 0), "total_cost": t.get("total_cost", 0),
        "profit": t.get("profit", 0), "margin": t.get("margin", 0),
        "routes": [_route_out(r) for r in routes],
        "unassigned": _unassigned_rows(unassigned, fleet),
    }


@app.route("/api/optimize", methods=["POST"])
def api_optimize():
    p = request.get_json(silent=True) or {}
    preset = p.get("preset", STORE["_preset"])
    weights = p.get("weights") or ext.preset_weights(preset)
    radius = eng._f(p.get("radius", STORE["_radius"]), 30)
    ok, err = _run_optimize(p.get("scenario", ""), preset, weights, radius,
                            reason="manual", mode=p.get("mode"), time_limit=p.get("time_limit"))
    if not ok:
        return jsonify({"error": err}), 400
    return jsonify(_optimize_payload())


@app.route("/api/plan")
def api_plan():
    """Trả kế hoạch tuyến hiện tại trong phiên (để frontend làm mới sau auto-optimize)."""
    if not STORE.get("_routes"):
        return jsonify({"routes": [], "unassigned": [], "n_vehicles_used": 0,
                        "n_orders_assigned": 0, "n_unassigned": 0, "has_plan": False})
    out = _optimize_payload()
    out["has_plan"] = True
    return jsonify(out)


def _maybe_auto_optimize(reason, sid=None):
    """Tự tối ưu lại nếu auto_optimize bật VÀ đã có kế hoạch tuyến (Mục 2,4).
    KHÔNG đụng tuyến đã khóa/đang chạy/hoàn tất. CHỈ tự tối ưu khi đơn vừa sửa
    thuộc đúng kịch bản đang lập kế hoạch (tránh đổi nhầm kế hoạch / mất đơn).
    Trả True nếu đã chạy lại."""
    if not STORE.get("_auto_optimize"):
        return False
    if not STORE.get("_routes"):
        return False
    cur = STORE.get("_scenario")
    if sid is not None and str(sid) != str(cur):
        return False   # đơn thuộc kịch bản khác kế hoạch hiện tại -> để người dùng tối ưu thủ công
    try:
        ok, _ = _run_optimize(cur, reason=reason)
        return bool(ok)
    except Exception as e:
        print("auto-optimize error:", e)
        return False


@app.route("/api/optimize/log")
def api_optimize_log():
    return jsonify({"log": _load_opt_log()})


@app.route("/api/route/status", methods=["POST"])
def api_route_status():
    """Đổi trạng thái 1 tuyến: assigned | locked | in_progress | completed (Mục 3)."""
    p = request.get_json(silent=True) or {}
    vid = p.get("vehicle_id")
    status = str(p.get("status", "")).strip().lower()
    valid_states = {"assigned", "locked", "in_progress", "completed"}
    if status not in valid_states:
        return jsonify({"error": "Trạng thái tuyến không hợp lệ."}), 400
    r = next((x for x in (STORE.get("_routes") or []) if x.get("vehicle_id") == vid), None)
    if not r:
        return jsonify({"error": "Không tìm thấy tuyến."}), 404
    r["status"] = status
    label = {"assigned": "Đã gán (cho phép tối ưu lại)", "locked": "Đã khóa",
             "in_progress": "Đang chạy", "completed": "Hoàn thành"}[status]
    _append_log({"case_id": "ROUTE", "source": "Trạng thái tuyến", "order_id": "—",
                 "event_type": "Cập nhật trạng thái tuyến", "vehicle": vid,
                 "decision": f"Đặt tuyến {vid} = {label}", "status": "Đã cập nhật"})
    return jsonify({"ok": True, "vehicle_id": vid, "status": status, "locked": _frozen_route(r)})


@app.route("/api/config", methods=["GET", "POST"])
def api_config():
    """Bật/tắt auto_optimize + chọn chế độ engine + thời gian metaheuristic (Mục 4)."""
    if request.method == "POST":
        p = request.get_json(silent=True) or {}
        if "auto_optimize" in p:
            STORE["_auto_optimize"] = bool(p["auto_optimize"])
        if p.get("solver_mode") in ("greedy", "ortools", "hybrid"):
            STORE["_solver_mode"] = p["solver_mode"]
        if p.get("solver_time_limit"):
            STORE["_solver_time_limit"] = max(1, int(eng._f(p["solver_time_limit"], 30)))
    return jsonify({
        "auto_optimize": STORE.get("_auto_optimize"),
        "solver_mode": STORE.get("_solver_mode"),
        "solver_time_limit": STORE.get("_solver_time_limit"),
        "ortools_available": eng._has_ortools(),
    })


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
            "has_backhaul": bool(r.get("has_backhaul")),
            "stops": [{"type": s["type"], "name": s.get("name"), "lat": s["lat"],
                       "lon": s["lon"], "order_id": s.get("order_id"),
                       "eta": s.get("eta")} for s in r["stops"]],
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
def _ensure_backhaul_sample(force=False):
    """Nạp/làm mới đơn quay đầu MẪU bám điểm kết thúc tuyến hiện tại (Mục 7) để
    Module 4 LUÔN có ~40–50% tuyến ghép được. force=True: thay các đơn mẫu cũ
    nhưng GIỮ đơn nhập tay/đơn từ Excel. Không force: chỉ nạp khi đang rỗng."""
    d = STORE.get("static")
    routes = STORE.get("_routes")
    if not d or not routes:
        return 0
    if STORE["new_backhaul_orders"] and not force:
        return 0
    sample = ext.build_return_orders(routes, d["fleet"], ratio=0.45,
                                     label="Mẫu sinh theo kế hoạch")
    if force:
        manual = [o for o in STORE["new_backhaul_orders"]
                  if "Mẫu sinh theo kế hoạch" not in str(o.get("source", ""))]
        STORE["new_backhaul_orders"] = manual + sample
    else:
        STORE["new_backhaul_orders"] = list(sample)
    return len(sample)


@app.route("/api/backhaul/load_sample", methods=["POST"])
def api_backhaul_load_sample():
    """Nạp đơn quay đầu mẫu trực tiếp từ kế hoạch hiện tại (nút trong Module 4)."""
    if not STORE.get("_routes"):
        return jsonify({"error": "Hãy chạy Kế hoạch tuyến (Module 3) trước."}), 400
    n = _ensure_backhaul_sample(force=True)
    return jsonify({"ok": True, "added": n, "total": len(STORE["new_backhaul_orders"]),
                    "message": f"Đã nạp {n} đơn quay đầu mẫu bám điểm kết thúc tuyến."})


@app.route("/api/backhaul/orders", methods=["GET", "POST", "DELETE"])
def api_backhaul_orders():
    if request.method == "GET":
        _ensure_backhaul_sample()  # nạp trực tiếp vào module nếu đang rỗng & đã có kế hoạch
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
    # L7 — Hợp nhất nguồn chân lý ghép chiều về: route này ALIAS sang engine matcher
    # (ai_matcher.recommend_backhaul_matches) — cùng kết quả với /api/matcher/backhaul,
    # tránh hai lối tính lệch nhau. UI gọi /api/matcher/backhaul; route này giữ tương thích.
    d = STORE["static"]
    routes = STORE.get("_routes")
    if not d or not routes:
        return jsonify({"error": "Hãy chạy Kế hoạch tuyến (Module 3) trước."}), 400
    _ensure_backhaul_sample()   # luôn có đơn để ghép (Mục 7) nếu đang rỗng
    res = matcher.recommend_backhaul_matches(
        routes, STORE["new_backhaul_orders"], d["fleet"],
        fuel_price=fuel.get_diesel_price(), r_pickup=STORE.get("_radius") or 30)
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
    # Giá nhiên liệu TỰ ĐỘNG (trực tuyến/cache/dự phòng) là giá chính để tính P&L.
    try:
        pr["gia_nhien_lieu"] = fuel.get_diesel_price()
    except Exception:
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
    res["uplift_pp"] = round(res["totals"]["margin"] - base, 2)
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
    order_id = (p.get("order_id") or "").strip()
    event_type = p.get("event_type")
    sid = p.get("scenario") or STORE.get("_scenario")

    # Mã đơn là TÙY CHỌN: có mã -> dựng sự cố bám đơn; không có -> mở phiên xử lý
    # chung theo loại sự cố đã chọn (không bắt buộc nhập mã đơn).
    o = None
    if order_id:
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

    if o is not None:
        incident = eng.incident_from_static_order(o, live, params)
        if event_type:
            incident["event_type"] = event_type
        et = incident["event_type"]
        rec = incident.get("recommended_vehicle")
        customer = incident.get("customer")
        delivery_name = incident.get("delivery_name")
        corridor = incident.get("corridor")
        priority = ("Cao" if o["computed_status"] == "ERROR" else "Trung bình")
    else:
        et = event_type or "Rủi ro trễ SLA"
        incident = None
        rec = None
        customer = delivery_name = corridor = None
        priority = "Trung bình"

    opt = ext.incident_options(et, {
        "rec_vehicle": (rec["vehicle"] if rec else None),
        "dist_km": (rec["dist_km"] if rec else 0),
        "eta_min": (rec["eta_min"] if rec else 35),
    })
    analysis = ai.incident_analysis(
        {"order_id": order_id or "—", "event_type": et, "customer": customer,
         "delivery_name": delivery_name, "corridor": corridor},
        opt["options"])

    STORE["_inc_seq"] += 1
    case_id = f"SC-{datetime.now().strftime('%H%M%S')}-{STORE['_inc_seq']}"
    # tuyến/xe liên quan (chỉ khi có mã đơn cụ thể)
    route = next((r for r in (STORE.get("_routes") or [])
                  if order_id and order_id in (r.get("orders") or [])), None)
    inc_record = {
        "case_id": case_id, "order_id": order_id or "—", "event_type": et,
        "priority": priority,
        "ts": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        "customer": customer, "delivery_name": delivery_name, "corridor": corridor,
        "vehicle": (route["vehicle_id"] if route else (rec["vehicle"] if rec else "—")),
        "driver": (route.get("driver") if route else None),
        "route_id": (route["vehicle_id"] if route else "—"),
        "status": "Đang xử lý", "decision": None, "note": "",
        "incident": incident, "options": opt["options"], "soft_skills": opt["soft_skills"],
        "analysis": analysis["text"], "analysis_source": analysis["source"],
        "cost_breakdown": None,
    }
    # thay thế nếu đã có sự cố mở cho CÙNG đơn (chỉ khi có mã đơn cụ thể)
    if order_id:
        STORE["incidents"] = [i for i in STORE["incidents"]
                              if not (i["order_id"] == order_id and i["status"] == "Đang xử lý")]
    STORE["incidents"].insert(0, inc_record)

    _append_log({"case_id": case_id,
                 "source": ("Đơn kế hoạch tĩnh" if order_id else "Mở thủ công"),
                 "order_id": order_id or "—",
                 "event_type": et, "decision": "Mở phiên xử lý sự cố",
                 "vehicle": inc_record["vehicle"], "status": "Đang xử lý"})
    return jsonify({"incident": inc_record})


# ---- Nạp sự cố từ file Excel động + tự sinh nếu file chưa có (Mục 12) ----
INCIDENTS_SEED_CAP = 60   # giới hạn hiển thị để UI gọn (không cắt im lặng: báo tổng số)


def _incident_from_dynamic_case(c):
    """Chuyển 1 case trong file Excel động thành bản ghi sự cố hiển thị ở Module 6.
    Hiển thị ở trạng thái 'Đang xử lý' để điều phối viên xử lý lại trong Control Tower
    (giữ kết quả lịch sử trong file ở trường file_status để tham khảo)."""
    et = ext.dynamic_event_vi(c.get("event_type"))
    return {
        "case_id": c.get("case_id"), "order_id": c.get("order_id") or "—",
        "event_type": et, "event_type_raw": c.get("event_type"),
        "priority": ("Cao" if c.get("must_not_cancel") else "Trung bình"),
        "ts": (datetime.now().strftime("%d/%m/%Y ") + str(c.get("event_time") or "")).strip(),
        "customer": None, "delivery_name": c.get("name"), "corridor": None,
        "vehicle": c.get("vehicle") or "—", "driver": None,
        "route_id": c.get("route_id") or "—",
        "status": "Đang xử lý", "file_status": c.get("status"),
        "decision": None, "note": "",
        "incident": None, "options": None, "soft_skills": None,
        "analysis": None, "analysis_source": None, "cost_breakdown": None,
        "source": "Excel động", "_case": c,
    }


def _autogen_incidents():
    """Tự sinh sự cố khi file chưa có: ưu tiên các đơn tĩnh đang bị gắn cờ; nếu
    không có thì sinh một bộ sự cố mẫu để dispatcher luyện xử lý (Mục 12)."""
    out = []
    d = STORE.get("static")
    if d:
        validated, sid, _ = _validated(STORE.get("_scenario"))
        flagged = [o for o in (validated or []) if o.get("computed_status") in ("REVIEW", "ERROR")][:6]
        for k, o in enumerate(flagged, 1):
            et = {"Traffic Congestion & Police Check": "Tắc đường",
                  "Vehicle Mismatch / Split": "Thiếu xe",
                  "Empty-run Risk": "Rủi ro trễ SLA"}.get(o.get("incident_hint"), "Rủi ro trễ SLA")
            out.append({
                "case_id": f"GEN-{k:02d}", "order_id": o.get("order_id"), "event_type": et,
                "event_type_raw": o.get("incident_hint"), "priority": "Trung bình",
                "ts": datetime.now().strftime("%d/%m/%Y %H:%M"),
                "customer": o.get("customer"), "delivery_name": o.get("delivery_name"),
                "corridor": o.get("corridor"), "vehicle": "—", "driver": None, "route_id": "—",
                "status": "Đang xử lý", "decision": None, "note": "",
                "incident": None, "options": None, "soft_skills": None,
                "analysis": None, "analysis_source": None, "cost_breakdown": None,
                "source": "Tự sinh (đơn gắn cờ)", "_order_id": o.get("order_id"),
            })
    if not out:
        for k, et in enumerate(["Tắc đường", "Khách đổi giờ giao", "Xe hỏng"], 1):
            out.append({
                "case_id": f"GEN-{k:02d}", "order_id": "—", "event_type": et,
                "event_type_raw": et, "priority": "Trung bình",
                "ts": datetime.now().strftime("%d/%m/%Y %H:%M"),
                "customer": None, "delivery_name": "Điểm giao mẫu", "corridor": None,
                "vehicle": "—", "driver": None, "route_id": "—",
                "status": "Đang xử lý", "decision": None, "note": "",
                "incident": None, "options": None, "soft_skills": None,
                "analysis": None, "analysis_source": None, "cost_breakdown": None,
                "source": "Tự sinh (mẫu)",
            })
    return out


def _ensure_incidents():
    """Đảm bảo Module 6 luôn có sự cố để xử lý: nạp toàn bộ từ file Excel động đã
    nạp; nếu file chưa có sự cố -> tự sinh. Chỉ seed 1 lần (cho tới khi nạp lại file)."""
    if STORE.get("_incidents_seeded"):
        return
    dy = STORE.get("dynamic")
    seeded = []
    if dy and dy.get("cases"):
        STORE["_incidents_excel_total"] = len(dy["cases"])
        for c in dy["cases"][:INCIDENTS_SEED_CAP]:
            seeded.append(_incident_from_dynamic_case(c))
    if not seeded:
        seeded = _autogen_incidents()
        STORE["_incidents_excel_total"] = 0
    # giữ các sự cố do dispatcher tạo tay; thêm các sự cố seed (tránh trùng case_id)
    existing_ids = {i.get("case_id") for i in STORE["incidents"]}
    STORE["incidents"] = STORE["incidents"] + [s for s in seeded if s["case_id"] not in existing_ids]
    STORE["_incidents_seeded"] = True


def _hydrate_incident(inc):
    """Dựng phương án/soft-skill/phân tích cho 1 sự cố từ Excel/auto-gen khi mở chi
    tiết (lazy). Dùng lại đúng luồng phương án của engine + Trợ lý AI."""
    if inc.get("options") is not None:
        return inc
    et = inc.get("event_type")
    case = inc.get("_case") or {}
    # xe thay thế gần nhất (nếu có ứng viên trong file động)
    live, params = _live_fleet()
    rec_vehicle, dist_km, eta_min = None, 0, 35
    incident_blob = {"event_type": et, "delivery_name": inc.get("delivery_name"),
                     "candidates": [], "recommended_vehicle": None}
    dy = STORE.get("dynamic")
    if dy and case:
        cands = [c for c in dy.get("candidates", []) if c.get("case_id") == case.get("case_id")]
        scored = []
        for c in cands:
            sc, feasible = eng.score_replacement(c, dy.get("params"))
            scored.append({"vehicle": c.get("vehicle"), "vehicle_type": c.get("vehicle_type"),
                           "lat": c.get("lat"), "lon": c.get("lon"),
                           "dist_km": c.get("dist_km"), "eta_min": c.get("eta_min"),
                           "capacity_ok": c.get("capacity_ok"),
                           "engine_score": sc, "engine_feasible": feasible})
        scored.sort(key=lambda x: (-int(x["engine_feasible"]), x.get("dist_km") or 1e9))
        if scored:
            incident_blob["candidates"] = scored[:6]
            incident_blob["recommended_vehicle"] = next((x for x in scored if x["engine_feasible"]), scored[0])
            best = incident_blob["recommended_vehicle"]
            rec_vehicle, dist_km, eta_min = best.get("vehicle"), best.get("dist_km", 0), best.get("eta_min", 35)
            incident_blob["incident_lat"] = cands[0].get("incident_lat")
            incident_blob["incident_lon"] = cands[0].get("incident_lon")
            incident_blob["radius_max"] = 30
    opt = ext.incident_options(et, {"rec_vehicle": rec_vehicle, "dist_km": dist_km, "eta_min": eta_min})
    analysis = ai.incident_analysis(
        {"order_id": inc.get("order_id"), "event_type": et, "customer": inc.get("customer"),
         "delivery_name": inc.get("delivery_name"), "corridor": inc.get("corridor")}, opt["options"])
    inc["incident"] = incident_blob
    inc["options"] = opt["options"]
    inc["soft_skills"] = opt["soft_skills"]
    inc["analysis"] = analysis["text"]
    inc["analysis_source"] = analysis["source"]
    return inc


@app.route("/api/incidents")
def api_incidents():
    _ensure_incidents()
    active = [i for i in STORE["incidents"] if i.get("status") != "Hoàn tất"]
    return jsonify({"incidents": [{
        "case_id": i["case_id"], "order_id": i["order_id"], "event_type": i["event_type"],
        "priority": i["priority"], "ts": i["ts"], "vehicle": i["vehicle"],
        "driver": i.get("driver"), "route_id": i.get("route_id"),
        "status": i["status"], "decision": i.get("decision"), "source": i.get("source"),
    } for i in active],
        "types": ["Tất cả"] + ext.INCIDENT_TYPES,
        "excel_total": STORE.get("_incidents_excel_total", 0),
        "shown": len(active),
        "seed_cap": INCIDENTS_SEED_CAP})


@app.route("/api/incident/<case_id>")
def api_incident_detail(case_id):
    inc = next((i for i in STORE["incidents"] if i["case_id"] == case_id), None)
    if not inc:
        return jsonify({"error": "Không tìm thấy sự cố."}), 404
    _hydrate_incident(inc)   # dựng phương án/phân tích nếu là sự cố từ Excel/auto-gen
    return jsonify({"incident": inc})


@app.route("/api/incident/resolve", methods=["POST"])
def api_incident_resolve():
    p = request.get_json(silent=True) or {}
    inc = next((i for i in STORE["incidents"] if i["case_id"] == p.get("case_id")), None)
    if not inc:
        return jsonify({"error": "Không tìm thấy sự cố."}), 404
    opt = p.get("option") or {}
    note = p.get("note", "")
    if opt.get("self_fill"):
        # Dispatcher tự điền: quyết định lấy từ ghi chú (Mục 13).
        inc["decision"] = note.strip() or "Phương án do điều phối viên tự điền"
    else:
        inc["decision"] = opt.get("ten") or p.get("decision") or "Đã chọn phương án"
    inc["note"] = note
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
@app.route("/api/ai/chat", methods=["POST"])
def api_assistant():
    p = request.get_json(silent=True) or {}
    q = (p.get("question") or "").strip()
    if not q:
        return jsonify({"error": "Vui lòng nhập câu hỏi."}), 400
    ans = ai.answer_dispatch_question(q, STORE)
    return jsonify({"answer": ans["text"], "source": ans["source"]})


@app.route("/api/ai/context")
def api_ai_context():
    """Trả ngữ cảnh trực tuyến mà Trợ lý AI đang đọc (minh bạch dữ liệu)."""
    return jsonify(ai.build_ai_context(STORE))


@app.route("/api/ai/suggest")
def api_ai_suggest():
    """Gợi ý AI bám sát module hiện tại (nguồn online + dữ liệu phiên) — Mục 11."""
    module = request.args.get("module", "plan")
    adv = ai.module_advice(module, STORE)
    return jsonify(adv)


# ============================================================
# MODULE — Matcher (thuật toán matching/scoring) cho AI & UI
# ============================================================
@app.route("/api/matcher/backhaul", methods=["POST"])
def api_matcher_backhaul():
    d = STORE["static"]
    routes = STORE.get("_routes")
    if not d or not routes:
        return jsonify({"error": "Hãy chạy Kế hoạch tuyến (Module 3) trước."}), 400
    _ensure_backhaul_sample()   # luôn có đơn quay đầu để ghép (~40–50% tuyến)
    res = matcher.recommend_backhaul_matches(
        routes, STORE["new_backhaul_orders"], d["fleet"],
        fuel_price=fuel.get_diesel_price(), r_pickup=STORE.get("_radius") or 30)
    return jsonify(res)


@app.route("/api/matcher/reassign", methods=["POST"])
def api_matcher_reassign():
    """Đề xuất điều phối lại khi có sự cố (xe thay thế/standby)."""
    p = request.get_json(silent=True) or {}
    inc = p.get("incident") or {}
    live, _ = _live_fleet()
    res = matcher.recommend_reassignment_for_incident(
        inc, live, STORE.get("_routes"), fuel_price=fuel.get_diesel_price())
    return jsonify(res)


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
SCENARIO_VI = {
    "S1": "Kịch bản 1 — Nhu cầu ổn định (thừa năng lực)",
    "S2": "Kịch bản 2 — Nhu cầu tăng cao (đủ năng lực)",
    "S3": "Kịch bản 3 — Phát sinh sự cố (thiếu năng lực)",
}


def _scenario_vi(sid):
    return SCENARIO_VI.get(sid, sid or "—")


def _build_export_payload():
    """Gom toàn bộ dữ liệu phiên thành payload cho dashboard Excel."""
    d = STORE["static"]
    routes = STORE.get("_routes") or []
    fin = STORE.get("_financial")
    if not fin and routes and d:
        fin = ext.financials_detailed(routes, d["fleet"], _fin_params(),
                                      incident_costs=_incident_costs(),
                                      backhaul_gain=STORE.get("_backhaul_gain", 0))
        pnl_map = {pp["vehicle_id"]: pp for pp in fin["per_route"]}
        for r in routes:
            r["pnl"] = pnl_map.get(r["vehicle_id"], r.get("pnl"))
    fin = fin or {"per_route": [], "totals": {}}
    totals = fin.get("totals", {})

    sid = STORE.get("_scenario")
    validated = []
    if d:
        validated, sid, _ = _validated(sid)
        validated = validated or []

    # bản đồ đơn -> xe gán
    order_vehicle = {}
    for r in routes:
        for oid in (r.get("orders") or []):
            order_vehicle[str(oid)] = r["vehicle_id"]

    orders_out = []
    for o in validated:
        oid = str(o["order_id"])
        veh = order_vehicle.get(oid)
        if veh:
            status_gan = "Đã gán"
        elif o.get("computed_status") == "ERROR":
            status_gan = "Không thể xử lý"
        else:
            status_gan = "Chưa gán"
        orders_out.append({
            "order_id": o["order_id"], "customer": o["customer"], "corridor": o["corridor"],
            "weight_kg": o["weight_kg"], "min_vehicle": o["min_vehicle"],
            "drop_tw": f"{eng.min_to_hhmm(o['drop_tw_start'])}-{eng.min_to_hhmm(o['drop_tw_end'])}",
            "revenue": o["revenue"], "status_vi": ext.lifecycle_status(o),
            "status_gan": status_gan, "assigned_vehicle": veh,
            "issues": o["issues"], "note": o.get("note", ""),
        })

    used_ids = set(order_vehicle.values())
    fleet_out = []
    for v in (d["fleet"] if d else []):
        fleet_out.append({
            "vehicle_id": v["vehicle_id"], "plate": v.get("plate"), "vehicle_type": v["vehicle_type"],
            "driver_name": v.get("driver_name"), "depot_name": v.get("depot_name"),
            "corridor": v.get("corridor"), "max_weight_kg": v.get("max_weight_kg"),
            "max_volume_m3": v.get("max_volume_m3"), "used": v["vehicle_id"] in used_ids,
        })

    bk = {"results": [], "empty_km_avoided": 0, "n_matched": 0}
    if routes and d:
        bk = matcher.recommend_backhaul_matches(
            routes, STORE["new_backhaul_orders"], d["fleet"],
            fuel_price=fuel.get_diesel_price(), r_pickup=STORE.get("_radius") or 30)

    fuel_ctx = fuel.get_fuel_price_for_ai()
    log = _load_log()
    fills = [r.get("fill_weight_pct") for r in routes if r.get("fill_weight_pct") is not None]
    kpi = {
        "n_orders_total": len(orders_out),
        "n_assigned": sum(r["n_orders"] for r in routes),
        "n_unassigned": len(STORE.get("_unassigned") or []),
        "n_vehicles_used": len(routes),
        "n_standby": _standby_summary()["count"],
        "fill_rate_avg": round(sum(fills) / len(fills), 1) if fills else 0,
        "total_km": totals.get("total_km", 0), "empty_km": totals.get("empty_km", 0),
        "empty_km_pct": totals.get("empty_km_pct", 0), "empty_km_avoided": bk.get("empty_km_avoided", 0),
        "revenue_total": totals.get("revenue_total", 0), "total_cost": totals.get("total_cost", 0),
        "profit": totals.get("profit", 0), "margin": totals.get("margin", 0),
        "profit_after": totals.get("profit_after", totals.get("profit", 0)),
        "margin_after": totals.get("margin_after", totals.get("margin", 0)),
        "incident_cost": totals.get("incident_cost", 0),
        "backhaul_gain": totals.get("backhaul_gain", STORE.get("_backhaul_gain", 0)),
        "n_incidents": len(STORE["incidents"]),
        "n_backhaul_suggested": bk.get("n_matched", 0),
        "n_backhaul_accepted": sum(1 for e in log if e.get("case_id") == "BACKHAUL"),
        "fuel_price": fuel_ctx["gia_nhien_lieu"],
    }
    return {
        "routes": routes,
        "unassigned": _unassigned_rows(STORE.get("_unassigned") or [], (d["fleet"] if d else [])),
        "orders": orders_out, "fleet": fleet_out,
        "backhaul_orders": STORE["new_backhaul_orders"], "backhaul_matches": bk.get("results", []),
        "financial": fin, "kpi": kpi,
        "incidents": [{k: i.get(k) for k in
                       ("case_id", "order_id", "event_type", "priority", "ts", "vehicle",
                        "route_id", "status", "decision")} for i in STORE["incidents"]],
        "log": log,
        "meta": {"scenario": sid, "scenario_vi": _scenario_vi(sid),
                 "engine": "Routing engine đa tiêu chí (thời gian · chi phí · tải · cấm tải · backhaul)",
                 "generated_display": datetime.now().strftime("%d/%m/%Y %H:%M"),
                 "fuel": fuel_ctx},
    }


@app.route("/api/export")
@app.route("/api/export/dashboard")
def api_export():
    try:
        payload = _build_export_payload()
        buf = report.build_report(payload)
        fname = f"HPL_Dashboard_DieuPhoi_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        return send_file(buf, as_attachment=True, download_name=fname,
                         mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    except Exception as e:
        return jsonify({"error": f"Lỗi xuất Excel: {e}"}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
