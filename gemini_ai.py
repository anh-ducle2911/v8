# -*- coding: utf-8 -*-
"""
TRỢ LÝ AI TẠO SINH — GEMINI (gemini_ai.py) — LỚP DIỄN GIẢI / HỘI THOẠI
======================================================================
ĐÂY LÀ LỚP AI TẠO SINH, KHÔNG phải lớp thuật toán. Trách nhiệm:
  1) Đọc NGỮ CẢNH TRỰC TUYẾN của website (kế hoạch tuyến, tài chính, sự cố,
     đơn chưa gán, đơn backhaul, giá nhiên liệu, ràng buộc cấm tải...).
  2) Khi câu hỏi cần TÍNH TOÁN (ghép backhaul, điều phối lại, đơn chưa gán,
     standby, sự cố...) -> GỌI SANG `ai_matcher.py` để lấy kết quả CÓ CẤU TRÚC.
  3) Gửi prompt có cấu trúc sang Gemini (trực tuyến) và DIỄN GIẢI kết quả thành
     câu trả lời tiếng Việt, rõ ràng, có hướng xử lý cho điều phối viên.
  4) Ánh xạ cột Excel, tóm tắt dữ liệu, phân tích sự cố (giữ tương thích app cũ).

NGUYÊN TẮC:
  • Chỉ trả lời dựa trên DỮ LIỆU THẬT trong phiên + kết quả matcher. Không bịa số.
  • Nếu thiếu dữ liệu, nói rõ thiếu gì và bước cần làm.
  • Có GEMINI_API_KEY (hoặc ANTHROPIC_API_KEY) -> TRỰC TUYẾN. Không có -> chế độ
    ngoại tuyến bám dữ liệu thật (vẫn gọi matcher), KHÔNG bao giờ vỡ demo.

Gọi mạng bằng requests nếu có, ngược lại dùng urllib (stdlib) — không bắt buộc cài thêm.
"""

import os
import re
import json
import difflib
from datetime import datetime

import hpl_engine as eng
import engine_ext as ext
import ai_matcher as matcher
import fuel_price as fuel

GEMINI_MODEL = "gemini-3.1-flash-lite"
ANTHROPIC_MODEL = "claude-sonnet-4-6"

CANONICAL_FIELDS = {
    "Order_ID": ["order id", "ma don", "mã đơn", "order", "don hang", "id don", "mã vận đơn"],
    "Customer_Name": ["customer", "khach hang", "khách hàng", "ten khach", "đại lý", "dai ly"],
    "Pickup_Name": ["pickup", "diem lay", "điểm lấy", "kho lay", "noi lay"],
    "Pickup_Lat": ["pickup lat", "lat lay", "vĩ độ lấy", "pickup latitude"],
    "Pickup_Lon": ["pickup lon", "lon lay", "kinh độ lấy", "pickup longitude"],
    "Delivery_Name": ["delivery", "diem giao", "điểm giao", "điểm trả", "noi giao"],
    "Delivery_Lat": ["delivery lat", "lat giao", "vĩ độ giao", "drop lat"],
    "Delivery_Lon": ["delivery lon", "lon giao", "kinh độ giao", "drop lon"],
    "Weight_kg": ["weight", "trong luong", "khối lượng", "khoi luong", "kg", "tải trọng"],
    "Volume_m3": ["volume", "the tich", "thể tích", "m3", "so khoi", "số khối"],
    "Min_Vehicle_Type": ["min vehicle", "loai xe", "loại xe", "vehicle type", "xe toi thieu"],
    "Max_Vehicle_Type_Allowed": ["max vehicle", "xe toi da", "loại xe tối đa"],
    "Pickup_TW_Start": ["pickup tw start", "gio lay bat dau", "giờ lấy", "pickup start"],
    "Pickup_TW_End": ["pickup tw end", "gio lay ket thuc", "pickup end"],
    "Drop_TW_Start": ["drop tw start", "gio giao bat dau", "giờ giao", "delivery start"],
    "Drop_TW_End": ["drop tw end", "gio giao ket thuc", "delivery end"],
    "Freight_Revenue_VND": ["revenue", "doanh thu", "cuoc", "cước", "tien cuoc", "freight"],
    "Customer_Priority": ["priority", "uu tien", "ưu tiên", "sla"],
    "Inner_City_Restriction": ["inner city", "cam tai", "cấm tải", "noi do", "nội đô"],
    "Corridor": ["corridor", "hanh lang", "hành lang", "tuyen", "tuyến"],
    "Direct_Distance_km": ["distance", "khoang cach", "khoảng cách", "km"],
    "Product_Group": ["product", "loai hang", "loại hàng", "nhom hang", "nhóm hàng"],
}


# ============================================================
# TRẠNG THÁI & GỌI MẠNG
# ============================================================
def gemini_key():
    return os.environ.get("GEMINI_API_KEY")


def anthropic_key():
    return os.environ.get("ANTHROPIC_API_KEY")


def ai_online():
    return bool(gemini_key() or anthropic_key())


def ai_status():
    if gemini_key():
        return {"provider": "Trực tuyến · Gemini (Internet)", "online": True}
    if anthropic_key():
        return {"provider": "Trực tuyến · Claude", "online": True}
    # Chưa cấu hình key: vẫn trả lời bám dữ liệu phiên, KHÔNG dùng nhãn "Ngoại tuyến".
    return {"provider": "Trực tuyến", "online": False}


def _http_post_json(url, payload, headers=None, timeout=30):
    headers = headers or {"Content-Type": "application/json"}
    body = json.dumps(payload).encode("utf-8")
    try:
        import requests  # type: ignore
        r = requests.post(url, data=body, headers=headers, timeout=timeout)
        return r.json()
    except Exception:
        pass
    try:
        import urllib.request
        req = urllib.request.Request(url, data=body, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8", errors="ignore"))
    except Exception:
        return None


def _call_gemini(prompt, temperature=0.3, max_tokens=1024, web=False):
    """Gọi Gemini. web=True -> bật công cụ google_search để TRA CỨU INTERNET
    (grounding). Nếu API từ chối công cụ, tự thử lại không grounding (không vỡ)."""
    key = gemini_key()
    if not key:
        return None
    url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
           f"{GEMINI_MODEL}:generateContent?key={key}")
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": temperature, "maxOutputTokens": max_tokens},
    }
    if web:
        payload["tools"] = [{"google_search": {}}]   # cho phép tra cứu Internet

    def _extract(data):
        try:
            parts = data["candidates"][0]["content"]["parts"]
            return "".join(p.get("text", "") for p in parts).strip() or None
        except Exception:
            return None

    txt = _extract(_http_post_json(url, payload))
    if txt is None and web:
        # API có thể không hỗ trợ google_search trên cấu hình hiện tại -> thử lại không grounding
        payload.pop("tools", None)
        txt = _extract(_http_post_json(url, payload))
    return txt


