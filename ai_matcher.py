# -*- coding: utf-8 -*-
"""
AI MATCHER (ai_matcher.py) — LỚP THUẬT TOÁN MATCHING / SCORING / ĐỀ XUẤT
=======================================================================
ĐÂY KHÔNG PHẢI CHATBOT. Đây là lớp tính toán điều phối thuần thuật toán,
trả kết quả CÓ CẤU TRÚC (dict/JSON) để `gemini_ai.py` diễn giải thành câu
trả lời cho điều phối viên.

Trách nhiệm:
  • Tính điểm phù hợp xe ↔ đơn (score_vehicle_order_match).
  • Tính điểm ghép chuyến quay đầu / backhaul (score_backhaul_match).
  • Kiểm tra ràng buộc vận hành (tải, dung tích, loại xe, khung giờ, depot).
  • Kiểm tra cấm đường / cấm tải (check_road_restrictions).
  • Tính km rỗng giảm được và lợi nhuận bổ sung theo GIÁ NHIÊN LIỆU hiện hành.
  • Đề xuất ghép backhaul, điều phối lại khi sự cố, xếp hạng đơn chưa gán,
    quyết định dùng xe standby.

NGUYÊN TẮC:
  • Mọi đề xuất xét ĐỒNG THỜI: thời gian, khoảng cách, tải trọng, loại xe,
    depot, fill-rate, chi phí nhiên liệu, lợi nhuận, km rỗng, ràng buộc cấm tải.
  • KHÔNG tối ưu chỉ theo khoảng cách.
  • Vi phạm ràng buộc CỨNG (tải/dung tích/loại xe/cấm tải) -> loại phương án.
  • Kết quả luôn kèm `score`, `violations`, `reason`, `decision` rõ ràng.

Không gọi mạng, không gọi LLM. Chỉ dùng hpl_engine cho hàm hình học/ràng buộc.
"""

import hpl_engine as eng

# ------------------------------------------------------------
# Tham số mặc định (đồng bộ với engine_ext.DEFAULT_PARAMS)
# ------------------------------------------------------------
DEFAULTS = {
    "fuel_price": 27500,          # đ/lít — giá cấu hình mặc định (chỉnh tay tại Module 5)
    "fuel_l_per_km": 0.12,        # lít/km mặc định nếu xe không khai báo
    "maint_per_km": 1400,         # đ/km — bảo dưỡng + hao mòn chiều vận hành
    "handling_per_order": 50000,  # đ/đơn — bốc + dỡ
    "free_reposition_km": 30.0,   # km rỗng ngắn coi là điều xe về depot (đã gồm chi phí cố định)
    "r_pickup": 30.0,             # bán kính tối đa từ điểm xe rảnh tới điểm lấy backhaul
    "standby_reserve": 4,         # số xe dự phòng mong muốn (3–5)
}

# Quyết định chuẩn hóa (tiếng Việt) theo điểm số / vi phạm
DECISION_RECOMMEND = "Đề xuất ghép"
DECISION_CONSIDER = "Cân nhắc"
DECISION_REJECT = "Không ghép"


def _veh_fuel_l_per_km(vehicle):
    return eng._f((vehicle or {}).get("fuel_l_per_km"), DEFAULTS["fuel_l_per_km"]) or DEFAULTS["fuel_l_per_km"]


def _veh_speed(vehicle):
    return eng._f((vehicle or {}).get("avg_speed"), 45) or 45


def _op_rate(vehicle, fuel_price):
    """Đơn giá vận hành biến đổi (đ/km): nhiên liệu + bảo dưỡng/hao mòn."""
    fp = eng._f(fuel_price, DEFAULTS["fuel_price"]) or DEFAULTS["fuel_price"]
    return _veh_fuel_l_per_km(vehicle) * fp + DEFAULTS["maint_per_km"]


def _last_delivery(route):
    return next((s for s in reversed(route.get("stops", []) or []) if s.get("type") == "delivery"), None)


def _route_depot(route):
    stops = route.get("stops") or []
    return stops[0] if stops else {"lat": route.get("depot_lat"), "lon": route.get("depot_lon")}


