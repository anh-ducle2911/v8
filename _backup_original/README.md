# Hòa Phát Logistics — Trung tâm điều phối & tối ưu tuyến

Website demo điều phối vận tải cho **Công ty Cổ phần Tiếp vận Hòa Phát**. Giao diện
tiếng Việt, nền sáng, phối màu xanh navy `#0B3D91` và đỏ `#E2231A` theo nhận diện
thương hiệu. Thể hiện rõ luồng **từ kế hoạch tĩnh sang xử lý động khi có sự cố**.

Hệ thống tách bạch hai phần:
- **Routing engine / optimization engine** — thuật toán gán xe, lập tuyến, tính chi
  phí, xử lý ràng buộc vận hành (`hpl_engine.py`, `engine_ext.py`).
- **AI tạo sinh (Gemini API)** — đọc hiểu & ánh xạ dữ liệu, giải thích lỗi, phân
  tích sự cố và trợ lý hỏi đáp (`gemini_ai.py`).

---

## 1. Cài đặt & chạy

```bash
cd HPL-Dispatcher-v3
pip install -r requirements.txt
python app.py
```

Mở trình duyệt: **http://localhost:8000**

- Website **tự nạp 2 file mẫu** trong `data/` khi khởi động nên có dữ liệu ngay.
  Bấm **Nạp dữ liệu mẫu** để nạp lại, hoặc kéo–thả file Excel của bạn ở Module 1.
- Thiếu `ortools` → engine tự dùng heuristic gán theo preset (vẫn tôn trọng đủ ràng buộc).
- Bản đồ vẽ **tuyến đường bộ thực tế** qua OSRM (cần Internet). Khi không lấy được
  tuyến đường bộ, hệ thống báo: *"Không tìm thấy tuyến đường bộ phù hợp…"*.

### Bật AI tạo sinh (Gemini)

Không hard-code API key. Tạo file `.env` từ mẫu rồi điền key:

```bash
cp .env.example .env
# Mở .env và điền:  GEMINI_API_KEY=AIza...
```

Lấy key tại https://aistudio.google.com/app/apikey. Khi chưa cấu hình key, hệ thống
chạy ở **chế độ ngoại tuyến** — vẫn hoạt động đầy đủ, chỉ khác phần diễn giải bằng
ngôn ngữ tự nhiên (ánh xạ cột dùng khớp mờ, trợ lý trả lời theo luật dựa trên dữ liệu).

---

## 2. Tám module

| # | Module | Chức năng chính |
|---|---|---|
| 1 | **Nhập dữ liệu & ánh xạ** | Tải Excel (tĩnh / động / đơn bổ sung quay đầu), nhập thủ công, **xem trước & sửa trực tiếp từng dòng**, ánh xạ cột bằng Gemini |
| 2 | **Kiểm định dữ liệu** | Bắt lỗi cứng/mềm, cột *Lý do cần xem xét*, lọc/tìm kiếm, ghi chú điều phối, đánh dấu trạng thái |
| 3 | **Kế hoạch tuyến & bản đồ** | Gán xe theo **preset/trọng số**, bản đồ tuyến đường bộ (OSRM), bảng **Đơn chưa gán** kèm lý do & gợi ý |
| 4 | **Ghép chuyến quay đầu** | Bổ sung **đơn mới** (Excel/thủ công) để ghép chiều về, tối ưu round-use, xem tuyến chiều về trên bản đồ |
| 5 | **Tài chính P&L** | Dashboard chi phí theo hạng mục thực tế, chỉ báo biên lợi nhuận, công thức nền sáng, **cập nhật khi có sự cố/ghép chuyến** |
| 6 | **Phát hiện sự cố khẩn cấp** | Từ đơn tĩnh → mở case động, AI phân tích & engine đề xuất phương án, Dispatcher chọn + ghi chú, hướng xử lý mềm |
| 7 | **Nhật ký & lưu vết** | Lưu toàn bộ thao tác, tìm kiếm/lọc, xóa từng dòng có xác nhận, xuất Excel |
| 8 | **Trợ lý điều phối AI** | Cửa sổ hỏi đáp góc dưới phải, trả lời **bám dữ liệu trong phiên** |

Ngoài ra có mục **Ràng buộc vận hành** (quy định cấm tải theo khu vực, loại xe,
tuyến, khung giờ, ngày áp dụng — xem & chỉnh được) và **Bản đồ điều phối** toàn mạng.

> Không có module "phân cụm" độc lập. Việc gom đơn cùng hành lang chỉ là một bước
> hỗ trợ bên trong thuật toán.