def _call_claude(prompt, max_tokens=1024):
    key = anthropic_key()
    if not key:
        return None
    data = _http_post_json(
        "https://api.anthropic.com/v1/messages",
        {"model": ANTHROPIC_MODEL, "max_tokens": max_tokens,
         "messages": [{"role": "user", "content": prompt}]},
        headers={"x-api-key": key, "anthropic-version": "2023-06-01",
                 "content-type": "application/json"})
    try:
        return "".join(b.get("text", "") for b in data.get("content", []))
    except Exception:
        return None


def _generate(prompt, temperature=0.3, max_tokens=1024, web=False):
    """Gọi mô hình trực tuyến đang cấu hình. Trả về (text, source) hoặc (None, None).
    web=True -> ưu tiên Gemini có tra cứu Internet (grounding)."""
    if gemini_key():
        txt = _call_gemini(prompt, temperature, max_tokens, web=web)
        if txt:
            return txt.strip(), ("Trực tuyến · Gemini (Internet)" if web else "Trực tuyến · Gemini")
    if anthropic_key():
        txt = _call_claude(prompt, max_tokens)
        if txt:
            return txt.strip(), "Trực tuyến · Claude"
    return None, None


def _extract_json(text):
    if not text:
        return None
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except Exception:
        return None


# ============================================================
# 1. ÁNH XẠ CỘT (giữ tương thích app cũ)
# ============================================================
def _fuzzy_map(headers):
    mapping, used = {}, set()
    norm = {h: re.sub(r"[^a-z0-9 ]", " ", str(h).lower()).strip() for h in headers}
    for field, aliases in CANONICAL_FIELDS.items():
        best, best_score = None, 0.0
        targets = [field.lower().replace("_", " ")] + aliases
        for h in headers:
            if h in used:
                continue
            hn = norm[h]
            for t in targets:
                score = difflib.SequenceMatcher(None, hn, t).ratio()
                if t in hn or hn in t:
                    score = max(score, 0.92)
                if score > best_score:
                    best, best_score = h, score
        if best and best_score >= 0.6:
            mapping[field] = best
            used.add(best)
    return mapping


def map_columns(headers):
    headers = [str(h) for h in headers if h]
    if ai_online():
        prompt = (
            "Bạn là trợ lý dữ liệu logistics. Ánh xạ các cột tiêu đề Excel sau sang "
            "trường chuẩn của hệ thống điều phối. Chỉ trả về JSON dạng "
            '{"trường_chuẩn":"tên_cột_gốc"}, bỏ qua trường không khớp.\n'
            f"Trường chuẩn: {list(CANONICAL_FIELDS.keys())}\n"
            f"Cột của file: {headers}\n"
        )
        txt, src = _generate(prompt, temperature=0.0)
        data = _extract_json(txt)
        if data:
            return {"mapping": data, "source": src, "matched": len(data), "total": len(headers)}
    m = _fuzzy_map(headers)
    src = "Khớp cột tự động (chưa cấu hình API key)" if not ai_online() else "Khớp cột tự động"
    return {"mapping": m, "source": src, "matched": len(m), "total": len(headers)}


# ============================================================
# 2. TÓM TẮT DỮ LIỆU (giữ tương thích app cũ)
# ============================================================
def summarize_data(summary):
    if ai_online():
        prompt = (
            "Bạn là chuyên gia điều phối vận tải Hòa Phát Logistics. Dựa trên số liệu "
            "tóm tắt kế hoạch điều phối, viết 3–4 câu nhận định ngắn gọn, chuyên nghiệp "
            "bằng tiếng Việt: nêu rủi ro chính (cấm tải theo khung giờ, vượt tải, "
            "lead-time hẹp, chạy rỗng), đánh giá năng lực và đề xuất hành động. "
            "Không dùng markdown, không dùng emoji.\n"
            f"Số liệu: {json.dumps(summary, ensure_ascii=False)}"
        )
        txt, src = _generate(prompt)
        if txt:
            return {"text": txt, "source": src}
    return {"text": _offline_summary(summary), "source": "Trợ lý AI · dữ liệu phiên"}


def _offline_summary(s):
    parts = []
    if s.get("error_orders"):
        parts.append(f"Có {s['error_orders']} đơn không thể xử lý do thiếu dữ liệu cứng "
                     f"(tọa độ, loại xe, doanh thu hoặc khối lượng) — cần bổ sung trước khi lập tuyến.")
    if s.get("review_orders"):
        parts.append(f"{s['review_orders']} đơn cần xem xét (cấm tải theo khung giờ, tách đơn, "
                     f"kiểm tra chuyến quay đầu).")
    if s.get("scenario"):
        parts.append(f"Tình huống năng lực: {s['scenario']}.")
    parts.append("Khuyến nghị: ưu tiên xe phù hợp cho đơn nội đô trong khung giờ cấm tải, "
                 "gom các đơn cùng hành lang để giảm số xe và tăng tỷ lệ sử dụng tải trọng.")
    return " ".join(parts)


# ============================================================
# 3. PHÂN TÍCH SỰ CỐ (giữ tương thích app cũ)
# ============================================================
def incident_analysis(incident_ctx, options):
    if ai_online():
        prompt = (
            "Bạn là điều phối viên cấp cao Hòa Phát Logistics. Dựa trên thông tin sự cố "
            "và các phương án xử lý engine đã tính, viết 2–3 câu phân tích tình huống và "
            "nêu phương án nên ưu tiên kèm lý do, bằng tiếng Việt, không markdown, không emoji.\n"
            f"Sự cố: {json.dumps(incident_ctx, ensure_ascii=False)}\n"
            f"Phương án: {json.dumps(options, ensure_ascii=False)}\n"
        )
        txt, src = _generate(prompt)
        if txt:
            return {"text": txt, "source": src}
    return {"text": _offline_incident(incident_ctx, options), "source": "Trợ lý AI · dữ liệu phiên"}


def _offline_incident(ctx, options):
    et = ctx.get("event_type", "sự cố")
    best = None
    if options:
        best = sorted(options, key=lambda o: ({"Cao": 0, "Trung bình": 1, "Thấp": 2}.get(o.get("khuyen_nghi"), 3),
                                              o.get("tac_dong_chi_phi", 0)))[0]
    s = (f"Sự cố \"{et}\" cho đơn {ctx.get('order_id','—')} tại {ctx.get('delivery_name','điểm giao')} "
         f"có thể ảnh hưởng SLA và phát sinh chi phí xử lý. ")
    if best:
        s += (f"Engine khuyến nghị ưu tiên phương án \"{best['ten']}\" "
              f"(mức khuyến nghị {best['khuyen_nghi']}, chi phí phát sinh ~{best['tac_dong_chi_phi']:,}đ). "
              .replace(",", "."))
    s += "Điều phối viên là người ra quyết định cuối cùng; mọi thao tác sẽ được lưu vết."
    return s