def _tw_overlap(s1, e1, s2, e2):
    """Hai khoảng [s1,e1] và [s2,e2] có giao nhau không."""
    return s1 < e2 and s2 < e1


# ============================================================
# 1. RÀNG BUỘC VẬN HÀNH (tải / dung tích / loại xe / lạnh)
# ============================================================
def check_operational_constraints(vehicle, order, route=None):
    """Kiểm tra ràng buộc CỨNG giữa xe và đơn (có tính tải đang có trên tuyến).
    Trả về {ok, violations, headroom_ton, headroom_m3}."""
    v = vehicle or {}
    violations = []
    cap_w = eng._f(v.get("max_weight_kg"))
    cap_v = eng._f(v.get("max_volume_m3"))
    used_w = eng._f((route or {}).get("total_weight"))
    used_v = eng._f((route or {}).get("total_volume"))
    w = eng._f(order.get("weight_kg"))
    vol = eng._f(order.get("volume_m3"))

    if eng.veh_rank(v.get("vehicle_type")) < eng.veh_rank(order.get("min_vehicle")):
        violations.append("Loại xe nhỏ hơn yêu cầu tối thiểu của đơn")
    if used_w + w > cap_w + 1e-6:
        violations.append("Vượt tải trọng cho phép")
    if cap_v > 0 and used_v + vol > cap_v + 1e-6:
        violations.append("Vượt dung tích cho phép")
    if order.get("need_refrigeration") and not v.get("refrigerated", False):
        violations.append("Đơn cần xe lạnh, xe không có khả năng giữ lạnh")

    return {
        "ok": not violations,
        "violations": violations,
        "headroom_ton": round(max(0.0, cap_w - used_w - w) / 1000.0, 2),
        "headroom_m3": round(max(0.0, cap_v - used_v - vol), 2),
    }


# ============================================================
# 2. CẤM ĐƯỜNG / CẤM TẢI
# ============================================================
def check_road_restrictions(order, vehicle):
    """Kiểm tra cấm tải nội đô theo khung giờ (dùng đúng cửa sổ cấm đang cấu hình
    trong eng.INNER_CITY_BAN_WINDOWS). Trả về {ok, violations}."""
    violations = []
    inner = order.get("inner_city")
    if inner and eng.veh_rank((vehicle or {}).get("vehicle_type")) > eng.INNER_CITY_BAN_RANK:
        s = eng._f(order.get("drop_tw_start"), 0)
        e = eng._f(order.get("drop_tw_end"), 1440)
        for a, b in eng.INNER_CITY_BAN_WINDOWS:
            if _tw_overlap(s, e, a, b):
                violations.append(f"Vi phạm cấm tải nội đô {eng.min_to_hhmm(a)}–{eng.min_to_hhmm(b)} (xe > 1.25T)")
                break
    return {"ok": not violations, "violations": violations}


# ============================================================
# 3. KM RỖNG GIẢM ĐƯỢC + LỢI NHUẬN BỔ SUNG
# ============================================================
def calculate_empty_km_reduction(route, backhaul_order):
    """Km rỗng (deadhead) chiều về vốn có, và phần giảm được khi ghép backhaul.
    Trả về {empty_home_km, to_pickup_km, empty_km_reduced}."""
    last = _last_delivery(route)
    depot = _route_depot(route)
    if not last or depot.get("lat") is None:
        return {"empty_home_km": 0.0, "to_pickup_km": 0.0, "empty_km_reduced": 0.0}
    empty_home = eng.haversine_km(last["lat"], last["lon"], depot.get("lat"), depot.get("lon"))
    to_pickup = eng.haversine_km(last["lat"], last["lon"],
                                 backhaul_order.get("pickup_lat"), backhaul_order.get("pickup_lon"))
    reduced = max(0.0, empty_home - DEFAULTS["free_reposition_km"])
    return {"empty_home_km": round(empty_home, 1),
            "to_pickup_km": round(to_pickup, 1),
            "empty_km_reduced": round(reduced, 1)}


