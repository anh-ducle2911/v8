# -*- coding: utf-8 -*-
"""
AI MATCHER (ai_matcher.py)
==========================
Dùng AI (Claude của Anthropic HOẶC Gemini của Google) cho 2 việc:

  1) ÁNH XẠ CỘT (column mapping): file Excel người dùng tải lên có tiêu đề cột
     khác chuẩn -> AI suy luận cột nào ứng với trường chuẩn của engine
     (Order_ID, Pickup_Lat, Weight_kg, ...). => "match file import với dữ liệu web".

  2) DIỄN GIẢI ĐIỀU PHỐI (risk narrative): AI đọc tóm tắt kế hoạch và sinh nhận
     định điều phối bằng tiếng Việt (cấm tải, vượt tải, lead-time hẹp, chạy rỗng,
     biên lợi nhuận...).

An toàn demo: KHÔNG có API key / KHÔNG có mạng -> tự rơi về khớp mờ (fuzzy) +
nhận định offline. Không bao giờ vỡ demo.

Cấu hình key qua biến môi trường:
  ANTHROPIC_API_KEY   (Claude)    hoặc    GEMINI_API_KEY   (Gemini)
"""

import os
import json
import re
import difflib

# Trường chuẩn của engine + bí danh (Việt/Anh) — bám đúng schema 2 file Excel
CANONICAL_FIELDS = {
    "Order_ID": ["order id", "ma don", "mã đơn", "order", "don hang", "id don"],
    "Customer_Name": ["customer", "khach hang", "khách hàng", "ten khach", "đại lý", "dai ly", "customer name"],
    "Pickup_Lat": ["pickup lat", "lat lay", "vĩ độ lấy", "pickup latitude"],
    "Pickup_Lon": ["pickup lon", "lon lay", "kinh độ lấy", "pickup longitude"],
    "Delivery_Lat": ["delivery lat", "lat giao", "vĩ độ giao", "drop lat"],
    "Delivery_Lon": ["delivery lon", "lon giao", "kinh độ giao", "drop lon"],
    "Weight_kg": ["weight", "trong luong", "khối lượng", "khoi luong", "kg", "tải trọng", "weight kg"],
    "Volume_m3": ["volume", "the tich", "thể tích", "m3", "so khoi", "số khối", "volume m3"],
    "Min_Vehicle_Type": ["min vehicle", "loai xe", "loại xe", "vehicle type", "xe toi thieu", "min vehicle type"],
    "Max_Vehicle_Type_Allowed": ["max vehicle", "xe toi da", "loại xe tối đa"],
    "Pickup_TW_Start": ["pickup tw start", "gio lay bat dau", "giờ lấy", "pickup start"],
    "Pickup_TW_End": ["pickup tw end", "gio lay ket thuc", "pickup end"],
    "Drop_TW_Start": ["drop tw start", "gio giao bat dau", "giờ giao", "delivery start"],
    "Drop_TW_End": ["drop tw end", "gio giao ket thuc", "delivery end"],
    "Freight_Revenue_VND": ["revenue", "doanh thu", "cuoc", "cước", "tien cuoc", "freight", "freight revenue"],
    "Customer_Priority": ["priority", "uu tien", "ưu tiên", "sla", "customer priority"],
    "Inner_City_Restriction": ["inner city", "cam tai", "cấm tải", "noi do", "nội đô", "inner city restriction"],
    "Corridor": ["corridor", "hanh lang", "hành lang", "tuyen", "tuyến"],
    "Direct_Distance_km": ["distance", "khoang cach", "khoảng cách", "km", "direct distance"],
}


# ------------------------------------------------------------
# A. KHỚP CỘT
# ------------------------------------------------------------
def _fuzzy_map(headers):
    """Khớp mờ offline: bí danh + difflib."""
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