# ============================================================
# 4. NGỮ CẢNH TRỰC TUYẾN CỦA WEBSITE
# ============================================================
def get_latest_fuel_price_context():
    """Giá nhiên liệu mới nhất + thời điểm + nguồn + trạng thái (cho AI)."""
    return fuel.get_fuel_price_for_ai()


def get_route_context(store):
    """Dữ liệu tuyến/xe/đơn/depot + trạng thái điều phối (đầy đủ km rỗng, fill, P&L)."""
    routes = store.get("_routes") or []
    d = store.get("static") or {}
    fleet = d.get("fleet") or []
    used = {r.get("vehicle_id") for r in routes}
    standby = matcher.select_standby_fleet(
        [{"vehicle_id": v["vehicle_id"], "status": v.get("status", "Available")} for v in fleet],
        used, reserve=5)
    tuyen = []
    for r in routes:
        pnl = r.get("pnl") or {}
        tuyen.append({
            "xe": r.get("vehicle_id"), "loai_xe": r.get("vehicle_type"),
            "tai_xe": r.get("driver"), "hanh_lang": r.get("corridor"),
            "so_don": r.get("n_orders"), "don": r.get("orders"),
            "km": r.get("distance_km"), "km_rong": r.get("empty_km"),
            "fill_tai_pct": r.get("fill_weight_pct"),
            "loi_nhuan": pnl.get("profit"), "bien_pct": pnl.get("margin"),
            "co_backhaul": bool(r.get("has_backhaul")),
            "nguy_co_tre": pnl.get("risk_late"),
        })
    return {
        "kich_ban": store.get("_scenario"),
        "so_tuyen": len(routes), "tuyen": tuyen,
        "tong_xe_doi": len(fleet), "xe_dung": len(used),
        "xe_standby_kha_dung": len(standby),
    }


def get_backhaul_context(store):
    """Dữ liệu Module 4: đơn bổ sung + kết quả ghép chiều về (chạy matcher trực tiếp)."""
    routes = store.get("_routes") or []
    d = store.get("static") or {}
    fleet = d.get("fleet") or []
    new_bk = store.get("new_backhaul_orders") or []
    out = {"don_bo_sung": len(new_bk), "co_ket_qua": False}
    if routes and new_bk:
        price = fuel.get_diesel_price()
        res = matcher.recommend_backhaul_matches(routes, new_bk, fleet, fuel_price=price,
                                                 r_pickup=store.get("_radius") or 30)
        out.update({"co_ket_qua": True, "so_xe_ghep": res["n_matched"],
                    "loi_nhuan_bo_sung": res["total_gain"],
                    "km_rong_giam": res["empty_km_avoided"],
                    "top": [{"xe": x["vehicle_id"], "don": x["match"]["order_id"],
                             "diem": x["match"]["score"], "loi_nhuan_them": x["match"]["profit_add"],
                             "ly_do": x["match"]["reason"]} for x in res["results"][:5]]})
    return out


def get_unassigned_context(store):
    d = store.get("static") or {}
    fleet = d.get("fleet") or []
    una = store.get("_unassigned") or []
    if not una:
        return {"so_don_chua_gan": 0, "chi_tiet": []}
    ranked = matcher.rank_unassigned_orders(una, fleet, store.get("_routes"))
    return {"so_don_chua_gan": ranked["n"],
            "chi_tiet": [{"don": o["order_id"], "ly_do": o["reason"], "goi_y": o["suggestion"]}
                         for o in ranked["orders"][:8]]}


def get_constraints_context(store):
    items = store.get("constraints") or []
    return [{"khu_vuc": c.get("khu_vuc"), "loai_xe": c.get("loai_xe"), "tuyen": c.get("tuyen"),
             "khung_gio": f"{c.get('gio_bat_dau')}–{c.get('gio_ket_thuc')}",
             "hieu_luc": c.get("hieu_luc", True)} for c in items if c.get("hieu_luc", True)]


def get_current_website_state(store):
    """Trạng thái hiện tại của các module (ưu tiên dữ liệu động nếu đã nạp)."""
    return {
        "da_nap_tinh": store.get("static") is not None,
        "da_nap_dong": store.get("dynamic") is not None,
        "da_chay_ke_hoach": bool(store.get("_routes")),
        "da_tinh_tai_chinh": bool(store.get("_financial")),
        "so_su_co_dang_xu_ly": len([i for i in (store.get("incidents") or [])
                                    if i.get("status") != "Hoàn tất"]),
    }


# ============================================================
# 4b. TRA CỨU CHI TIẾT 1 ĐƠN (Q13 / Spec Phần 3) — get_order_detail
#     Gom ĐỦ trường của 1 đơn từ STORE (đã có trong phiên/RAM là đủ): đơn gốc,
#     kiểm định, gán tuyến + vị trí stop + ETA, P&L tuyến, chưa gán, backhaul, sự cố.
#     Mọi field bám đúng tên code thật (đã kiểm chứng file:line trong brief).
# ============================================================
_ORDER_BASE_KEYS = [
    "order_id", "scenario", "planning_date", "customer", "customer_group", "channel", "product",
    "pickup_id", "pickup_name", "pickup_province", "pickup_district", "pickup_lat", "pickup_lon",
    "delivery_id", "delivery_name", "delivery_province", "delivery_district", "delivery_lat", "delivery_lon",
    "corridor", "route_axis", "direct_km", "weight_kg", "volume_m3", "pallet", "min_vehicle", "max_vehicle",
    "need_refrigeration", "can_consolidate", "dedicated", "inner_city", "access_note",
    "pickup_tw_start", "pickup_tw_end", "drop_tw_start", "drop_tw_end", "tw_flex_min",
    "pickup_service", "drop_service", "lead_time", "revenue", "extra_stop_fee", "waiting_fee",
    "late_penalty_30m", "priority", "contract_route", "suggested_vehicle", "suggested_action",
    "validation_status", "risk_flag", "notes",
]


def _scenario_orders(store):
    """Đơn gốc của kịch bản đang lập (bản làm việc ưu tiên) + nhãn nguồn."""
    sid = store.get("_scenario")
    raw = (store.get("working") or {}).get(sid)
    if raw:
        return raw, "working"
    d = store.get("static") or {}
    return (d.get("scenarios") or {}).get(sid) or [], "static"


def _all_order_ids(store):
    ids = set()
    raw, _ = _scenario_orders(store)
    for o in (raw or []):
        if o.get("order_id") is not None:
            ids.add(str(o.get("order_id")))
    for key in ("new_backhaul_orders", "_unassigned"):
        for o in (store.get(key) or []):
            if o.get("order_id") is not None:
                ids.add(str(o.get("order_id")))
    for i in (store.get("incidents") or []):
        if i.get("order_id") not in (None, "—"):
            ids.add(str(i.get("order_id")))
    return ids