def calculate_incremental_profit(route, backhaul_order, vehicle, fuel_price=None):
    """Lợi nhuận bổ sung khi ghép 1 đơn backhaul vào chiều về của tuyến.
    LN bổ sung = Doanh thu đơn + Giá trị tiết kiệm km rỗng − Chi phí đi ghép.
    Tất cả chi phí nhiên liệu tính theo GIÁ NHIÊN LIỆU truyền vào (cập nhật động)."""
    fp = eng._f(fuel_price, DEFAULTS["fuel_price"]) or DEFAULTS["fuel_price"]
    op = _op_rate(vehicle, fp)
    em = calculate_empty_km_reduction(route, backhaul_order)
    depot = _route_depot(route)
    leg = eng.haversine_km(backhaul_order.get("pickup_lat"), backhaul_order.get("pickup_lon"),
                           backhaul_order.get("delivery_lat"), backhaul_order.get("delivery_lon"))
    to_home = eng.haversine_km(backhaul_order.get("delivery_lat"), backhaul_order.get("delivery_lon"),
                               depot.get("lat"), depot.get("lon"))
    return_km = em["to_pickup_km"] + leg + to_home
    revenue_add = eng._f(backhaul_order.get("revenue"))
    cost_add = return_km * op + DEFAULTS["handling_per_order"]
    empty_saved_value = em["empty_km_reduced"] * op
    profit_add = revenue_add + empty_saved_value - cost_add
    return {
        "return_km": round(return_km, 1),
        "op_rate": round(op),
        "revenue_add": round(revenue_add),
        "cost_add": round(cost_add),
        "empty_saved_value": round(empty_saved_value),
        "empty_km_reduced": em["empty_km_reduced"],
        "to_pickup_km": em["to_pickup_km"],
        "profit_add": round(profit_add),
    }


def _fill_pct(weight, cap):
    cap = eng._f(cap)
    return round(100.0 * eng._f(weight) / cap, 1) if cap > 0 else 0.0


# ============================================================
# 4. ĐIỂM PHÙ HỢP XE ↔ ĐƠN (gán đơn lẻ / đơn chưa gán)
# ============================================================
def score_vehicle_order_match(vehicle, order, route=None, fuel_price=None):
    """Điểm 0–100 cho việc xe nhận MỘT đơn. Xét: loại xe, tải, dung tích, cấm tải,
    khoảng cách điều xe tới điểm lấy, cùng hành lang, mức tăng fill-rate."""
    v = vehicle or {}
    oc = check_operational_constraints(v, order, route)
    rr = check_road_restrictions(order, v)
    violations = oc["violations"] + rr["violations"]
    if violations:
        return {"vehicle_id": v.get("vehicle_id"), "order_id": order.get("order_id"),
                "score": 0.0, "has_violation": True, "violations": violations,
                "decision": DECISION_REJECT, "reason": "; ".join(violations)}

    # khoảng cách điều xe tới điểm lấy
    vlat = v.get("lat"); vlon = v.get("lon")
    if route and route.get("stops"):
        last = _last_delivery(route) or _route_depot(route)
        vlat, vlon = last.get("lat", vlat), last.get("lon", vlon)
    to_pickup = eng.haversine_km(vlat, vlon, order.get("pickup_lat"), order.get("pickup_lon"))
    dist_score = max(0.0, 1 - to_pickup / max(1.0, DEFAULTS["r_pickup"] * 3))

    corridor_score = 1.0 if (v.get("corridor") and v.get("corridor") == order.get("corridor")) else 0.5
    rank_gap = eng.veh_rank(v.get("vehicle_type")) - eng.veh_rank(order.get("min_vehicle"))
    type_score = 1.0 if rank_gap == 0 else max(0.3, 1 - 0.15 * rank_gap)  # phạt điều xe quá lớn cho đơn nhỏ
    fill_after = _fill_pct(eng._f((route or {}).get("total_weight")) + eng._f(order.get("weight_kg")),
                           v.get("max_weight_kg"))
    fill_score = min(1.0, fill_after / 85.0)  # khuyến khích đạt ~85% tải

    score = 100 * (0.34 * dist_score + 0.20 * corridor_score +
                   0.20 * type_score + 0.26 * fill_score)
    decision = DECISION_RECOMMEND if score >= 62 else (DECISION_CONSIDER if score >= 45 else DECISION_REJECT)
    bits = []
    if dist_score > 0.6:
        bits.append(f"điều xe ngắn (~{round(to_pickup,1)}km tới điểm lấy)")
    if corridor_score == 1.0:
        bits.append("cùng tuyến")
    if rank_gap == 0:
        bits.append("đúng loại xe")
    elif rank_gap > 0:
        bits.append("xe lớn hơn yêu cầu (lãng phí tải)")
    bits.append(f"fill-rate dự kiến {fill_after}%")
    return {"vehicle_id": v.get("vehicle_id"), "order_id": order.get("order_id"),
            "score": round(score, 1), "has_violation": False, "violations": [],
            "to_pickup_km": round(to_pickup, 1), "fill_after": fill_after,
            "decision": decision, "reason": "Phù hợp vì " + ", ".join(bits) + "."}


