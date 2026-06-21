# -*- coding: utf-8 -*-
"""
GIÁ NHIÊN LIỆU (fuel_price.py)
==============================
Giá dầu diesel dùng để TÍNH CHI PHÍ tuyến & P&L là một GIÁ CỐ ĐỊNH tham chiếu nội bộ
(mặc định 27.500 đ/lít). Điều phối viên chỉnh tay tại Module 5 (Tài chính) khi cần.

KHÔNG crawl / tự động lấy giá từ website. Giá XĂNG DẦU THỊ TRƯỜNG (thời gian thực) do
Trợ lý AI tra cứu trực tiếp qua Google ngay trên thanh hội thoại khi điều phối viên hỏi
— không lưu cố định trong file này.
"""

import os
from datetime import datetime

# Giá tham chiếu nội bộ (đ/lít) để tính chi phí & P&L. Có thể override qua biến môi
# trường FUEL_PRICE; mặc định 27.500. Điều phối viên cũng chỉnh tay được tại Module 5.
FUEL_PRICE = float(os.environ.get("FUEL_PRICE", os.environ.get("FUEL_PRICE_FALLBACK", "27500")))
PRODUCT = "Dầu DO 0,05S-II (diesel)"


def get_price():
    """Giá tham chiếu nội bộ CỐ ĐỊNH để tính chi phí & P&L (chỉnh tay tại Module 5).
    Giá thị trường thời gian thực: hỏi Trợ lý AI (tra cứu Google)."""
    now = datetime.now()
    return {
        "price": round(FUEL_PRICE), "currency": "VND", "product": PRODUCT,
        "source": "Giá tham chiếu nội bộ (chỉnh tại Module 5)", "status": "reference",
        "fetched_at": now.isoformat(timespec="seconds"),
        "fetched_display": now.strftime("%d/%m/%Y %H:%M"),
        "note": ("Giá tham chiếu nội bộ để tính chi phí. Giá thị trường thời gian thực: "
                 "hỏi Trợ lý AI (tra cứu Google) hoặc chỉnh tại Module 5."),
    }


def get_diesel_price():
    """Số đ/lít để engine/financials dùng trực tiếp."""
    try:
        return float(get_price()["price"])
    except Exception:
        return FUEL_PRICE


def get_fuel_price_for_ai():
    """Ngữ cảnh giá nhiên liệu cho Trợ lý AI (giá tham chiếu nội bộ + thời điểm + nguồn)."""
    p = get_price()
    return {
        "gia_nhien_lieu": p["price"], "don_vi": "đ/lít", "san_pham": p["product"],
        "nguon": p["source"],
        "trang_thai": "Giá tham chiếu nội bộ (giá thị trường tra cứu thời gian thực qua Trợ lý AI)",
        "cap_nhat_luc": p.get("fetched_display"), "ghi_chu": p.get("note"),
    }