def detect_order_id(question, store):
    """Nhận diện mã đơn xuất hiện trong câu hỏi bằng cách so khớp với DANH SÁCH mã
    đơn THẬT trong phiên (không đoán định dạng) — khớp mã dài trước để tránh trùng."""
    ql = (question or "").lower()
    for oid in sorted(_all_order_ids(store), key=len, reverse=True):
        if oid and oid.lower() in ql:
            return oid
    return None


def get_order_detail(store, order_id):
    oid = str(order_id)
    raw, nguon = _scenario_orders(store)
    validated = eng.validate_orders(raw or [])
    o = next((x for x in validated if str(x.get("order_id")) == oid), None)
    if not o:
        # Đơn KHÔNG thuộc kịch bản (đơn bổ sung backhaul / đơn chưa gán / đơn dính sự cố):
        # vẫn dựng chi tiết tối thiểu rồi chạy tiếp các khối route/backhaul/sự cố bên dưới.
        nb = next((n for n in (store.get("new_backhaul_orders") or []) if str(n.get("order_id")) == oid), None)
        una = next((u for u in (store.get("_unassigned") or []) if str(u.get("order_id")) == oid), None)
        inc = next((i for i in (store.get("incidents") or []) if str(i.get("order_id")) == oid), None)
        if not (nb or una or inc):
            return {"order_id": order_id, "tim_thay": False}
        o = dict(nb or una or {})
        o.setdefault("order_id", oid)
        nguon = "backhaul" if nb else ("chua_gan" if una else "su_co")

    don_goc = {k: o.get(k) for k in _ORDER_BASE_KEYS}
    don_goc["pickup_tw"] = f"{eng.min_to_hhmm(o.get('pickup_tw_start'))}-{eng.min_to_hhmm(o.get('pickup_tw_end'))}"
    don_goc["drop_tw"] = f"{eng.min_to_hhmm(o.get('drop_tw_start'))}-{eng.min_to_hhmm(o.get('drop_tw_end'))}"

    kiem_dinh = {
        "computed_status": o.get("computed_status"), "issues": o.get("issues"),
        "hard_errors": o.get("hard_errors"), "soft_warnings": o.get("soft_warnings"),
        "valid": o.get("valid"), "incident_hint": o.get("incident_hint"),
        "status_lifecycle": ext.lifecycle_status(o),
    }

    out = {"order_id": order_id, "tim_thay": True, "nguon_don": nguon,
           "don_goc": don_goc, "kiem_dinh": kiem_dinh,
           "gan_tuyen": None, "thoi_gian_eta": None, "pnl_tuyen": None,
           "chua_gan": None, "backhaul": None, "su_co": None}

    routes = store.get("_routes") or []
    fleet = (store.get("static") or {}).get("fleet") or []
    route = next((r for r in routes if oid in [str(x) for x in (r.get("orders") or [])]), None)

    if route:
        st = str(route.get("status", "assigned")).strip().lower()
        locked = st in ("locked", "in_progress", "completed")
        stops = route.get("stops") or []
        pidx = didx = None
        for i, s in enumerate(stops):
            if str(s.get("order_id")) == oid and s.get("type") == "pickup" and pidx is None:
                pidx = i
            if str(s.get("order_id")) == oid and s.get("type") == "delivery":
                didx = i
        nm = lambda i: stops[i].get("name") if (i is not None and 0 <= i < len(stops)) else None
        out["gan_tuyen"] = {
            "vehicle_id": route.get("vehicle_id"), "plate": route.get("plate"),
            "vehicle_type": route.get("vehicle_type"), "driver": route.get("driver"),
            "corridor": route.get("corridor"), "n_orders": route.get("n_orders"),
            "fill_weight_pct": route.get("fill_weight_pct"), "fill_volume_pct": route.get("fill_volume_pct"),
            "empty_km": route.get("empty_km"), "productive_km": route.get("productive_km"),
            "distance_km": route.get("distance_km"), "total_weight": route.get("total_weight"),
            "total_volume": route.get("total_volume"), "has_backhaul": bool(route.get("has_backhaul")),
            "locked": locked,
            "vi_tri": {"pickup_index": pidx, "delivery_index": didx,
                       "prev_stop": nm(pidx - 1) if (pidx not in (None, 0)) else None,
                       "next_stop": nm(didx + 1) if (didx is not None and didx + 1 < len(stops)) else None},
        }
        tl = route.get("timeline") or []
        steps = [s for s in tl if str(s.get("order_id")) == oid]
        eta_p = next((s.get("time") for s in steps if s.get("type") == "pickup"), None)
        eta_d = next((s.get("time") for s in steps if s.get("type") == "delivery"), None)
        if eta_p is None and pidx is not None:
            eta_p = stops[pidx].get("eta")
        if eta_d is None and didx is not None:
            eta_d = stops[didx].get("eta")
        out["thoi_gian_eta"] = {"eta_pickup": eta_p, "eta_delivery": eta_d, "steps_cua_don": steps}
        pnl = route.get("pnl") or {}
        if pnl:
            keep = ("revenue_total", "total_cost", "profit", "margin", "fuel", "toll",
                    "driver_cost", "vehicle_cost", "empty_cost", "handling", "overhead", "overtime", "risk_late")
            out["pnl_tuyen"] = {k: pnl.get(k) for k in keep}
            out["pnl_tuyen"]["dong_gop_doanh_thu_don"] = (eng._f(o.get("revenue"))
                + eng._f(o.get("extra_stop_fee")) + eng._f(o.get("waiting_fee")))
    else:
        una = store.get("_unassigned") or []
        if any(str(u.get("order_id")) == oid for u in una):
            reason, sug = ext.unassigned_reason(o, fleet)
            ranked = matcher.rank_unassigned_orders(una, fleet, routes)
            ro = next((x for x in ranked["orders"] if str(x.get("order_id")) == oid), {})
            out["chua_gan"] = {"reason": reason, "suggestion": sug,
                               "handle_score": ro.get("handle_score"), "hard_block": ro.get("hard_block")}

    nb_ids = [str(n.get("order_id")) for n in (store.get("new_backhaul_orders") or [])]
    if oid in nb_ids and routes:
        try:
            res = matcher.recommend_backhaul_matches(routes, store.get("new_backhaul_orders"), fleet,
                                                     fuel.get_diesel_price(), store.get("_radius") or 30)
            hit = next((r for r in res["results"] if str(r["match"]["order_id"]) == oid), None)
            if hit:
                m = hit["match"]
                out["backhaul"] = {"co_the_ghep": True, "vehicle_id": hit.get("vehicle_id"),
                    "score": m.get("score"), "decision": m.get("decision"),
                    "to_pickup_km": m.get("to_pickup_km"), "profit_add": m.get("profit_add"),
                    "empty_km_reduced": m.get("empty_km_reduced"), "fill_after": m.get("fill_after"),
                    "reason": m.get("reason"), "violations": m.get("violations"),
                    "has_violation": m.get("has_violation")}
            else:
                out["backhaul"] = {"co_the_ghep": False}
        except Exception:
            pass

    inc = next((i for i in (store.get("incidents") or []) if str(i.get("order_id")) == oid), None)
    if inc:
        blob = inc.get("incident") or {}
        out["su_co"] = {
            "case_id": inc.get("case_id"), "event_type": inc.get("event_type"),
            "status": inc.get("status"), "priority": inc.get("priority"),
            "vehicle": inc.get("vehicle"), "route_id": inc.get("route_id"),
            "decision": inc.get("decision"), "options": inc.get("options"),
            "soft_skills": inc.get("soft_skills"), "analysis": inc.get("analysis"),
            "candidates": blob.get("candidates"), "recommended_vehicle": blob.get("recommended_vehicle"),
            "recommended_action": blob.get("recommended_action"), "action_desc": blob.get("action_desc"),
            "slack_min": blob.get("slack_min"),
        }
    return out