# ============================================================
# 5. ĐIỂM GHÉP BACKHAUL (đơn chiều về)
# ============================================================
def score_backhaul_match(route, backhaul_order, vehicle, fuel_price=None, r_pickup=None):
    """Điểm 0–100 cho việc ghép 1 đơn backhaul vào chiều về của 1 tuyến.
    Hard-constraint: tải/dung tích/loại xe/cấm tải/bán kính/lợi nhuận dương.
    Soft-score: gần điểm rảnh + lợi nhuận + tăng fill + giảm km rỗng + khung giờ."""
    r_pickup = eng._f(r_pickup, DEFAULTS["r_pickup"]) or DEFAULTS["r_pickup"]
    v = vehicle or {}
    last = _last_delivery(route)
    if not last:
        return None

    oc = check_operational_constraints(v, backhaul_order, route=None)  # backhaul đi sau khi đã dỡ chiều đi
    rr = check_road_restrictions(backhaul_order, v)
    violations = list(oc["violations"]) + list(rr["violations"])

    em = calculate_empty_km_reduction(route, backhaul_order)
    to_pickup = em["to_pickup_km"]
    if to_pickup > r_pickup:
        violations.append(f"Điểm lấy chiều về quá xa điểm xe rảnh ({to_pickup}km > bán kính {round(r_pickup)}km)")

    fin = calculate_incremental_profit(route, backhaul_order, v, fuel_price)
    if fin["profit_add"] <= 0:
        violations.append("Lợi nhuận bổ sung không dương")

    # Fill-rate CHIỀU VỀ: trước ghép xe chạy rỗng (0%), sau ghép chở đơn backhaul.
    fill_before = 0.0
    fill_after = _fill_pct(backhaul_order.get("weight_kg"), v.get("max_weight_kg"))
    speed = _veh_speed(v)
    wait_min = 0  # khung giờ backhaul thường mở; nếu có TW chặt sẽ phản ánh ở khung giờ

    base = {
        "vehicle_id": v.get("vehicle_id") or route.get("vehicle_id"),
        "route_id": route.get("vehicle_id"),
        "order_id": backhaul_order.get("order_id"),
        "customer": backhaul_order.get("customer"),
        "pickup_name": backhaul_order.get("pickup_name"),
        "delivery_name": backhaul_order.get("delivery_name"),
        "pickup_lat": backhaul_order.get("pickup_lat"), "pickup_lon": backhaul_order.get("pickup_lon"),
        "delivery_lat": backhaul_order.get("delivery_lat"), "delivery_lon": backhaul_order.get("delivery_lon"),
        "to_pickup_km": to_pickup,
        "to_pickup_min": int(round(to_pickup / max(1e-6, speed) * 60)),
        "return_km": fin["return_km"], "wait_min": wait_min,
        "fill_before": fill_before, "fill_after": fill_after,
        "revenue_add": fin["revenue_add"], "cost_add": fin["cost_add"],
        "profit_add": fin["profit_add"], "empty_km_reduced": fin["empty_km_reduced"],
        "min_vehicle": backhaul_order.get("min_vehicle"),
        "weight_kg": eng._f(backhaul_order.get("weight_kg")),
    }

    if violations:
        base.update({"score": 0.0, "has_violation": True, "violations": violations,
                     "decision": DECISION_REJECT,
                     "reason": "Không ghép vì " + "; ".join(violations) + "."})
        return base

    dist_s = max(0.0, 1 - to_pickup / r_pickup)
    profit_s = min(1.0, fin["profit_add"] / 500000.0)
    fill_s = min(1.0, max(0.0, (fill_after - fill_before)) / 40.0)
    empty_s = min(1.0, fin["empty_km_reduced"] / 50.0)
    rank_gap = eng.veh_rank(v.get("vehicle_type")) - eng.veh_rank(backhaul_order.get("min_vehicle"))
    type_s = 1.0 if rank_gap == 0 else max(0.4, 1 - 0.15 * max(0, rank_gap))
    time_s = 1.0  # đã không vi phạm khung giờ cấm tải
    score = 100 * (0.30 * dist_s + 0.25 * profit_s + 0.15 * fill_s +
                   0.15 * empty_s + 0.08 * type_s + 0.07 * time_s)
    decision = DECISION_RECOMMEND if score >= 58 else DECISION_CONSIDER

    reasons = [f"gần điểm xe rảnh (~{to_pickup}km)",
               f"fill-rate chiều về {fill_before:.0f}%→{fill_after:.0f}%",
               f"giảm ~{fin['empty_km_reduced']}km chạy rỗng",
               f"lợi nhuận thêm ~{fin['profit_add']:,}đ".replace(",", ".")]
    base.update({"score": round(score, 1), "has_violation": False, "violations": [],
                 "decision": decision, "reason": "Ưu tiên vì " + ", ".join(reasons) + "."})
    return base


