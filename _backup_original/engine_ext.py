# -*- coding: utf-8 -*-
"""
ENGINE EXTENSIONS (engine_ext.py)
=================================
Phần mở rộng cho lõi thuật toán hpl_engine.py, phục vụ bản v4 (Control Tower
8 module). Tất cả logic ở đây KHÔNG phải AI tạo sinh — đây là routing engine /
optimization engine: gán xe, lập tuyến, tính chi phí, xử lý ràng buộc vận hành.

Gồm:
  • Ràng buộc vận hành (cấm tải/cấm đường) có thể xem & chỉnh theo khu vực,
    loại xe, khung giờ, ngày áp dụng — thay cho hằng số cứng trong UI.
  • Ghép chuyến quay đầu TỪ ĐƠN BỔ SUNG MỚI (không lấy đơn cũ trong kế hoạch).
  • Tài chính P&L chi tiết theo từng hạng mục thực tế 3PL + cập nhật khi có sự cố.
  • Sinh phương án xử lý sự cố theo loại sự cố (engine đề xuất, Dispatcher quyết).
  • Dựng "ngữ cảnh điều phối" cho Trợ lý AI trả lời bám dữ liệu thực.
"""

import os
import json
from datetime import datetime

import hpl_engine as eng

BASE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE, "data")
CONSTRAINTS_PATH = os.path.join(DATA_DIR, "constraints.json")


# ============================================================
# 1. RÀNG BUỘC VẬN HÀNH — CẤM TẢI / CẤM ĐƯỜNG (xem & chỉnh)
# ============================================================
DEFAULT_CONSTRAINTS = [
    {
        "id": "RB-HN-INNER-AM",
        "khu_vuc": "Nội thành Hà Nội",
        "loai_xe": "Trên 1.25 tấn",
        "tuyen": "Vành đai trong",
        "gio_bat_dau": "06:00",
        "gio_ket_thuc": "09:00",
        "ngay_ap_dung": "Tất cả các ngày",
        "ghi_chu": "Cấm xe tải trên 1.25 tấn giờ cao điểm sáng.",
        "hieu_luc": True,
    },
    {
        "id": "RB-HN-INNER-PM",
        "khu_vuc": "Nội thành Hà Nội",
        "loai_xe": "Trên 1.25 tấn",
        "tuyen": "Vành đai trong",
        "gio_bat_dau": "16:30",
        "gio_ket_thuc": "19:30",
        "ngay_ap_dung": "Tất cả các ngày",
        "ghi_chu": "Cấm xe tải trên 1.25 tấn giờ cao điểm chiều.",
        "hieu_luc": True,
    },
]


def load_constraints():
    try:
        with open(CONSTRAINTS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list) and data:
                return data
    except Exception:
        pass
    return [dict(c) for c in DEFAULT_CONSTRAINTS]