def build_ai_context(store):
    """Gom TOÀN BỘ ngữ cảnh trực tuyến cho Trợ lý AI."""
    fin = store.get("_financial") or {}
    incidents = store.get("incidents") or []
    return {
        "trang_thai": get_current_website_state(store),
        **get_route_context(store),
        "tai_chinh": (fin.get("totals") if fin else None),
        "don_chua_gan": get_unassigned_context(store),
        "backhaul": get_backhaul_context(store),
        "gia_nhien_lieu": get_latest_fuel_price_context(),
        "rang_buoc_cam_tai": get_constraints_context(store),
        "so_su_co": len([i for i in incidents if i.get("status") != "Hoàn tất"]),
        "su_co": [{"ma": i.get("case_id"), "don": i.get("order_id"), "loai": i.get("event_type"),
                   "xe": i.get("vehicle"), "trang_thai": i.get("status"),
                   "phuong_an": i.get("decision")} for i in incidents[:8]],
    }


# ============================================================
# 5. GỌI MATCHER KHI CẦN
# ============================================================
def call_matcher_if_needed(user_question, store):
    """Tự xác định và chạy thuật toán matching phù hợp với câu hỏi. Trả về dict
    kết quả CÓ CẤU TRÚC để đưa vào prompt / diễn giải, hoặc None nếu không cần."""
    if not matcher.needs_matcher(user_question):
        return None
    q = (user_question or "").lower()
    routes = store.get("_routes") or []
    d = store.get("static") or {}
    fleet = d.get("fleet") or []
    price = fuel.get_diesel_price()

    if any(k in q for k in ("ghép", "quay đầu", "chiều về", "backhaul")):
        new_bk = store.get("new_backhaul_orders") or []
        if not routes:
            return {"loai": "backhaul", "thieu": "Chưa chạy Kế hoạch tuyến (Module 3)."}
        if not new_bk:
            return {"loai": "backhaul", "thieu": "Chưa có đơn bổ sung trong Module 4."}
        return {"loai": "backhaul",
                "ket_qua": matcher.recommend_backhaul_matches(routes, new_bk, fleet, price,
                                                              store.get("_radius") or 30)}
    if "gán" in q and any(k in q for k in ("chưa", "không", "khong", "chua")):
        una = store.get("_unassigned") or []
        return {"loai": "don_chua_gan", "ket_qua": matcher.rank_unassigned_orders(una, fleet, routes)}
    if any(k in q for k in ("standby", "dự phòng")):
        used = [r.get("vehicle_id") for r in routes]
        live = [{"vehicle_id": v["vehicle_id"], "vehicle_type": v["vehicle_type"],
                 "lat": v["lat"], "lon": v["lon"], "max_ton": v["max_weight_kg"] / 1000.0,
                 "max_m3": v["max_volume_m3"], "status": "Available"} for v in fleet]
        return {"loai": "standby", "ket_qua": {"so_xe_standby": len(matcher.select_standby_fleet(live, used, 5))}}
    # các câu hỏi km rỗng / fill / tối ưu / sự cố -> dùng ngữ cảnh tuyến + tài chính sẵn có
    return None


# ============================================================
# 6. HỎI ĐÁP — HÀM CHÍNH
# ============================================================
def ask_gemini(user_question, context):
    """Gửi câu hỏi + ngữ cảnh sang mô hình TRỰC TUYẾN có tra cứu Internet.
    Trợ lý trả lời được TẤT TẦN TẬT: ưu tiên dữ liệu phiên cho câu hỏi điều phối,
    với câu hỏi ngoài phạm vi thì dùng kiến thức + Internet. Trả về (text, source)."""
    today = datetime.now().strftime("%d/%m/%Y")
    prompt = (
        "Bạn là Trợ lý AI điều phối của Hòa Phát Logistics, hoạt động TRỰC TUYẾN và có thể "
        "TRA CỨU INTERNET. Nguyên tắc trả lời:\n"
        "1) Với câu hỏi về điều phối/kế hoạch/tài chính/sự cố: BÁM SÁT dữ liệu "
        "JSON ngữ cảnh phiên dưới đây và kết quả thuật toán (matcher); không bịa số liệu phiên.\n"
        "2) Với câu hỏi ngoài phạm vi dữ liệu phiên (kiến thức chung, quy định, thời sự, "
        "logistics nói chung...): dùng kiến thức của bạn và Internet để trả lời đầy đủ.\n"
        "3) RIÊNG câu hỏi về GIÁ DẦU DO 0,05S-II / giá xăng dầu hiện hành: hãy TRA CỨU INTERNET "
        f"(google_search) giá MỚI NHẤT theo THỜI GIAN THỰC tính đến HÔM NAY ({today}) và trả lời "
        "kèm THỜI ĐIỂM tra cứu hiện tại. KHÔNG trích dẫn nguồn Petrolimex. Con số giá nhiên liệu "
        "trong ngữ cảnh phiên CHỈ là giá tham chiếu nội bộ để tính chi phí (chỉnh ở Module 5) — "
        "KHÔNG trình bày như giá thị trường, KHÔNG nói 'giá cố định cấu hình trong hệ thống'.\n"
        "Trả lời bằng tiếng Việt, ngắn gọn, đi thẳng vấn đề, có hướng xử lý cụ thể cho điều "
        "phối viên khi liên quan. Không markdown, không emoji.\n"
        f"Ngữ cảnh phiên: {json.dumps(context, ensure_ascii=False)}\n"
        f"Câu hỏi: {user_question}\n"
    )
    return _generate(prompt, temperature=0.25, max_tokens=900, web=True)