# ============================================================
# 6. ĐỀ XUẤT GHÉP BACKHAUL CHO TOÀN BỘ TUYẾN
# ============================================================
def recommend_backhaul_matches(routes, backhaul_orders, fleet, fuel_price=None, r_pickup=None):
    """Với mỗi tuyến chính (chiều đi), tìm trong DANH SÁCH ĐƠN BỔ SUNG đơn ghép
    chiều về tối ưu nhất (greedy, không gán trùng đơn). Trả kết quả có cấu trúc."""
    r_pickup = eng._f(r_pickup, DEFAULTS["r_pickup"]) or DEFAULTS["r_pickup"]
    fmap = {v.get("vehicle_id"): v for v in (fleet or [])}
    used, results = set(), []
    total_gain = 0.0
    total_empty = 0.0
    for r in routes or []:
        veh = fmap.get(r.get("vehicle_id"), {})
        best = None
        for nb in backhaul_orders or []:
            oid = nb.get("order_id")
            if oid in used:
                continue
            if not (nb.get("pickup_lat") and nb.get("delivery_lat")):
                continue
            m = score_backhaul_match(r, nb, veh, fuel_price, r_pickup)
            if not m or m.get("has_violation"):
                continue
            if best is None or m["score"] > best["score"]:
                best = m
        if best:
            used.add(best["order_id"])
            total_gain += best["profit_add"]
            total_empty += best["empty_km_reduced"]
            last = _last_delivery(r) or {}
            depot = _route_depot(r)
            results.append({
                "vehicle_id": r.get("vehicle_id"), "vehicle_type": r.get("vehicle_type"),
                "driver": r.get("driver"), "corridor": r.get("corridor"),
                "end_lat": last.get("lat"), "end_lon": last.get("lon"), "end_name": last.get("name"),
                "depot_lat": depot.get("lat"), "depot_lon": depot.get("lon"),
                "match": best,
            })
    results.sort(key=lambda x: -x["match"]["score"])
    return {
        "results": results, "n_matched": len(results),
        "total_gain": round(total_gain), "empty_km_avoided": round(total_empty, 1),
        "n_new_orders": len(backhaul_orders or []), "n_routes": len(routes or []),
        "fuel_price": eng._f(fuel_price, DEFAULTS["fuel_price"]),
    }