def save_constraints(items):
    try:
        with open(CONSTRAINTS_PATH, "w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, indent=2)
    except Exception:
        pass
    apply_constraints(items)
    return items


def apply_constraints(items):
    """Đẩy các khung giờ cấm tải đang hiệu lực vào lõi engine để VRPTW + kiểm định
    tôn trọng đúng dữ liệu ràng buộc người dùng cấu hình (không hard-code)."""
    windows = []
    for c in items or []:
        if not c.get("hieu_luc", True):
            continue
        a = eng.time_to_min(c.get("gio_bat_dau"))
        b = eng.time_to_min(c.get("gio_ket_thuc"))
        if b > a:
            windows.append((a, b))
    if windows:
        eng.INNER_CITY_BAN_WINDOWS = windows
    return windows


def constraint_window_text(items):
    parts = []
    for c in items or []:
        if c.get("hieu_luc", True):
            parts.append(f"{c.get('gio_bat_dau')}–{c.get('gio_ket_thuc')}")
    return " và ".join(parts) if parts else "—"


# ============================================================
# 2. CHUẨN HÓA / GÁN TRẠNG THÁI ĐƠN HÀNG (vòng đời đơn)
# ============================================================
ORDER_STATES = [
    "Chưa kiểm định", "Cần xem xét", "Hợp lệ", "Đã gán xe", "Chưa gán được",
    "Đang vận chuyển", "Có nguy cơ trễ", "Phát sinh sự cố", "Đang xử lý sự cố",
    "Đã xử lý sự cố", "Hoàn tất", "Đã hủy",
]


def lifecycle_status(o):
    """Quy đổi kết quả kiểm định kỹ thuật sang trạng thái nghiệp vụ tiếng Việt."""
    cs = o.get("computed_status")
    if cs == "ERROR":
        return "Không thể xử lý"
    if cs == "REVIEW":
        return "Cần xem xét"
    return "Hợp lệ"


# ============================================================
# 3. TÀI CHÍNH P&L CHI TIẾT (theo hạng mục thực tế 3PL)
# ============================================================
DEFAULT_PARAMS = {
    "gia_nhien_lieu": 30020,          # VND/lít
    "tieu_hao_lit_km": 0.09,          # lít/km (mặc định; có thể theo loại xe)
    "luong_tai_xe_chuyen": 300000,    # lương cơ bản phân bổ/chuyến
    "phu_cap_chuyen": 80000,          # phụ cấp/chuyến
    "chi_phi_tang_ca_gio": 45000,     # /giờ vượt ca
    "phi_cau_duong_km": 1400,         # phí BOT bình quân/km liên tỉnh
    "chi_phi_boc_xep_don": 50000,     # bốc + dỡ/đơn
    "chi_phi_thue_xe_ngoai": 0,       # /chuyến thuê ngoài (mặc định 0)
    "chi_phi_chuyen_tai": 0,          # /lần chuyển tải
    "chi_phi_cho_phut": 1500,         # /phút chờ không thu được
    "chi_phi_phat_tre": 0,            # /đơn phạt trễ
    "bao_duong_km": 1400,             # bảo dưỡng/km
    "khau_hao_km": 1600,              # khấu hao/km
    "bao_hiem_chuyen": 30000,         # bảo hiểm phân bổ/chuyến
    "ty_le_quan_ly": 0.08,            # overhead quản lý theo % doanh thu
    "nguong_gio_lam": 600,            # phút làm chuẩn trước khi tính tăng ca (10h)
}

# Thứ tự ca làm chuẩn cho rủi ro trễ
SHIFT_DEFAULT_END = 1080  # 18:00


def _intercity_km(route):
    """Quãng liên tỉnh (ngoài nội thành) — nội thành HN không qua trạm BOT."""
    inner = any("Nội thành" in str(o.get("corridor") or "") for o in route.get("order_objs", []))
    all_inner = inner and all("Nội thành" in str(o.get("corridor") or "")
                              for o in route.get("order_objs", []))
    if all_inner:
        return 0.0
    return route.get("productive_km", route.get("distance_km", 0.0))


def route_pnl_detailed(route, veh, params):
    p = {**DEFAULT_PARAMS, **(params or {})}
    orders = route.get("order_objs", [])

    # --- Doanh thu tuyến ---
    revenue = sum(eng._f(o.get("revenue")) for o in orders)
    extra = sum(eng._f(o.get("extra_stop_fee")) for o in orders)
    waiting_chargeable = sum(eng._f(o.get("waiting_fee")) for o in orders)
    revenue_total = revenue + extra + waiting_chargeable

    productive_km = route.get("productive_km", route.get("distance_km", 0.0))
    full_km = route.get("distance_km", 0.0)
    empty_km = route.get("empty_km", 0.0)

    fuel_lpk = (veh or {}).get("fuel_l_per_km") or p["tieu_hao_lit_km"]

    # --- Chi phí nhiên liệu (chỉ quãng có tải) ---
    fuel = productive_km * fuel_lpk * p["gia_nhien_lieu"]
    # chiều rỗng vượt ngưỡng repositioning -> nhiên liệu+bảo dưỡng chiều rỗng
    free_rep = 30.0
    charged_empty = max(0.0, empty_km - free_rep) if not route.get("has_backhaul") else 0.0
    empty_cost = charged_empty * (fuel_lpk * p["gia_nhien_lieu"] + p["bao_duong_km"])

    # --- Phí cầu đường ---
    toll = _intercity_km(route) * p["phi_cau_duong_km"]

    # --- Chi phí tài xế ---
    avg_speed = (veh or {}).get("avg_speed") or 45
    drive_min = full_km / max(1e-6, avg_speed) * 60 + 50 * max(1, len(orders))
    overtime_min = max(0.0, drive_min - p["nguong_gio_lam"])
    overtime = overtime_min / 60.0 * p["chi_phi_tang_ca_gio"]
    driver_cost = p["luong_tai_xe_chuyen"] + p["phu_cap_chuyen"] + overtime

    # --- Chi phí xe (khấu hao + bảo dưỡng + bảo hiểm) ---
    depreciation = productive_km * p["khau_hao_km"]
    maintenance = productive_km * p["bao_duong_km"]
    insurance = p["bao_hiem_chuyen"]
    vehicle_cost = depreciation + maintenance + insurance

    # --- Bốc xếp ---
    handling = len(orders) * p["chi_phi_boc_xep_don"]

    # --- Overhead quản lý ---
    overhead = revenue_total * p["ty_le_quan_ly"]

    total_cost = (fuel + toll + driver_cost + vehicle_cost + handling +
                  empty_cost + overhead)
    profit = revenue_total - total_cost
    margin = (profit / revenue_total * 100) if revenue_total > 0 else 0.0

    # rủi ro trễ giờ: nếu kết thúc ca dự kiến vượt shift_end
    shift_end = (veh or {}).get("shift_end") or SHIFT_DEFAULT_END
    risk_late = drive_min > p["nguong_gio_lam"] or (overtime_min > 30)

    return {
        "vehicle_id": route.get("vehicle_id"),
        "vehicle_type": route.get("vehicle_type"),
        "driver": route.get("driver"),
        "corridor": route.get("corridor"),
        "n_orders": route.get("n_orders"),
        "distance_km": round(full_km, 1),
        "productive_km": round(productive_km, 1),
        "empty_km": round(empty_km, 1),
        "revenue_freight": round(revenue),
        "revenue_total": round(revenue_total),
        "fuel": round(fuel),
        "toll": round(toll),
        "driver_base": round(p["luong_tai_xe_chuyen"]),
        "driver_allowance": round(p["phu_cap_chuyen"]),
        "overtime": round(overtime),
        "driver_cost": round(driver_cost),
        "depreciation": round(depreciation),
        "maintenance": round(maintenance),
        "insurance": round(insurance),
        "vehicle_cost": round(vehicle_cost),
        "handling": round(handling),
        "empty_cost": round(empty_cost),
        "overhead": round(overhead),
        "total_cost": round(total_cost),
        "profit": round(profit),
        "margin": round(margin, 1),
        "risk_late": risk_late,
        "fill_weight_pct": route.get("fill_weight_pct"),
        "fill_volume_pct": route.get("fill_volume_pct"),
    }


def financials_detailed(routes, fleet, params, incident_costs=None, backhaul_gain=0):
    """P&L toàn kế hoạch + 'sau xử lý sự cố'. incident_costs: list dict hạng mục."""
    p = {**DEFAULT_PARAMS, **(params or {})}
    fmap = {v["vehicle_id"]: v for v in (fleet or [])}
    per_route = []
    line = {"fuel": 0, "toll": 0, "driver_cost": 0, "vehicle_cost": 0,
            "handling": 0, "empty_cost": 0, "overhead": 0,
            "depreciation": 0, "maintenance": 0, "insurance": 0,
            "overtime": 0, "driver_base": 0, "driver_allowance": 0}
    revenue_total = 0
    total_cost = 0
    total_km = 0.0
    total_empty = 0.0
    total_weight = 0.0
    n_risk = 0
    for r in routes or []:
        veh = fmap.get(r.get("vehicle_id"), {})
        d = route_pnl_detailed(r, veh, p)
        per_route.append(d)
        revenue_total += d["revenue_total"]
        total_cost += d["total_cost"]
        total_km += d["distance_km"]
        total_empty += d["empty_km"]
        total_weight += r.get("total_weight", 0)
        if d["risk_late"]:
            n_risk += 1
        for k in line:
            line[k] += d.get(k, 0)

    profit = revenue_total - total_cost
    margin = round(profit / revenue_total * 100, 1) if revenue_total else 0.0

    # --- Chi phí phát sinh do sự cố ---
    inc_total = 0
    inc_breakdown = {"xe_thay_the": 0, "chuyen_tai": 0, "cho": 0, "phat_tre": 0,
                     "nhien_lieu_di_vong": 0, "khac": 0}
    for ic in incident_costs or []:
        for k in inc_breakdown:
            inc_breakdown[k] += eng._f(ic.get(k))
        inc_total += sum(eng._f(ic.get(k)) for k in inc_breakdown)

    profit_after = profit - inc_total + (backhaul_gain or 0)
    margin_after = round(profit_after / revenue_total * 100, 1) if revenue_total else 0.0

    totals = {
        "revenue_total": round(revenue_total),
        "total_cost": round(total_cost),
        **{k: round(v) for k, v in line.items()},
        "incident_cost": round(inc_total),
        "incident_breakdown": {k: round(v) for k, v in inc_breakdown.items()},
        "backhaul_gain": round(backhaul_gain or 0),
        "profit": round(profit),
        "margin": margin,
        "profit_after": round(profit_after),
        "margin_after": margin_after,
        "n_routes": len(routes or []),
        "total_km": round(total_km, 1),
        "empty_km": round(total_empty, 1),
        "empty_km_pct": round(total_empty / total_km * 100, 1) if total_km else 0,
        "total_weight_ton": round(total_weight / 1000.0, 2),
        "cost_per_ton": round(total_cost / max(0.001, total_weight / 1000.0)) if total_weight else 0,
        "profit_per_km": round(profit / total_km) if total_km else 0,
        "n_risk_late": n_risk,
        "band": margin_band(margin_after),
    }
    return {"per_route": per_route, "totals": totals, "params": p}


def margin_band(m):
    if m < 0:
        return {"key": "lo", "label": "Lỗ", "color": "#B71C1C"}
    if m < 10:
        return {"key": "thap", "label": "Rủi ro thấp lợi nhuận", "color": "#E67700"}
    if m < 17:
        return {"key": "xem_xet", "label": "Cần xem xét", "color": "#B07A00"}
    if m <= 22:
        return {"key": "muc_tieu", "label": "Vùng mục tiêu thực tế", "color": "#1B7A2F"}
    return {"key": "cao", "label": "Tốt — cần kiểm tra tính bền vững", "color": "#1565C0"}


def baseline_margin(orders, fleet, depots, params):
    """Biên 'ngây thơ' (mỗi đơn 1 xe, không gom) để chứng minh engine nâng biên."""
    valid = [o for o in orders if o.get("valid", True)]
    avail = eng._avail_fleet(fleet)
    routes = []
    for i, o in enumerate(valid):
        if not avail:
            break
        veh = avail[i % len(avail)]
        routes.append(eng._assemble_route(veh, [o], depots))
    res = financials_detailed(routes, fleet, params)
    return res["totals"]["margin"]


# ============================================================
# 4. GHÉP CHUYẾN QUAY ĐẦU — TỪ ĐƠN BỔ SUNG MỚI (round-use)
# ============================================================
def backhaul_new_orders(routes, new_orders, fleet, params, r_pickup=30.0):
    """Mỗi tuyến chính (chiều đi) sau khi giao xong sẽ ở gần điểm giao cuối. Tìm
    trong DANH SÁCH ĐƠN BỔ SUNG MỚI (do điều phối nhập) đơn phù hợp để ghép chiều
    về: gần điểm xe rảnh, đủ tải, đúng loại xe, có lãi. KHÔNG dùng đơn cũ trong
    kế hoạch chính."""
    p = {**DEFAULT_PARAMS, **(params or {})}
    fmap = {v["vehicle_id"]: v for v in (fleet or [])}
    results = []
    used = set()
    total_gain = 0.0
    total_empty_avoided = 0.0
    for r in routes or []:
        last = next((s for s in reversed(r.get("stops", [])) if s.get("type") == "delivery"), None)
        depot = (r.get("stops") or [{}])[0]
        if not last:
            continue
        veh = fmap.get(r.get("vehicle_id"), {})
        cap_ton = veh.get("max_weight_kg", 0)
        cap_m3 = veh.get("max_volume_m3", 0)
        empty_home = eng.haversine_km(last["lat"], last["lon"], depot.get("lat"), depot.get("lon"))

        best, best_score = None, None
        for nb in new_orders or []:
            oid = nb.get("order_id")
            if oid in used:
                continue
            if not (nb.get("pickup_lat") and nb.get("delivery_lat")):
                continue
            to_pickup = eng.haversine_km(last["lat"], last["lon"], nb["pickup_lat"], nb["pickup_lon"])
            if to_pickup > r_pickup:
                continue
            if eng._f(nb.get("weight_kg")) > cap_ton or eng._f(nb.get("volume_m3")) > cap_m3:
                continue
            # loại xe phù hợp
            if nb.get("min_vehicle") and eng.veh_rank(veh.get("vehicle_type")) < eng.veh_rank(nb.get("min_vehicle")):
                continue
            # cấm tải chiều về
            ban = False
            if nb.get("inner_city") and eng.veh_rank(veh.get("vehicle_type")) > eng.INNER_CITY_BAN_RANK:
                s, e = nb.get("drop_tw_start", 0), nb.get("drop_tw_end", 1440)
                ban = any(s < b and a < e for a, b in eng.INNER_CITY_BAN_WINDOWS)
            if ban:
                continue
            return_km = (to_pickup +
                         eng.haversine_km(nb["pickup_lat"], nb["pickup_lon"], nb["delivery_lat"], nb["delivery_lon"]) +
                         eng.haversine_km(nb["delivery_lat"], nb["delivery_lon"], depot.get("lat"), depot.get("lon")))
            op_rate = (veh.get("fuel_l_per_km", 0.12) * p["gia_nhien_lieu"] + p["bao_duong_km"])
            cost = return_km * op_rate + p["chi_phi_boc_xep_don"]
            revenue = eng._f(nb.get("revenue"))
            empty_saved = max(0.0, empty_home - 30.0) * op_rate
            gain = revenue + empty_saved - cost
            if gain <= 0:
                continue
            score = max(0, 1 - to_pickup / r_pickup) * 0.6 + min(1, gain / 1e6) * 0.4
            if best_score is None or score > best_score:
                best, best_score = {
                    "order_id": oid, "customer": nb.get("customer"),
                    "pickup_name": nb.get("pickup_name"), "delivery_name": nb.get("delivery_name"),
                    "pickup_lat": nb["pickup_lat"], "pickup_lon": nb["pickup_lon"],
                    "delivery_lat": nb["delivery_lat"], "delivery_lon": nb["delivery_lon"],
                    "weight_kg": eng._f(nb.get("weight_kg")), "min_vehicle": nb.get("min_vehicle"),
                    "to_pickup_km": round(to_pickup, 1),
                    "to_pickup_min": int(round(to_pickup / max(1e-6, veh.get("avg_speed", 45)) * 60)),
                    "return_km": round(return_km, 1),
                    "revenue": round(revenue), "cost": round(cost),
                    "empty_saved": round(empty_saved),
                    "gain": round(gain), "empty_km_avoided": round(max(0.0, empty_home - 30.0), 1),
                    "score": round(score, 3),
                }, score
        if best:
            used.add(best["order_id"])
            total_gain += best["gain"]
            total_empty_avoided += best["empty_km_avoided"]
            results.append({
                "vehicle_id": r.get("vehicle_id"), "vehicle_type": r.get("vehicle_type"),
                "driver": r.get("driver"), "corridor": r.get("corridor"),
                "end_lat": last["lat"], "end_lon": last["lon"],
                "end_name": last.get("name"),
                "free_time": "Sau chiều đi",
                "depot_lat": depot.get("lat"), "depot_lon": depot.get("lon"),
                "match": best,
            })
    return {
        "results": results, "n_matched": len(results),
        "total_gain": round(total_gain),
        "empty_km_avoided": round(total_empty_avoided, 1),
        "n_new_orders": len(new_orders or []),
        "n_routes": len(routes or []),
    }


# ============================================================
# 5. SINH PHƯƠNG ÁN XỬ LÝ SỰ CỐ (engine đề xuất; Dispatcher quyết)
# ============================================================
INCIDENT_TYPES = [
    "Xe hỏng", "Tài xế báo trễ", "Tắc đường", "Cấm tải phát sinh",
    "Khách đổi giờ giao", "Khách đổi địa điểm giao", "Không liên hệ được khách",
    "Điểm giao không nhận hàng", "Thiếu xe", "Thiếu tài xế", "Đơn phát sinh gấp",
    "Đơn bị hủy", "Chi phí vượt ngưỡng", "Rủi ro trễ SLA",
]


def _opt(name, desc, dt=0, dkm=0.0, dcost=0, rec="Trung bình", risk="Thấp", pnl=None):
    return {
        "ten": name, "mo_ta": desc,
        "tac_dong_thoi_gian": dt, "tac_dong_quang_duong": round(dkm, 1),
        "tac_dong_chi_phi": int(dcost),
        "tac_dong_pnl": int(pnl if pnl is not None else -dcost),
        "rui_ro": risk, "khuyen_nghi": rec,
    }


def incident_options(event_type, ctx=None):
    """Trả về danh sách phương án xử lý + hướng xử lý mềm theo loại sự cố.
    ctx có thể chứa rec_vehicle (xe thay thế gần nhất), dist_km, eta_min."""
    ctx = ctx or {}
    rv = ctx.get("rec_vehicle")
    dist = ctx.get("dist_km", 0)
    et = (event_type or "").lower()
    options = []

    if "hỏng" in et or "breakdown" in et or "thiếu xe" in et:
        veh_txt = f" ({rv})" if rv else ""
        options = [
            _opt("Điều xe thay thế gần nhất" + veh_txt,
                 f"Điều xe khả dụng gần điểm sự cố nhất{(' — cách %.1fkm' % dist) if dist else ''}, nhận phần hàng còn lại.",
                 dt=ctx.get("eta_min", 35), dkm=dist, dcost=180000, rec="Cao", risk="Thấp"),
            _opt("Chuyển tải tại điểm an toàn gần nhất",
                 "Tìm điểm dừng an toàn gần xe sự cố để chuyển tải sang xe thay thế.",
                 dt=ctx.get("eta_min", 35) + 20, dcost=260000, rec="Cao", risk="Trung bình"),
            _opt("Tách đơn cho nhiều xe gần khu vực",
                 "Chia hàng cho 2 xe nhỏ đang trống gần đó để kịp khung giờ.",
                 dt=45, dcost=320000, rec="Trung bình", risk="Trung bình"),
            _opt("Đổi thứ tự giao các đơn còn lại",
                 "Ưu tiên đơn SLA gấp trước trong lúc chờ xe thay thế.",
                 dt=15, dcost=40000, rec="Trung bình", risk="Thấp"),
            _opt("Thuê xe ngoài/3PL chặng còn lại",
                 "Khi không có xe nội bộ phù hợp trong bán kính cho phép.",
                 dt=60, dcost=900000, rec="Thấp", risk="Cao"),
        ]
    elif "tắc" in et or "traffic" in et:
        options = [
            _opt("Định tuyến lại theo đường tránh",
                 "Routing engine tính tuyến tránh điểm ùn tắc theo đường bộ.",
                 dt=18, dkm=6, dcost=90000, rec="Cao", risk="Thấp"),
            _opt("Cập nhật ETA & thông báo khách",
                 "Giữ nguyên xe, gửi ETA mới cho khách/kho.",
                 dt=20, dcost=0, rec="Cao", risk="Thấp"),
            _opt("Đổi thứ tự giao để né khung ùn tắc",
                 "Giao đơn ngoài vùng ùn tắc trước, quay lại sau.",
                 dt=10, dcost=30000, rec="Trung bình", risk="Thấp"),
        ]
    elif "cấm tải" in et:
        options = [
            _opt("Chờ ngoài vùng cấm tải đến khi hết khung giờ",
                 "Xe dừng hợp lệ ngoài vùng cấm, vào giao khi hết giờ cấm.",
                 dt=60, dcost=90000, rec="Trung bình", risk="Trung bình"),
            _opt("Đổi khung giờ giao với khách",
                 "Xin khách dời lịch giao ra ngoài khung cấm tải.",
                 dt=0, dcost=0, rec="Cao", risk="Thấp"),
            _opt("Chuyển tải sang xe tải nhỏ ≤1.25 tấn",
                 "Dùng xe được phép vào nội đô trong khung giờ cấm.",
                 dt=30, dcost=240000, rec="Cao", risk="Trung bình"),
            _opt("Định tuyến vòng hợp lệ",
                 "Tuyến vòng tránh khu vực cấm tải theo đường bộ.",
                 dt=25, dkm=8, dcost=120000, rec="Trung bình", risk="Thấp"),
        ]
    elif "đổi giờ" in et or "tw" in et or "late" in et:
        options = [
            _opt("Cập nhật ETA & xác nhận lại với khách",
                 "Cập nhật khung giờ mới, kiểm tra khả thi với lịch xe.",
                 dt=0, dcost=0, rec="Cao", risk="Thấp"),
            _opt("Đổi thứ tự giao trong tuyến",
                 "Sắp xếp lại điểm giao để phù hợp giờ mới.",
                 dt=10, dcost=20000, rec="Cao", risk="Thấp"),
            _opt("Giữ nguyên xe nếu vẫn khả thi",
                 "Không đổi xe nếu thời gian còn đủ.",
                 dt=0, dcost=0, rec="Cao", risk="Thấp"),
            _opt("Ghép với đơn lân cận nếu có lợi",
                 "Tận dụng thời gian chờ để ghép đơn cùng khu vực.",
                 dt=15, dcost=-60000, rec="Trung bình", risk="Thấp", pnl=60000),
        ]
    elif "gấp" in et or "phát sinh" in et:
        veh_txt = f" ({rv})" if rv else ""
        options = [
            _opt("Chèn vào xe gần nhất còn chỗ" + veh_txt,
                 "Tìm xe gần điểm lấy còn tải/thời gian để chèn đơn.",
                 dt=25, dkm=dist, dcost=150000, rec="Cao", risk="Thấp"),
            _opt("Mở tuyến mới cho đơn gấp",
                 "Điều xe trống riêng nếu đơn giá trị cao/đặc thù.",
                 dt=40, dcost=500000, rec="Trung bình", risk="Trung bình"),
            _opt("Đánh giá ảnh hưởng tới đơn hiện có",
                 "Kiểm tra rủi ro trễ các đơn đang trên tuyến trước khi chèn.",
                 dt=0, dcost=0, rec="Cao", risk="Thấp"),
        ]
    else:
        options = [
            _opt("Cập nhật ETA & thông báo các bên",
                 "Giữ kế hoạch, cập nhật thời gian dự kiến.",
                 dt=15, dcost=0, rec="Cao", risk="Thấp"),
            _opt("Điều chỉnh tuyến phần còn lại",
                 "Rolling re-optimization phần chưa hoàn thành.",
                 dt=20, dkm=4, dcost=80000, rec="Trung bình", risk="Thấp"),
            _opt("Điều xe/đổi xe nếu cần thiết",
                 "Chỉ áp dụng khi bắt buộc để bảo vệ SLA.",
                 dt=40, dcost=300000, rec="Thấp", risk="Trung bình"),
        ]

    soft = soft_skill_notes(event_type)
    return {"options": options, "soft_skills": soft}


def soft_skill_notes(event_type):
    et = (event_type or "").lower()
    base = [
        {"tinh_huong": "Thông báo cho khách",
         "huong_dan": "Chủ động gọi sớm, nói rõ nguyên nhân và ETA mới, xin giữ slot giao.",
         "mau_cau": "Dạ anh/chị, đơn [mã đơn] phát sinh [sự cố], bên em đang điều phối xe xử lý, dự kiến giao lúc [giờ], mong anh/chị hỗ trợ giữ lịch giúp em."},
        {"tinh_huong": "Trao đổi với tài xế",
         "huong_dan": "Nêu rõ điểm chuyển tải/điểm đến, phần tải còn lại, yêu cầu xác nhận nhận chuyến.",
         "mau_cau": "Anh xác nhận giúp em điểm chuyển tải tại [địa điểm], nhận [khối lượng] giao cho [điểm giao] trong [thời gian] nhé."},
        {"tinh_huong": "Ghi nhận nguyên nhân sự cố",
         "huong_dan": "Ghi lại nguyên nhân, thời điểm, bên liên quan để phục vụ Close & Learn.",
         "mau_cau": "Nguyên nhân: [...]; thời điểm: [...]; bên liên quan: [...]; biện pháp đã áp dụng: [...]."},
    ]
    if "đổi giờ" in et:
        base.insert(1, {"tinh_huong": "Xin xác nhận đổi giờ giao",
                        "huong_dan": "Đề xuất 1–2 khung giờ thay thế, xác nhận bằng tin nhắn để lưu vết.",
                        "mau_cau": "Bên em đề xuất giao lại vào [khung 1] hoặc [khung 2], anh/chị chọn giúp em khung phù hợp ạ."})
    return base


# ============================================================
# 6. TỐI ƯU TUYẾN THEO PRESET / TRỌNG SỐ (routing engine)
# ============================================================
PRESETS = {
    "dung_gio":   {"ten": "Ưu tiên đúng giờ",            "time": 85, "cost": 35, "empty": 40, "urgent": 80},
    "tiet_kiem":  {"ten": "Ưu tiên tiết kiệm chi phí",   "time": 35, "cost": 90, "empty": 70, "urgent": 40},
    "can_bang":   {"ten": "Cân bằng thời gian và chi phí","time": 60, "cost": 60, "empty": 60, "urgent": 55},
    "giam_rong":  {"ten": "Ưu tiên giảm chạy rỗng",      "time": 45, "cost": 65, "empty": 95, "urgent": 45},
    "loi_nhuan":  {"ten": "Ưu tiên lợi nhuận",           "time": 50, "cost": 75, "empty": 80, "urgent": 50},
    "don_gap":    {"ten": "Ưu tiên xử lý đơn gấp",       "time": 80, "cost": 40, "empty": 45, "urgent": 95},
}


def preset_weights(preset_key):
    p = PRESETS.get(preset_key) or PRESETS["can_bang"]
    return {k: p[k] for k in ("time", "cost", "empty", "urgent")}


def solve_preset(orders, fleet, depots=None, weights=None, radius=30.0):
    """Gán đơn vào xe theo trọng số preset (đúng giờ / chi phí / chạy rỗng / đơn gấp).
    Tôn trọng đầy đủ ràng buộc tương thích (loại xe, tải trọng, dung tích, cấm tải
    theo khung giờ) qua eng._compat. Solver tự gom đơn cùng hành lang để giảm số xe."""
    w = {"time": 50, "cost": 50, "empty": 50, "urgent": 50}
    w.update(weights or {})
    wt, wc, we, wu = w["time"] / 100.0, w["cost"] / 100.0, w["empty"] / 100.0, w["urgent"] / 100.0

    valid = [o for o in orders if o.get("valid", True)]
    avail = eng._avail_fleet(fleet)
    if not valid or not avail:
        return [], [o for o in valid]

    def pri(o):
        p = str(o.get("priority") or "")
        base = 0 if p.startswith("A") else (1 if p.startswith("B") else 2)
        return base - wu  # urgent cao -> kéo đơn ưu tiên lên trước

    pending = sorted(valid, key=lambda o: (pri(o), -eng._f(o.get("revenue"))))
    open_routes, unassigned = [], []

    def can_fit(slot, o):
        veh = slot["veh"]
        if not eng._compat(o, veh, True):
            return False
        if len(slot["orders"]) >= veh["max_stops"]:
            return False
        if slot["weight"] + o["weight_kg"] > veh["max_weight_kg"]:
            return False
        if slot["volume"] + o["volume_m3"] > veh["max_volume_m3"]:
            return False
        return True

    for o in pending:
        best_slot, best_cost = None, None
        for slot in open_routes:
            if not can_fit(slot, o):
                continue
            last = slot["orders"][-1]
            d = eng.haversine_km(last["delivery_lat"], last["delivery_lon"],
                                 o["pickup_lat"], o["pickup_lon"])
            corridor_pen = 0 if slot["veh"].get("corridor") == o.get("corridor") else 22
            # gom thêm vào xe đang chạy giúp giảm chạy rỗng & chi phí cố định
            cost = d * (wc + we) + corridor_pen * we - 8 * (wc + we)
            if best_cost is None or cost < best_cost:
                best_slot, best_cost = slot, cost
        if best_slot is not None:
            best_slot["orders"].append(o)
            best_slot["weight"] += o["weight_kg"]
            best_slot["volume"] += o["volume_m3"]
            continue

        cand, cand_cost = None, None
        used_ids = {s["veh"]["vehicle_id"] for s in open_routes}
        for veh in avail:
            if veh["vehicle_id"] in used_ids:
                continue
            tmp = {"veh": veh, "orders": [], "weight": 0.0, "volume": 0.0}
            if not can_fit(tmp, o):
                continue
            d = eng.haversine_km(veh["lat"], veh["lon"], o["pickup_lat"], o["pickup_lon"])
            corridor_pen = 0 if veh.get("corridor") == o.get("corridor") else 18
            oversize_pen = max(0, eng.veh_rank(veh["vehicle_type"]) - eng.veh_rank(o["min_vehicle"])) * 8
            cost = d * (we + wt) + corridor_pen * we + oversize_pen * wc
            if cand_cost is None or cost < cand_cost:
                cand, cand_cost = veh, cost
        if cand:
            open_routes.append({"veh": cand, "orders": [o],
                                "weight": o["weight_kg"], "volume": o["volume_m3"]})
        else:
            unassigned.append(o)

    routes = [eng._assemble_route(s["veh"], s["orders"], depots) for s in open_routes]
    return routes, unassigned


def unassigned_reason(o, fleet):
    """Suy luận lý do một đơn chưa gán được (đường bộ / năng lực / cấm tải...)."""
    if not (o.get("pickup_lat") and o.get("delivery_lat")):
        return ("Địa chỉ chưa xác định được tọa độ",
                "Bổ sung tọa độ điểm lấy/giao hoặc geocode lại địa chỉ.")
    avail = eng._avail_fleet(fleet)
    if not avail:
        return ("Không đủ xe", "Bổ sung xe khả dụng hoặc thuê xe ngoài/3PL.")
    type_ok = any(eng.veh_rank(v["vehicle_type"]) >= eng.veh_rank(o.get("min_vehicle")) for v in avail)
    if not type_ok:
        return ("Không có xe phù hợp", "Điều xe loại lớn hơn hoặc thuê xe ngoài phù hợp loại hàng.")
    cap_ok = any(o.get("weight_kg", 0) <= v["max_weight_kg"] and o.get("volume_m3", 0) <= v["max_volume_m3"]
                 for v in avail)
    if not cap_ok:
        return ("Không đủ tải trọng", "Tách đơn cho nhiều xe hoặc dùng xe tải lớn hơn.")
    if eng.road_ban_conflict(o):
        return ("Vi phạm giờ cấm tải",
                "Đổi khung giờ giao, dùng xe ≤1.25 tấn hoặc chuyển tải.")
    if o.get("direct_km", 0) > 100:
        return ("Tuyến dài, cần kiểm tra chiều về",
                "Xem xét ghép chuyến quay đầu (Module 4) để đảm bảo hiệu quả.")
    return ("Không đủ thời gian giao hàng",
            "Đổi thứ tự giao, nới khung giờ hoặc điều thêm xe.")


# ============================================================
# 7. NGỮ CẢNH CHO TRỢ LÝ AI (bám dữ liệu thực trong phiên)
# ============================================================
def build_ai_context(store, loader_log=None):
    routes = store.get("_routes") or []
    fin = store.get("_financial") or {}
    incidents = store.get("incidents") or []
    new_bk = store.get("new_backhaul_orders") or []
    ctx = {
        "kich_ban": store.get("_scenario"),
        "so_tuyen": len(routes),
        "tuyen": [{
            "xe": r.get("vehicle_id"), "loai_xe": r.get("vehicle_type"),
            "tai_xe": r.get("driver"), "hanh_lang": r.get("corridor"),
            "so_don": r.get("n_orders"), "don": r.get("orders"),
            "km": r.get("distance_km"),
            "fill_tai": r.get("fill_weight_pct"),
            "loi_nhuan": (r.get("pnl") or {}).get("profit"),
            "bien": (r.get("pnl") or {}).get("margin"),
        } for r in routes],
        "tai_chinh": (fin.get("totals") if fin else None),
        "so_su_co": len(incidents),
        "su_co": [{"ma": i.get("case_id"), "don": i.get("order_id"),
                   "loai": i.get("event_type"), "trang_thai": i.get("status")}
                  for i in incidents],
        "don_bo_sung_quay_dau": len(new_bk),
    }
    return ctx
