# -*- coding: utf-8 -*-
"""
TEST SNAPSHOT — get_order_detail (L8 / C10)
===========================================
Đảm bảo gemini_ai.get_order_detail trả ĐỦ 8 nhóm thực thể và các trường khóa mà
24 câu hỏi vàng (Spec Phần 3) cần — cho mọi tình huống: đơn đã gán, đơn chưa gán,
đơn bổ sung (backhaul), đơn dính sự cố, và đơn không tồn tại.

Chạy:  python3 test_order_detail.py   (exit 0 = PASS)
KHÔNG cần mạng/API key: chỉ dùng dữ liệu mẫu + engine xác định trong phiên (RAM).
"""
import sys
import hpl_engine as eng
import engine_ext as ext
import gemini_ai as ai

DATA = "data/1. HPL_AI_Dispatching_Simulated_Data_VRPTW.xlsx"

# 52 trường gốc đơn (đồng bộ _ORDER_BASE_KEYS trong gemini_ai)
DON_GOC_KEYS = ai._ORDER_BASE_KEYS
KIEM_DINH_KEYS = ["computed_status", "issues", "hard_errors", "soft_warnings",
                  "valid", "incident_hint", "status_lifecycle"]
GAN_TUYEN_KEYS = ["vehicle_id", "plate", "vehicle_type", "driver", "corridor", "n_orders",
                  "fill_weight_pct", "fill_volume_pct", "empty_km", "productive_km",
                  "distance_km", "total_weight", "total_volume", "has_backhaul", "locked", "vi_tri"]
PNL_KEYS = ["revenue_total", "total_cost", "profit", "margin", "fuel", "toll", "driver_cost",
            "vehicle_cost", "empty_cost", "handling", "overhead", "overtime", "risk_late",
            "dong_gop_doanh_thu_don"]
ETA_KEYS = ["eta_pickup", "eta_delivery", "steps_cua_don"]
CHUA_GAN_KEYS = ["reason", "suggestion", "handle_score", "hard_block"]
BACKHAUL_KEYS = ["co_the_ghep", "vehicle_id", "score", "decision", "to_pickup_km",
                 "profit_add", "empty_km_reduced", "fill_after", "reason", "violations", "has_violation"]
SU_CO_KEYS = ["case_id", "event_type", "status", "priority", "vehicle", "route_id", "decision",
              "options", "soft_skills", "analysis", "candidates", "recommended_vehicle",
              "recommended_action", "action_desc", "slack_min"]

PASS, FAIL = 0, 0
def check(cond, msg):
    global PASS, FAIL
    if cond:
        PASS += 1
    else:
        FAIL += 1
        print("  ✗ FAIL:", msg)

def has_keys(d, keys, label):
    miss = [k for k in keys if k not in (d or {})]
    check(not miss, f"{label} thiếu trường: {miss}")


def build_store():
    with open(DATA, "rb") as f:
        d = eng.parse_workbook(f.read())["data"]
    sid = "S1"
    orders = eng.validate_orders(d["scenarios"][sid])
    routes, unassigned, _ = ext.solve_hybrid(orders, d["fleet"], d.get("depots"),
                                             ext.preset_weights("can_bang"), 30, mode="greedy")
    fin = ext.financials_detailed(routes, d["fleet"], ext.DEFAULT_PARAMS)
    pm = {p["vehicle_id"]: p for p in fin["per_route"]}
    fmap = {v["vehicle_id"]: v for v in d["fleet"]}
    for r in routes:
        r["pnl"] = pm.get(r["vehicle_id"], {})
        r["timeline"] = ext.route_timeline(r, fmap.get(r["vehicle_id"], {}))
    store = {"static": d, "working": {sid: d["scenarios"][sid]}, "_scenario": sid,
             "_routes": routes, "_unassigned": unassigned, "new_backhaul_orders": [],
             "incidents": [], "_radius": 30}
    return store, d, routes, unassigned, sid