---

## 3. Mô hình tài chính P&L

```
Doanh thu tuyến  = Tổng cước vận chuyển các đơn (+ phụ phí điểm + phí chờ thu được)
− Nhiên liệu     = Km có tải × Mức tiêu hao (lít/km) × Giá nhiên liệu
− Cầu đường      = Km liên tỉnh × đơn giá BOT/km            (nội thành không qua trạm)
− Tài xế         = Lương phân bổ/chuyến + Phụ cấp + Tăng ca khi vượt giờ
− Chi phí xe     = Khấu hao + Bảo dưỡng + Bảo hiểm phân bổ
− Bốc xếp        = Bốc + dỡ theo đơn
− Chạy rỗng      = (Km rỗng − quãng điều xe miễn phí) × đơn giá vận hành chiều rỗng
− Quản lý        = Tỷ lệ % × Doanh thu
= Lợi nhuận gộp  → Biên = Lợi nhuận / Doanh thu × 100%

+ Chi phí phát sinh do sự cố (xe thay thế, chuyển tải, chờ, phạt, đi vòng)
→ Lợi nhuận & biên SAU xử lý sự cố
```

Chỉ báo biên lợi nhuận theo vùng: dưới 0% (lỗ) · 0–10% (rủi ro thấp lợi nhuận) ·
10–17% (cần xem xét) · **17–22% (vùng mục tiêu thực tế)** · trên 22% (tốt — cần kiểm
tra tính bền vững). Trên dữ liệu mẫu, biên kế hoạch rơi khoảng **16–24%** tùy kịch bản.

---

## 4. Luồng demo gợi ý

1. Nạp dữ liệu tĩnh → **Module 1**, xem trước & sửa đơn nếu cần.
2. **Module 2**: kiểm định, xem *Lý do cần xem xét*, ghi chú.
3. **Module 3**: chọn preset (vd *Ưu tiên giảm chạy rỗng*) → Chạy kế hoạch tuyến →
   xem bản đồ, xem **Đơn chưa gán**.
4. **Module 4**: thêm đơn bổ sung → Tìm gợi ý ghép chiều về → Chấp nhận.
5. **Module 5**: Tính tài chính → xem biên & cơ cấu chi phí.
6. **Module 6**: nhập một mã đơn → Mở xử lý sự cố → chọn phương án → ghi chú →
   **Xác nhận áp dụng** (P&L cập nhật) → **Đánh dấu hoàn tất**.
7. **Module 7**: xem nhật ký. Bấm **Xuất Excel** để tải báo cáo.

---

## 5. Cấu trúc dự án

```
HPL-Dispatcher-v3/
├── app.py             # Flask backend + REST API /api/*
├── hpl_engine.py      # Lõi: parse Excel, kiểm định, cấm tải, VRPTW, P&L, sự cố tĩnh→động
├── engine_ext.py      # Mở rộng: ràng buộc cấm tải, P&L chi tiết, ghép quay đầu (đơn mới),
│                      #          solver theo preset, sinh phương án sự cố, ngữ cảnh trợ lý
├── gemini_ai.py       # AI tạo sinh Gemini + chế độ ngoại tuyến (ánh xạ, giải thích, trợ lý)
├── excel_report.py    # Xuất Excel 7 sheet, font Times New Roman (không CSV)
├── templates/dashboard.html   # Giao diện 8 module (nền sáng, navy/đỏ, không emoji)
├── data/              # 2 file Excel mẫu + incident_log.json + constraints.json
├── requirements.txt
├── .env.example       # Mẫu cấu hình GEMINI_API_KEY
└── README.md
```

API chính: `/api/status`, `/api/import`, `/api/load_demo`, `/api/preview`,
`/api/order/{update,add,delete}`, `/api/validate`, `/api/optimize`, `/api/map_data`,
`/api/backhaul[/orders|/accept]`, `/api/financial`,
`/api/incident/{from_order,<case_id>,resolve,complete}`, `/api/incidents`,
`/api/log[/delete|/clear]`, `/api/constraints`, `/api/assistant`, `/api/export`.

---

## 6. Triển khai online (tùy chọn)

App Python/Flask chạy 1 lệnh, phù hợp demo trong ngày. Để có domain riêng có thể
deploy lên **Render / Railway / Fly.io** với `gunicorn app:app`; nhớ đặt biến môi
trường `GEMINI_API_KEY` trên dashboard nền tảng (không commit key vào mã nguồn).
