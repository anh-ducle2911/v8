# -*- coding: utf-8 -*-
"""
TRỢ LÝ AI TẠO SINH — GEMINI (gemini_ai.py)
==========================================
AI tạo sinh (Gemini API) phục vụ 4 việc, TÁCH BIỆT rõ với routing/optimization
engine:
  1) Đọc & ánh xạ cột file Excel về trường chuẩn của hệ thống.
  2) Phát hiện dữ liệu thiếu/bất thường, giải thích lỗi dữ liệu bằng tiếng Việt.
  3) Phân tích tình huống sự cố, gợi ý diễn giải phương án (engine sinh phương án).
  4) Trợ lý hỏi đáp điều phối, trả lời BÁM dữ liệu thực trong phiên làm việc.

An toàn demo: không có GEMINI_API_KEY hoặc không có mạng -> tự rơi về chế độ
ngoại tuyến (khớp mờ + suy luận dựa trên dữ liệu thực). Không bao giờ vỡ demo.

Cấu hình: đặt biến môi trường GEMINI_API_KEY (không hard-code trong source).
"""

import os
import re
import json
import difflib

GEMINI_MODEL = "gemini-2.0-flash"

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


# ------------------------------------------------------------
# Trạng thái cấu hình
# ------------------------------------------------------------
def gemini_key():
    return os.environ.get("GEMINI_API_KEY")


def gemini_available():
    return bool(gemini_key())


def ai_status():
    return {"provider": "Gemini" if gemini_available() else "Ngoại tuyến",
            "online": gemini_available()}


# ------------------------------------------------------------
# Gọi Gemini (nếu có key + mạng), ngược lại trả None để fallback
# ------------------------------------------------------------
def _call_gemini(prompt, temperature=0.3, max_tokens=1024):
    key = gemini_key()
    if not key:
        return None
    try:
        import requests
        url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
               f"{GEMINI_MODEL}:generateContent?key={key}")
        r = requests.post(url, timeout=30, json={
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": temperature, "maxOutputTokens": max_tokens},
        })
        data = r.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception:
        return None


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
# 1. ÁNH XẠ CỘT
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
    if gemini_available():
        prompt = (
            "Bạn là trợ lý dữ liệu logistics. Ánh xạ các cột tiêu đề Excel sau sang "
            "trường chuẩn của hệ thống điều phối. Chỉ trả về JSON dạng "
            '{"trường_chuẩn":"tên_cột_gốc"}, bỏ qua trường không khớp.\n'
            f"Trường chuẩn: {list(CANONICAL_FIELDS.keys())}\n"
            f"Cột của file: {headers}\n"
        )
        data = _extract_json(_call_gemini(prompt))
        if data:
            return {"mapping": data, "source": "Gemini",
                    "matched": len(data), "total": len(headers)}
    m = _fuzzy_map(headers)
    src = "Ngoại tuyến (khớp mờ — chưa cấu hình GEMINI_API_KEY)" if not gemini_available() \
          else "Ngoại tuyến (khớp mờ)"
    return {"mapping": m, "source": src, "matched": len(m), "total": len(headers)}


# ============================================================
# 2. TÓM TẮT LỖI / TÌNH TRẠNG DỮ LIỆU
# ============================================================
def summarize_data(summary):
    if gemini_available():
        prompt = (
            "Bạn là chuyên gia điều phối vận tải Hòa Phát Logistics. Dựa trên số liệu "
            "tóm tắt kế hoạch điều phối, viết 3–4 câu nhận định ngắn gọn, chuyên nghiệp "
            "bằng tiếng Việt: nêu rủi ro chính (cấm tải theo khung giờ, vượt tải, "
            "lead-time hẹp, chạy rỗng), đánh giá năng lực và đề xuất hành động. "
            "Không dùng markdown, không dùng emoji.\n"
            f"Số liệu: {json.dumps(summary, ensure_ascii=False)}"
        )
        txt = _call_gemini(prompt)
        if txt:
            return {"text": txt.strip(), "source": "Gemini"}
    return {"text": _offline_summary(summary), "source": "Ngoại tuyến"}


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
# 3. PHÂN TÍCH TÌNH HUỐNG SỰ CỐ
# ============================================================
def incident_analysis(incident_ctx, options):
    if gemini_available():
        prompt = (
            "Bạn là điều phối viên cấp cao Hòa Phát Logistics. Dựa trên thông tin sự cố "
            "và các phương án xử lý engine đã tính, viết 2–3 câu phân tích tình huống và "
            "nêu phương án nên ưu tiên kèm lý do, bằng tiếng Việt, không markdown, không emoji.\n"
            f"Sự cố: {json.dumps(incident_ctx, ensure_ascii=False)}\n"
            f"Phương án: {json.dumps(options, ensure_ascii=False)}\n"
        )
        txt = _call_gemini(prompt)
        if txt:
            return {"text": txt.strip(), "source": "Gemini"}
    return {"text": _offline_incident(incident_ctx, options), "source": "Ngoại tuyến"}


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
# 4. TRỢ LÝ HỎI ĐÁP ĐIỀU PHỐI (bám dữ liệu phiên)
# ============================================================
def assistant_answer(question, context):
    if gemini_available():
        prompt = (
            "Bạn là Trợ lý điều phối AI của Hòa Phát Logistics. CHỈ trả lời dựa trên dữ "
            "liệu JSON ngữ cảnh dưới đây. Nếu thiếu dữ liệu để trả lời, nói rõ đang thiếu "
            "dữ liệu nào và gợi ý bước cần làm. Trả lời tiếng Việt, ngắn gọn, không markdown, "
            "không emoji.\n"
            f"Ngữ cảnh: {json.dumps(context, ensure_ascii=False)}\n"
            f"Câu hỏi: {question}\n"
        )
        txt = _call_gemini(prompt)
        if txt:
            return {"text": txt.strip(), "source": "Gemini"}
    return {"text": _offline_assistant(question, context), "source": "Ngoại tuyến"}