def answer_dispatch_question(user_question, store):
    """Hàm chính cho /api/assistant: lấy ngữ cảnh, gọi matcher nếu cần, gọi AI online,
    ngược lại trả lời ngoại tuyến bám dữ liệu thật. Trả về {text, source}."""
    context = build_ai_context(store)
    matcher_out = call_matcher_if_needed(user_question, store)
    if matcher_out:
        context["ket_qua_matcher"] = matcher_out
    # Q13/A5.1 — nếu câu hỏi nhắc tới 1 mã đơn cụ thể, NHÉT chi tiết đầy đủ của ĐÚNG đơn đó
    # (chỉ 1 đơn — không nhồi toàn bộ dữ liệu vào prompt).
    oid = detect_order_id(user_question, store)
    if oid:
        context["don_dang_hoi"] = get_order_detail(store, oid)
    if ai_online():
        txt, src = ask_gemini(user_question, context)
        if txt:
            return {"text": txt, "source": src}
    return {"text": _offline_assistant(user_question, context), "source": "Trợ lý AI · dữ liệu phiên"}


# Tương thích ngược: app cũ có thể gọi assistant_answer(question, context-dict)
def assistant_answer(question, context):
    if ai_online():
        txt, src = ask_gemini(question, context)
        if txt:
            return {"text": txt, "source": src}
    return {"text": _offline_assistant(question, context), "source": "Trợ lý AI · dữ liệu phiên"}


# ============================================================
# 8. GỢI Ý AI THEO TỪNG MODULE (bám nội dung module, nguồn online)
# ============================================================
MODULE_VI = {
    "import": "Nhập dữ liệu & ánh xạ", "validate": "Kiểm định dữ liệu",
    "plan": "Kế hoạch tuyến & bản đồ", "backhaul": "Ghép chuyến quay đầu",
    "finance": "Tài chính P&L", "incident": "Phát hiện & xử lý sự cố",
    "log": "Nhật ký & lưu vết", "constraints": "Ràng buộc cấm tải", "map": "Bản đồ điều phối",
}


def module_advice(module, store):
    """Sinh 2–3 gợi ý hành động bám sát module hiện tại (online + dữ liệu phiên)."""
    ctx = build_ai_context(store)
    name = MODULE_VI.get(module, module)
    if ai_online():
        prompt = (
            f"Bạn là Trợ lý AI điều phối Hòa Phát Logistics. Điều phối viên đang ở module "
            f"'{name}'. Dựa trên ngữ cảnh phiên, đưa 2–3 GỢI Ý hành động NGẮN GỌN, CỤ THỂ, "
            f"bám sát đúng module này (mỗi gợi ý một dòng bắt đầu bằng '- '). Tiếng Việt, "
            f"không emoji, không markdown ngoài gạch đầu dòng.\n"
            f"Ngữ cảnh: {json.dumps(ctx, ensure_ascii=False)}")
        txt, src = _generate(prompt, temperature=0.3, max_tokens=400, web=True)
        if txt:
            return {"text": txt, "source": src, "module": module}
    return {"text": _offline_module_advice(module, ctx), "source": "Trợ lý AI · dữ liệu phiên",
            "module": module}


def _offline_module_advice(module, ctx):
    routes = ctx.get("tuyen") or []
    fin = ctx.get("tai_chinh") or {}
    bk = ctx.get("backhaul") or {}
    una = ctx.get("don_chua_gan") or {}
    if module == "plan":
        if not routes:
            return "- Bấm 'Chạy kế hoạch tuyến' để engine Hybrid (Greedy → OR-Tools) lập tuyến.\n- Sau đó xem KPI: xe dùng, đơn gán, km rỗng, lợi nhuận."
        worst = max(routes, key=lambda r: eng._f(r.get("km_rong")), default=None)
        s = f"- Đã có {len(routes)} tuyến. Khóa các tuyến đã chốt để auto-optimize không đổi khi thêm đơn.\n"
        if worst:
            s += f"- Xe {worst.get('xe')} chạy rỗng ~{worst.get('km_rong')}km — ưu tiên ghép chiều về (Module 4)."
        return s
    if module == "backhaul":
        if bk.get("co_ket_qua"):
            return f"- Đã ghép {bk.get('so_xe_ghep')} tuyến, lợi nhuận thêm ~{int(bk.get('loi_nhuan_bo_sung',0)):,}đ.\n- Chấp nhận cặp ghép tốt rồi tính lại Tài chính (Module 5).".replace(",", ".")
        return "- Bấm 'Nạp đơn quay đầu mẫu' hoặc 'Nhập file 3PL' rồi 'Tối ưu ghép chuyến'.\n- Mục tiêu giảm km chạy rỗng chiều về."
    if module == "finance":
        if fin:
            return f"- Biên hiện tại ~{fin.get('margin')}% (mục tiêu 17–22%).\n- Giá nhiên liệu áp dụng đã tính vào chi phí vận hành; chỉnh tay nếu cần — P&L tự tính lại ngay.".replace(",", ".")
        return "- Bấm 'Tính tài chính' để xem cơ cấu chi phí và biên lợi nhuận."
    if module == "incident":
        return f"- Đang có {ctx.get('so_su_co',0)} sự cố. Chọn 'Tất cả' để xem mọi loại, hoặc xử lý từng case.\n- Có thể chọn 'Dispatcher tự điền' nếu muốn ghi phương án riêng."
    if module == "validate":
        return "- Soát các đơn 'Cần rà soát' (cấm tải/tách đơn/chiều về) trước khi lập tuyến.\n- Đơn 'Không thể xử lý' cần bổ sung dữ liệu cứng."
    if una.get("so_don_chua_gan"):
        return f"- Còn {una['so_don_chua_gan']} đơn chưa gán — xem lý do & gợi ý ở Module 3."
    return "- Hãy nạp dữ liệu (Module 1), kiểm định (Module 2) và chạy Kế hoạch tuyến (Module 3)."


# ============================================================
# 7. TRẢ LỜI NGOẠI TUYẾN (bám dữ liệu thật + kết quả matcher)
# ============================================================
def _vnd(x):
    try:
        return f"{int(round(float(x))):,}đ".replace(",", ".")
    except Exception:
        return "—"