# ============================================================
# 7. ĐIỀU PHỐI LẠI KHI CÓ SỰ CỐ (xe thay thế / standby)
# ============================================================
def recommend_reassignment_for_incident(incident, vehicles, routes=None, fuel_price=None):
    """Xếp hạng xe thay thế cho 1 sự cố. incident cần có: incident_lat/lon (hoặc
    delivery_lat/lon), req_ton, req_m3, min_vehicle. Trả về options + recommended."""
    inc = incident or {}
    ilat = inc.get("incident_lat", inc.get("delivery_lat"))
    ilon = inc.get("incident_lon", inc.get("delivery_lon"))
    req_ton = eng._f(inc.get("req_ton"))
    req_m3 = eng._f(inc.get("req_m3"))
    need_rank = eng.veh_rank(inc.get("min_vehicle"))
    rmax = eng._f(inc.get("radius_max"), 30) or 30
    used_ids = set()
    for r in routes or []:
        used_ids.add(r.get("vehicle_id"))

    options = []
    for v in vehicles or []:
        if ilat is None or v.get("lat") is None:
            continue
        d = eng.haversine_km(v["lat"], v["lon"], ilat, ilon)
        # Ưu tiên tải CÒN LẠI khi > 0; nếu khuyết/0 (ô Excel trống -> key vẫn tồn tại =0)
        # thì lùi về tải tối đa. Dùng .get(default) trực tiếp KHÔNG lùi được khi key có mặt=0.
        rt = eng._f(v.get("remain_ton"))
        avail_ton = rt if rt > 0 else eng._f(v.get("max_ton"), eng._f(v.get("max_weight_kg")) / 1000.0)
        rm = eng._f(v.get("remain_m3"))
        avail_m3 = rm if rm > 0 else eng._f(v.get("max_m3"), eng._f(v.get("max_volume_m3")))
        cap_ok = avail_ton >= req_ton and avail_m3 >= req_m3 and eng.veh_rank(v.get("vehicle_type")) >= need_rank
        within = d <= rmax
        status = str(v.get("status", "")).strip().lower()
        is_standby = status in ("standby", "dự phòng", "du phong")
        is_free = status in ("available", "sẵn sàng", "san sang", "standby", "dự phòng", "du phong")
        not_busy = v.get("vehicle_id") not in used_ids
        eta = int(round(d / 35.0 * 60))
        feasible = within and cap_ok and is_free
        dist_s = max(0.0, 1 - d / max(1.0, rmax))
        score = 100 * (0.45 * dist_s + 0.30 * (1 if cap_ok else 0) +
                       0.15 * (1 if within else 0) + 0.10 * (1 if not_busy else 0))
        reasons = [f"cách {round(d,1)}km (ETA ~{eta}')"]
        reasons.append("đủ tải/loại xe" if cap_ok else "KHÔNG đủ tải/loại xe")
        if is_standby:
            reasons.append("xe standby (giữ dự phòng)")
        if not not_busy:
            reasons.append("đang chạy tuyến khác")
        options.append({
            "vehicle_id": v.get("vehicle_id"), "vehicle_type": v.get("vehicle_type"),
            "driver": v.get("driver") or v.get("driver_name"),
            "dist_km": round(d, 2), "eta_min": eta, "capacity_ok": cap_ok,
            "within_radius": within, "is_standby": is_standby, "is_free": is_free,
            "available_now": not_busy, "score": round(score, 1), "feasible": feasible,
            "reason": ", ".join(reasons),
        })
    options.sort(key=lambda x: (-int(x["feasible"]), -x["score"]))
    recommended = next((o for o in options if o["feasible"]), (options[0] if options else None))
    return {"options": options[:8], "recommended": recommended,
            "n_candidates": len(options),
            "event_type": inc.get("event_type"), "order_id": inc.get("order_id")}