def _offline_assistant(q, ctx):
    ql = (q or "").lower()
    routes = ctx.get("tuyen") or []
    fin = ctx.get("tai_chinh") or {}
    incidents = ctx.get("su_co") or []

    # tìm mã đơn trong câu hỏi
    m = re.search(r"\b([a-zA-Z]{1,4}[-_ ]?\d{2,})\b", q or "")
    code = m.group(1).replace(" ", "").upper() if m else None

    if not routes and any(k in ql for k in ["tuyến", "xe", "đơn", "lợi nhuận", "biên", "chi phí"]):
        if not ctx.get("kich_ban"):
            return "Hiện chưa có dữ liệu kế hoạch tuyến trong phiên. Vui lòng nạp dữ liệu ở Module 1 và chạy Kế hoạch tuyến (Module 3) trước khi hỏi."

    if code:
        for r in routes:
            dons = [str(d).upper() for d in (r.get("don") or [])]
            if code in dons:
                return (f"Đơn {code} đang được gán cho xe {r.get('xe')} "
                        f"({r.get('loai_xe')}), tài xế {r.get('tai_xe') or '—'}, "
                        f"hành lang {r.get('hanh_lang') or '—'}. Tuyến dài "
                        f"{r.get('km')} km, biên lợi nhuận tuyến ~{r.get('bien')}%.")
        return (f"Không tìm thấy đơn {code} trong các tuyến đã gán. Có thể đơn nằm ở "
                f"danh sách Đơn chưa gán hoặc chưa chạy Kế hoạch tuyến. Vui lòng kiểm tra Module 3.")

    if "sự cố" in ql or "su co" in ql:
        if not incidents:
            return "Hiện chưa có sự cố nào đang xử lý trong phiên."
        ds = ", ".join(f"{i.get('don')} ({i.get('loai')})" for i in incidents[:6])
        return f"Đang có {len(incidents)} sự cố: {ds}."

    if "biên" in ql or "lợi nhuận" in ql or "loi nhuan" in ql:
        if not fin:
            return "Chưa có số liệu tài chính. Vui lòng chạy Module 5 (Tài chính P&L)."
        return (f"Biên lợi nhuận kế hoạch ~{fin.get('margin')}%, sau xử lý sự cố "
                f"~{fin.get('margin_after')}%. Tổng lợi nhuận ~{int(fin.get('profit',0)):,}đ."
                .replace(",", "."))

    if "chi phí" in ql or "chi phi" in ql:
        if not fin:
            return "Chưa có số liệu tài chính. Vui lòng chạy Module 5 (Tài chính P&L)."
        return (f"Tổng chi phí kế hoạch ~{int(fin.get('total_cost',0)):,}đ trên "
                f"{fin.get('n_routes')} tuyến, doanh thu ~{int(fin.get('revenue_total',0)):,}đ."
                .replace(",", "."))

    if "ghép" in ql or "quay đầu" in ql or "chiều về" in ql:
        n = ctx.get("don_bo_sung_quay_dau", 0)
        if not n:
            return "Chưa có đơn bổ sung cho chuyến quay đầu. Vui lòng thêm đơn ở Module 4."
        return f"Đang có {n} đơn bổ sung để xét ghép chuyến quay đầu. Mở Module 4 để xem gợi ý ghép theo từng xe."

    if "trống" in ql or "rảnh" in ql or "gần" in ql:
        return "Để biết xe trống gần một điểm, hãy mở một sự cố từ đơn (Module 6) — hệ thống sẽ quét xe khả dụng trong bán kính và chấm điểm phù hợp."

    # mặc định
    if routes:
        return (f"Phiên hiện có {len(routes)} tuyến đã gán. Bạn có thể hỏi: 'đơn [mã] ở đâu', "
                f"'biên lợi nhuận bao nhiêu', 'đơn nào đang có sự cố', 'tuyến nào ghép thêm chiều về'.")
    return ("Tôi trả lời dựa trên dữ liệu trong phiên. Hiện chưa đủ dữ liệu — hãy nạp dữ liệu (Module 1), "
            "kiểm định (Module 2) và chạy Kế hoạch tuyến (Module 3) để tôi hỗ trợ chính xác.")