def ai_map_columns(headers, provider="auto"):
    """Trả về {mapping, source, confidence}."""
    headers = [str(h) for h in headers if h]
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
    gemini_key = os.environ.get("GEMINI_API_KEY")

    prompt = (
        "Bạn là trợ lý dữ liệu logistics. Hãy ánh xạ các cột tiêu đề sau của file Excel "
        "sang trường chuẩn của hệ thống điều phối xe. Chỉ trả về JSON object dạng "
        '{"trường_chuẩn": "tên_cột_gốc"}, bỏ qua trường không khớp, không thêm chữ nào khác.\n\n'
        f"Trường chuẩn: {list(CANONICAL_FIELDS.keys())}\n"
        f"Cột tiêu đề của file: {headers}\n"
    )

    try:
        if provider in ("auto", "claude") and anthropic_key:
            txt = _call_claude(prompt, anthropic_key)
            data = _extract_json(txt)
            if data:
                return {"mapping": data, "source": "claude", "matched": len(data), "total": len(headers)}
        if provider in ("auto", "gemini") and gemini_key:
            txt = _call_gemini(prompt, gemini_key)
            data = _extract_json(txt)
            if data:
                return {"mapping": data, "source": "gemini", "matched": len(data), "total": len(headers)}
    except Exception as e:
        m = _fuzzy_map(headers)
        return {"mapping": m, "source": f"offline (AI lỗi: {e})", "matched": len(m), "total": len(headers)}

    m = _fuzzy_map(headers)
    return {"mapping": m, "source": "offline (fuzzy — chưa cấu hình API key)",
            "matched": len(m), "total": len(headers)}


# ------------------------------------------------------------
# B. DIỄN GIẢI ĐIỀU PHỐI
# ------------------------------------------------------------
def ai_risk_narrative(summary, provider="auto"):
    """summary: dict thống kê. Trả về nhận định tiếng Việt."""
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
    gemini_key = os.environ.get("GEMINI_API_KEY")
    prompt = (
        "Bạn là chuyên gia điều phối vận tải của Hòa Phát Logistics. Dựa trên số liệu tóm tắt "
        "kế hoạch điều phối dưới đây, hãy viết 3–4 câu nhận định ngắn gọn, chuyên nghiệp bằng "
        "tiếng Việt: nêu rủi ro chính (cấm tải theo khung giờ, vượt tải, lead-time hẹp, chạy rỗng), "
        "đánh giá biên lợi nhuận và đề xuất hành động. Không dùng markdown.\n\n"
        f"Số liệu: {json.dumps(summary, ensure_ascii=False)}"
    )
    try:
        if provider in ("auto", "claude") and anthropic_key:
            return {"text": _call_claude(prompt, anthropic_key).strip(), "source": "claude"}
        if provider in ("auto", "gemini") and gemini_key:
            return {"text": _call_gemini(prompt, gemini_key).strip(), "source": "gemini"}
    except Exception as e:
        return {"text": _offline_narrative(summary), "source": f"offline (AI lỗi: {e})"}
    return {"text": _offline_narrative(summary), "source": "offline"}


def _offline_narrative(s):
    parts = []
    if s.get("error_orders"):
        parts.append(f"Có {s['error_orders']} đơn cần kiểm định lại (lỗi dữ liệu cứng: tọa độ/loại xe/doanh thu).")
    if s.get("review_orders"):
        parts.append(f"{s['review_orders']} đơn cần can thiệp điều phối (cấm tải theo khung giờ, tách đơn, kiểm tra backhaul).")
    if s.get("scenario"):
        parts.append(f"Tình huống năng lực: {s['scenario']}.")
    if s.get("margin") is not None:
        parts.append(f"Biên lợi nhuận kế hoạch ước đạt {s['margin']}% — {'đạt mục tiêu 17–22%' if 17 <= s['margin'] <= 24 else 'cần tối ưu thêm gom đơn & backhaul'}.")
    if s.get("empty_warning"):
        parts.append("Một số tuyến dài có nguy cơ chạy rỗng chiều về — cần kích hoạt ghép backhaul.")
    parts.append("Khuyến nghị: ưu tiên xe ≤1.25T cho nội đô trong giờ cấm tải, gom cụm theo hành lang, khóa kế hoạch trước 19:00.")
    return " ".join(parts)


# ------------------------------------------------------------
# C. GỌI API
# ------------------------------------------------------------
def _call_claude(prompt, key, model="claude-sonnet-4-6"):
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=key)
        resp = client.messages.create(
            model=model, max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        return "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
    except ImportError:
        import requests
        r = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": key, "anthropic-version": "2023-06-01",
                     "content-type": "application/json"},
            json={"model": model, "max_tokens": 1024,
                  "messages": [{"role": "user", "content": prompt}]},
            timeout=30,
        )
        data = r.json()
        return "".join(b.get("text", "") for b in data.get("content", []))


def _call_gemini(prompt, key, model="gemini-2.0-flash"):
    import requests
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
    r = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=30)
    data = r.json()
    return data["candidates"][0]["content"]["parts"][0]["text"]


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