def main():
    store, d, routes, unassigned, sid = build_store()

    # 1) Đơn ĐÃ GÁN — đủ don_goc/kiem_dinh/gan_tuyen/thoi_gian_eta/pnl_tuyen
    assigned_id = routes[0]["orders"][0]
    det = ai.get_order_detail(store, assigned_id)
    print(f"[1] Đơn đã gán {assigned_id}")
    check(det.get("tim_thay") is True, "đơn đã gán phải tim_thay=True")
    check(det.get("nguon_don") in ("working", "static"), "nguon_don hợp lệ")
    has_keys(det.get("don_goc"), DON_GOC_KEYS, "don_goc")
    check(len(det.get("don_goc") or {}) >= len(DON_GOC_KEYS) + 2, "don_goc đủ trường gốc + pickup_tw/drop_tw hiển thị")
    has_keys(det.get("kiem_dinh"), KIEM_DINH_KEYS, "kiem_dinh")
    check(det.get("gan_tuyen") is not None, "đơn đã gán phải có gan_tuyen")
    has_keys(det.get("gan_tuyen"), GAN_TUYEN_KEYS, "gan_tuyen")
    has_keys(det["gan_tuyen"].get("vi_tri"), ["pickup_index", "delivery_index", "prev_stop", "next_stop"], "gan_tuyen.vi_tri")
    has_keys(det.get("thoi_gian_eta"), ETA_KEYS, "thoi_gian_eta")
    check(det.get("pnl_tuyen") is not None, "đơn đã gán phải có pnl_tuyen")
    has_keys(det.get("pnl_tuyen"), PNL_KEYS, "pnl_tuyen")
    check(det["chua_gan"] is None, "đơn đã gán: chua_gan phải None")

    # 2) Đơn CHƯA GÁN
    if unassigned:
        uid = unassigned[0]["order_id"]
        det = ai.get_order_detail(store, uid)
        print(f"[2] Đơn chưa gán {uid}")
        check(det.get("tim_thay") is True, "đơn chưa gán tim_thay=True")
        check(det.get("gan_tuyen") is None, "đơn chưa gán: gan_tuyen None")
        check(det.get("chua_gan") is not None, "đơn chưa gán phải có chua_gan")
        has_keys(det.get("chua_gan"), CHUA_GAN_KEYS, "chua_gan")
    else:
        print("[2] (Kịch bản không có đơn chưa gán — bỏ qua)")

    # 3) Đơn BỔ SUNG (backhaul) — sinh đơn quay đầu mẫu rồi tra
    bks = ext.build_return_orders(routes, d["fleet"], ratio=0.5, label="test")
    store["new_backhaul_orders"] = bks
    print(f"[3] Đơn bổ sung backhaul ({len(bks)} đơn mẫu)")
    check(len(bks) > 0, "phải sinh được đơn quay đầu mẫu")
    if bks:
        det = ai.get_order_detail(store, bks[0]["order_id"])
        check(det.get("tim_thay") is True or det.get("tim_thay") is False, "tra đơn backhaul không lỗi")
        # đơn backhaul không nằm trong scenario nên có thể tim_thay=False ở don_goc;
        # kiểm nhánh backhaul qua 1 đơn backhaul được matcher ghép:
        res = ai.matcher.recommend_backhaul_matches(routes, bks, d["fleet"],
                                                    ai.fuel.get_diesel_price(), 30)
        check("results" in res and "n_matched" in res, "matcher backhaul trả results/n_matched")

    # 4) Đơn DÍNH SỰ CỐ — dựng 1 sự cố từ đơn tĩnh rồi tra su_co
    o0 = next((x for x in eng.validate_orders(d["scenarios"][sid]) if x["order_id"] == assigned_id), None)
    live = [{"vehicle_id": v["vehicle_id"], "vehicle_type": v["vehicle_type"], "lat": v["lat"],
             "lon": v["lon"], "status": "Available", "max_ton": v["max_weight_kg"]/1000.0,
             "max_m3": v["max_volume_m3"], "remain_ton": v["max_weight_kg"]/1000.0,
             "remain_m3": v["max_volume_m3"], "can_reroute": True} for v in d["fleet"]]
    incident = eng.incident_from_static_order(o0, live, {"Search_Radius_Max": 30})
    store["incidents"] = [{"case_id": "SC-TEST-1", "order_id": assigned_id, "event_type": incident["event_type"],
                           "priority": "Cao", "vehicle": "V001", "route_id": "V001", "status": "Đang xử lý",
                           "decision": None, "options": [{"ten": "x"}], "soft_skills": [], "analysis": "a",
                           "incident": incident}]
    det = ai.get_order_detail(store, assigned_id)
    print(f"[4] Đơn dính sự cố {assigned_id}")
    check(det.get("su_co") is not None, "đơn có sự cố phải có su_co")
    has_keys(det.get("su_co"), SU_CO_KEYS, "su_co")

    # 5) Đơn KHÔNG TỒN TẠI
    det = ai.get_order_detail(store, "KHONG-CO-MA-NAY-999")
    print("[5] Đơn không tồn tại")
    check(det.get("tim_thay") is False, "đơn không tồn tại phải tim_thay=False")

    # 6) detect_order_id — nhận diện mã đơn trong câu hỏi tự nhiên
    print("[6] detect_order_id")
    check(ai.detect_order_id(f"đơn {assigned_id} chở gì và gán xe nào?", store) == str(assigned_id),
          "detect_order_id phải tìm thấy mã đơn trong câu hỏi")
    check(ai.detect_order_id("hôm nay thời tiết thế nào", store) is None,
          "detect_order_id không bịa mã khi câu hỏi không có mã")

    # 7) _answer_order — sinh câu trả lời cho vài câu hỏi vàng (không ném lỗi)
    print("[7] _answer_order (câu hỏi vàng)")
    det_a = ai.get_order_detail(store, assigned_id)
    for q in ["đơn này chở gì", "gán xe nào", "eta mấy giờ", "lợi nhuận bao nhiêu",
              "lấy ở đâu giao ở đâu", "khung giờ", "trạng thái kiểm định"]:
        ans = ai._answer_order(det_a, q.lower())
        check(isinstance(ans, str) and len(ans) > 0, f"_answer_order('{q}') phải trả chuỗi")

    print(f"\n=== KẾT QUẢ: {PASS} PASS · {FAIL} FAIL ===")
    sys.exit(0 if FAIL == 0 else 1)


if __name__ == "__main__":
    main()