def _answer_order(d, ql):
    """Trả lời ngoại tuyến cho câu hỏi về 1 đơn — bám 24 câu hỏi vàng (Spec 3.2/3.3)."""
    g = d.get("don_goc") or {}
    kd = d.get("kiem_dinh") or {}
    gt = d.get("gan_tuyen")
    eta = d.get("thoi_gian_eta")
    pn = d.get("pnl_tuyen")
    cg = d.get("chua_gan")
    bk = d.get("backhaul")
    sc = d.get("su_co")
    oid = g.get("order_id")
    has = lambda *ks: any(k in ql for k in ks)

    if has("chở gì", "cho gi", "sản phẩm", "san pham", "khối lượng", "khoi luong", "thể tích", "the tich", "pallet", "hàng gì", "xe lạnh", "xe lanh"):
        return (f"Đơn {oid} ({g.get('customer') or '—'}): {g.get('product') or '—'}, "
                f"{eng._f(g.get('weight_kg')):.0f}kg · {eng._f(g.get('volume_m3')):.1f}m³ · {eng._f(g.get('pallet')):.0f} pallet"
                + ("; CẦN xe lạnh." if g.get("need_refrigeration") else "."))
    if has("lấy ở đâu", "giao ở đâu", "điểm lấy", "điểm trả", "địa chỉ", "tọa độ", "toa do"):
        return (f"Đơn {oid}: lấy tại {g.get('pickup_name')} ({g.get('pickup_district')}, {g.get('pickup_province')}) "
                f"[{g.get('pickup_lat')},{g.get('pickup_lon')}] → giao {g.get('delivery_name')} "
                f"({g.get('delivery_district')}, {g.get('delivery_province')}) [{g.get('delivery_lat')},{g.get('delivery_lon')}].")
    if has("khung giờ", "giờ lấy", "giờ giao", "mấy giờ", "lead time", "time window"):
        return (f"Đơn {oid}: khung giờ lấy {g.get('pickup_tw')}, giao {g.get('drop_tw')}, "
                f"linh hoạt ±{eng._f(g.get('tw_flex_min')):.0f}', lead time {eng._f(g.get('lead_time')):.0f}'.")
    if has("doanh thu", "cước", "cuoc", "phụ phí", "phí chờ", "phạt trễ", "giá "):
        return (f"Đơn {oid}: cước {_vnd(g.get('revenue'))}, phụ phí điểm dừng {_vnd(g.get('extra_stop_fee'))}, "
                f"phí chờ {_vnd(g.get('waiting_fee'))}, phạt trễ {_vnd(g.get('late_penalty_30m'))}/30'.")
    if has("loại xe", "loai xe", "xe tối thiểu", "xe tối đa", "gom đơn", "min vehicle"):
        return (f"Đơn {oid}: xe tối thiểu {g.get('min_vehicle')}, tối đa {g.get('max_vehicle') or '—'}, "
                f"đề xuất {g.get('suggested_vehicle') or '—'}; {'cho' if g.get('can_consolidate') else 'không cho'} gom đơn"
                + ("; cần xe lạnh." if g.get("need_refrigeration") else "."))
    if has("cấm tải", "cam tai", "nội đô", "noi do", "giờ cấm", "tiếp cận"):
        warn = [i for i in (kd.get("soft_warnings") or []) if "cấm tải" in i]
        return (f"Đơn {oid}: {'thuộc nội đô' if g.get('inner_city') else 'không thuộc nội đô'}. "
                + (("Cảnh báo: " + warn[0] + ". ") if warn else "Không vướng khung giờ cấm tải hiện hành. ")
                + f"Ghi chú tiếp cận: {g.get('access_note') or '—'}.")
    if cg and has("chưa gán", "khong gan", "không gán", "vì sao", "tại sao", "sao bị", "chua gan"):
        return (f"Đơn {oid} CHƯA gán xe vì {cg.get('reason')} "
                f"(độ dễ xử lý {cg.get('handle_score')}/70{', vi phạm cứng' if cg.get('hard_block') else ''}). "
                f"Gợi ý: {cg.get('suggestion')}.")
    if bk and has("ghép", "chiều về", "backhaul", "quay đầu"):
        if bk.get("co_the_ghep"):
            return (f"Đơn {oid} CÓ thể ghép chiều về xe {bk.get('vehicle_id')} (điểm {bk.get('score')}, {bk.get('decision')}): "
                    f"cách {bk.get('to_pickup_km')}km, lợi nhuận thêm ~{_vnd(bk.get('profit_add'))}, "
                    f"giảm {bk.get('empty_km_reduced')}km rỗng, fill {bk.get('fill_after')}%. {bk.get('reason')}")
        return f"Đơn {oid} hiện chưa tìm được tuyến ghép chiều về phù hợp."
    if sc and has("sự cố", "su co", "incident", "thay thế", "phương án"):
        rv = sc.get("recommended_vehicle")
        rv = rv.get("vehicle") if isinstance(rv, dict) else "—"
        return (f"Đơn {oid}: sự cố {sc.get('case_id')} loại {sc.get('event_type')}, trạng thái {sc.get('status')}, "
                f"xe {sc.get('vehicle')}; đề xuất xe thay thế {rv}, hành động {sc.get('recommended_action') or '—'}.")
    if gt and has("xe nào", "gán xe", "gan xe", "tài xế", "tai xe", "ai chở", "biển số", "tuyến nào"):
        return (f"Đơn {oid} thuộc tuyến xe {gt.get('vehicle_id')} ({gt.get('vehicle_type')}, biển {gt.get('plate')}), "
                f"tài xế {gt.get('driver')}, hành lang {gt.get('corridor')}.")
    if eta and has("eta", "mấy giờ tới", "dự kiến đến", "timeline"):
        return f"Đơn {oid}: ETA điểm lấy ~{eta.get('eta_pickup') or '—'}, ETA điểm trả ~{eta.get('eta_delivery') or '—'}."
    if gt and has("fill", "đầy tải", "tải trọng", "tận dụng"):
        return (f"Tuyến chở đơn {oid} (xe {gt.get('vehicle_id')}): fill theo tải {gt.get('fill_weight_pct')}%, "
                f"theo thể tích {gt.get('fill_volume_pct')}% ({gt.get('total_weight')}kg / {gt.get('total_volume')}m³).")
    if pn and has("lợi nhuận", "loi nhuan", "biên", "p&l", "lãi", "lỗ", "đóng góp"):
        return (f"Đơn {oid} góp doanh thu ~{_vnd(pn.get('dong_gop_doanh_thu_don'))} vào tuyến xe {(gt or {}).get('vehicle_id')}; "
                f"tuyến lãi {_vnd(pn.get('profit'))}, biên {pn.get('margin')}%.")
    if has("kiểm định", "trạng thái", "hợp lệ", "rà soát", "lỗi", "vì sao đỏ"):
        return (f"Đơn {oid}: {kd.get('status_lifecycle')} (computed_status={kd.get('computed_status')}). "
                f"Lỗi cứng: {', '.join(kd.get('hard_errors') or []) or 'không'}. "
                f"Cảnh báo: {', '.join(kd.get('soft_warnings') or []) or 'không'}.")
    return _order_summary(d)