# ============================================================
# 8. XẾP HẠNG ĐƠN CHƯA GÁN
# ============================================================
def rank_unassigned_orders(unassigned_orders, fleet, routes=None):
    """Xếp hạng khả năng xử lý các đơn chưa gán + lý do + gợi ý. Đơn dễ xử lý
    (chỉ thiếu thời gian/điều xe) xếp trên đơn vi phạm cứng (tải/loại xe/cấm tải)."""
    import engine_ext as ext  # lazy để tránh phụ thuộc vòng
    out = []
    for o in unassigned_orders or []:
        reason, suggestion = ext.unassigned_reason(o, fleet)
        # điểm "dễ xử lý": vi phạm cứng -> thấp; chỉ thiếu thời gian/điều xe -> cao
        hard = any(k in reason for k in ("Không đủ tải", "Không đủ xe", "Không có xe phù hợp", "cấm tải", "tọa độ"))
        base = 30.0 if hard else 70.0
        if "thời gian" in reason:
            base = 60.0
        if "chiều về" in reason:
            base = 55.0
        out.append({
            "order_id": o.get("order_id"), "pickup_name": o.get("pickup_name"),
            "delivery_name": o.get("delivery_name"), "weight_kg": eng._f(o.get("weight_kg")),
            "min_vehicle": o.get("min_vehicle"), "reason": reason, "suggestion": suggestion,
            "handle_score": base, "hard_block": hard,
        })
    out.sort(key=lambda x: -x["handle_score"])
    return {"orders": out, "n": len(out)}


# ============================================================
# 9. ĐỀ XUẤT DÙNG XE STANDBY
# ============================================================
def select_standby_fleet(fleet, used_vehicle_ids, reserve=None):
    """Chọn các xe KHÔNG dùng trong kế hoạch làm xe standby (giữ 3–5 xe dự phòng
    cho đơn phát sinh / sự cố). Trả về danh sách xe standby."""
    reserve = int(eng._f(reserve, DEFAULTS["standby_reserve"]) or DEFAULTS["standby_reserve"])
    used = set(used_vehicle_ids or [])
    free = [v for v in (fleet or [])
            if v.get("vehicle_id") not in used
            and str(v.get("status", "Available")).strip().lower() in ("available", "sẵn sàng", "san sang")]
    return free[:max(reserve, 0)] if reserve else free


def recommend_standby_vehicle_usage(incident, standby_vehicles, fuel_price=None):
    """Quyết định có nên dùng xe standby cho sự cố không. Ưu tiên giữ tối thiểu 3
    xe dự phòng; chỉ dùng standby khi thật cần và có xe khả thi gần điểm sự cố."""
    rec = recommend_reassignment_for_incident(incident, standby_vehicles, None, fuel_price)
    best = rec["recommended"]
    n = len(standby_vehicles or [])
    if not best or not best.get("feasible"):
        return {"use_standby": False, "recommended": best, "reserve_left": n,
                "reason": "Không có xe standby khả thi gần điểm sự cố — nên giữ kế hoạch hoặc thuê ngoài/3PL."}
    reserve_left = max(0, n - 1)
    note = "Nên dùng xe standby vì kịp ETA và đủ tải."
    if reserve_left < 3:
        note += f" Lưu ý: sau khi điều xe, chỉ còn {reserve_left} xe dự phòng (dưới ngưỡng 3 xe)."
    return {"use_standby": True, "recommended": best, "reserve_left": reserve_left, "reason": note}


# ============================================================
# 10. TỰ XÁC ĐỊNH CÂU HỎI CÓ CẦN MATCHER KHÔNG (cho gemini_ai)
# ============================================================
MATCH_KEYWORDS = [
    "ghép", "quay đầu", "chiều về", "backhaul", "xe nào", "thay thế", "điều phối lại",
    "tái điều phối", "gán", "standby", "dự phòng", "km rỗng", "chạy rỗng",
    "fill", "tối ưu", "sự cố", "đơn gấp", "phát sinh", "lợi nhuận thêm", "giảm chi phí",
]


def needs_matcher(question):
    q = (question or "").lower()
    return any(k in q for k in MATCH_KEYWORDS)