def _order_summary(d):
    g = d.get("don_goc") or {}; kd = d.get("kiem_dinh") or {}; gt = d.get("gan_tuyen")
    pn = d.get("pnl_tuyen"); cg = d.get("chua_gan"); bk = d.get("backhaul"); sc = d.get("su_co")
    oid = g.get("order_id")
    parts = [f"Đơn {oid} — {g.get('customer') or '—'} · {g.get('product') or '—'} · "
             f"{eng._f(g.get('weight_kg')):.0f}kg/{eng._f(g.get('volume_m3')):.1f}m³.",
             f"Lấy {g.get('pickup_name')} → giao {g.get('delivery_name')} ({g.get('corridor') or '—'}, {eng._f(g.get('direct_km')):.0f}km).",
             f"Khung giao {g.get('drop_tw')}, cước {_vnd(g.get('revenue'))}, ưu tiên {g.get('priority') or '—'}.",
             f"Kiểm định: {kd.get('status_lifecycle')}."]
    if gt:
        parts.append(f"Đã gán xe {gt.get('vehicle_id')} ({gt.get('vehicle_type')}), tài xế {gt.get('driver')}, fill {gt.get('fill_weight_pct')}%.")
    elif cg:
        parts.append(f"CHƯA gán: {cg.get('reason')} — {cg.get('suggestion')}.")
    if pn:
        parts.append(f"Tuyến lãi {_vnd(pn.get('profit'))} (biên {pn.get('margin')}%).")
    if bk and bk.get("co_the_ghep"):
        parts.append(f"Có thể ghép chiều về xe {bk.get('vehicle_id')} (+{_vnd(bk.get('profit_add'))}).")
    if sc:
        parts.append(f"Đang có sự cố {sc.get('case_id')} ({sc.get('event_type')}, {sc.get('status')}).")
    return " ".join(parts)


def _offline_assistant(q, ctx):
    ql = (q or "").lower()
    routes = ctx.get("tuyen") or []
    fin = ctx.get("tai_chinh") or {}
    incidents = ctx.get("su_co") or []
    mres = ctx.get("ket_qua_matcher") or {}
    fuel_ctx = ctx.get("gia_nhien_lieu") or {}

    # Q13 — Hỏi về 1 đơn cụ thể: trả lời bám chi tiết đơn (đã nhét don_dang_hoi)
    don = ctx.get("don_dang_hoi")
    if don and don.get("tim_thay"):
        return _answer_order(don, ql)

    # Giá nhiên liệu -> chế độ trực tuyến sẽ Google giá real-time; ngoại tuyến thì hướng tra cứu nhanh
    if any(k in ql for k in ("giá dầu", "gia dau", "nhiên liệu", "nhien lieu", "xăng", "xang")):
        return ("Giá xăng dầu thay đổi theo thời gian thực — bạn tra cứu nhanh trên Google "
                "(\"giá dầu DO 0,05S-II hôm nay\") để có mức mới nhất. Hệ thống đang dùng giá tham chiếu "
                "nội bộ để tính chi phí vận hành & P&L; có thể chỉnh tay tại Module 5 (Tài chính).")

    # Ghép backhaul
    if any(k in ql for k in ("ghép", "quay đầu", "chiều về", "backhaul")):
        if mres.get("loai") == "backhaul" and mres.get("thieu"):
            return mres["thieu"]
        kq = (mres.get("ket_qua") or {}) if mres.get("loai") == "backhaul" else {}
        if kq.get("results"):
            top = kq["results"][0]["match"]
            return (f"Có {kq['n_matched']}/{kq['n_routes']} xe ghép được chiều về, "
                    f"giảm ~{kq['empty_km_avoided']}km rỗng, lợi nhuận bổ sung ~{int(kq['total_gain']):,}đ. "
                    f"Ưu tiên xe {top['vehicle_id']} ghép đơn {top['order_id']} (điểm {top['score']}): {top['reason']}"
                    ).replace(",", ".")
        return "Chưa tìm được cặp ghép chiều về phù hợp. Hãy thêm đơn bổ sung ở Module 4 và chạy Kế hoạch tuyến trước."

    # Đơn chưa gán
    if "chưa gán" in ql or ("đơn" in ql and "gán" in ql):
        kq = mres.get("ket_qua") or {}
        if kq.get("orders"):
            o = kq["orders"][0]
            return (f"Đang có {kq['n']} đơn chưa gán. Đơn dễ xử lý nhất: {o['order_id']} — "
                    f"{o['reason']}. Gợi ý: {o['suggestion']}.")
        return "Hiện không có đơn chưa gán, hoặc chưa chạy Kế hoạch tuyến (Module 3)."

    # Tuyến km rỗng cao nhất
    if "rỗng" in ql or "rong" in ql:
        if not routes:
            return "Chưa có kế hoạch tuyến. Hãy chạy Module 3 trước."
        worst = max(routes, key=lambda r: eng._f(r.get("km_rong")))
        return (f"Tuyến có km rỗng cao nhất: xe {worst['xe']} ({worst.get('hanh_lang') or '—'}) "
                f"với ~{worst.get('km_rong')}km chạy rỗng. Nên xét ghép backhaul (Module 4) cho xe này.")

    # Sự cố / thay thế / standby
    if "sự cố" in ql or "su co" in ql:
        if not incidents:
            return "Hiện chưa có sự cố nào đang xử lý trong phiên."
        ds = ", ".join(f"{i.get('don')} ({i.get('loai')}) — xe {i.get('xe')}" for i in incidents[:6])
        return f"Đang có {len(incidents)} sự cố: {ds}."
    if "standby" in ql or "dự phòng" in ql:
        n = ctx.get("xe_standby_kha_dung", 0)
        return (f"Hiện còn khoảng {n} xe có thể giữ standby (dự phòng). Nên duy trì 3–5 xe standby "
                f"để xử lý đơn phát sinh và sự cố; chỉ điều standby khi thật cần.")

    # Biên / lợi nhuận
    if "biên" in ql or "lợi nhuận" in ql or "loi nhuan" in ql:
        if not fin:
            return "Chưa có số liệu tài chính. Hãy chạy Module 5 (Tài chính P&L)."
        return (f"Biên lợi nhuận kế hoạch ~{fin.get('margin')}%, sau xử lý sự cố ~{fin.get('margin_after')}%. "
                f"Lợi nhuận ~{int(fin.get('profit',0)):,}đ. Giá nhiên liệu đang dùng "
                f"{int(fuel_ctx.get('gia_nhien_lieu',0)):,}đ/lít.").replace(",", ".")

    # Chi phí
    if "chi phí" in ql or "chi phi" in ql:
        if not fin:
            return "Chưa có số liệu tài chính. Hãy chạy Module 5 (Tài chính P&L)."
        return (f"Tổng chi phí kế hoạch ~{int(fin.get('total_cost',0)):,}đ trên {fin.get('n_routes')} tuyến, "
                f"doanh thu ~{int(fin.get('revenue_total',0)):,}đ.").replace(",", ".")

    # Mặc định
    if routes:
        return (f"Phiên có {len(routes)} tuyến đã gán. Bạn có thể hỏi: 'tuyến nào km rỗng cao nhất', "
                f"'đơn backhaul nào tăng fill-rate tốt nhất', 'giá dầu hiện tại', "
                f"'có nên dùng xe standby không', 'biên lợi nhuận bao nhiêu'.")
    return ("Tôi trả lời dựa trên dữ liệu trong phiên. Hiện chưa đủ dữ liệu — hãy nạp dữ liệu (Module 1), "
            "kiểm định (Module 2) và chạy Kế hoạch tuyến (Module 3) để tôi hỗ trợ chính xác.")
