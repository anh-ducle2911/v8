# HƯỚNG DẪN BÀN GIAO — HPL Dispatcher (bản hoàn thiện)

Trung tâm điều phối & tối ưu tuyến — Hòa Phát Logistics. Bản này nâng cấp theo
yêu cầu: tách kiến trúc AI, giá nhiên liệu cố định 27.500đ (chỉnh tay), dashboard Excel chuyên nghiệp,
ghép chuyến quay đầu đa tiêu chí, timeline tuyến, bản đồ rõ và giao diện gọn.

## 1. Chạy nhanh
```bash
cd <thư-mục-dự-án>
python3 app.py            # mở http://localhost:8000
```
- Tự nạp 2 file demo trong `data/`. Bật AI trực tuyến: tạo `.env` từ `.env.example`,
  điền `GEMINI_API_KEY`. Không có key → chạy ngoại tuyến bám dữ liệu thật (không vỡ).
- Thiếu `ortools`/`requests` vẫn chạy (greedy + urllib). Bản đồ vẽ đường bộ thật qua
  OSRM khi có mạng; mất mạng → tuyến tham chiếu có nhãn.

## 2. Các file đã sửa / thêm
- `ai_matcher.py` — **viết lại**: lớp thuật toán matching/scoring thuần (không AI).
- `gemini_ai.py` — **viết lại**: lớp AI tạo sinh online (Gemini) + ngoại tuyến, gọi matcher.
- `fuel_price.py` — giá nhiên liệu **cố định 27.500đ/lít** (tham chiếu nội bộ; chỉnh tay tại Module 5). Giá thị trường real-time do Trợ lý AI tra cứu qua Google.
- `excel_report.py` — **viết lại**: dashboard Excel 8 sheet (KPI, chart, Table, định dạng).
- `app.py` — endpoint mới + nối giá nhiên liệu vào P&L + ETA timeline + standby.
- `hpl_engine.py` — `parse_backhaul_workbook` (đọc Excel Module 4).
- `engine_ext.py` — `route_timeline` (ETA từng điểm), ràng buộc cấm tải mở rộng.
- `templates/dashboard.html` — toàn bộ chỉnh UI (xem mục 8).
- `gen_module4_template.py` — **mới**: sinh file mẫu Module 4.
- `data/module4_backhaul_orders_template.xlsx` — **mới**: file đơn bổ sung 3 trường hợp.
- `data/HPL_Dashboard_mau.xlsx` — **mới**: dashboard Excel mẫu.
- Bản gốc lưu ở `_backup_original/`.

## 3. Thuật toán đã bổ sung (ai_matcher.py)
Xét ĐỒNG THỜI: khoảng cách · thời gian/khung giờ · tải · dung tích · loại xe · depot ·
fill-rate · giá nhiên liệu · lợi nhuận · km rỗng · cấm tải. Vi phạm ràng buộc cứng →
loại phương án. Hàm chính: `score_backhaul_match`, `recommend_backhaul_matches`,
`recommend_reassignment_for_incident`, `rank_unassigned_orders`,
`recommend_standby_vehicle_usage`/`select_standby_fleet`,
`calculate_empty_km_reduction`, `calculate_incremental_profit`,
`check_operational_constraints`, `check_road_restrictions`. Kết quả luôn có
`score / violations / reason / decision`.

## 4. Module 4 — ghép chuyến quay đầu
- Nhập đơn: gõ tay, hoặc nút **"Nhập file 3PL"** (mẫu `data/module4_backhaul_orders_template.xlsx`,
  3 sheet: nhập tay / import 3PL / gợi ý tự động). Bắt buộc có vĩ độ/kinh độ điểm lấy & trả.
- Bấm **"Tối ưu ghép chuyến"** → matcher chấm điểm từng cặp xe↔đơn: lệch tuyến, chờ,
  fill chiều về, km rỗng giảm, lợi nhuận thêm, điểm, quyết định, lý do. Bản đồ vẽ chiều về.

## 5. Import Excel đơn bổ sung
`/api/import` (kind=backhaul) → `hpl_engine.parse_backhaul_workbook` đọc mọi sheet (trừ
"Hướng dẫn"), tự nhận cột theo bí danh, ghép khung giờ "HH:MM-HH:MM", nạp vào
`STORE["new_backhaul_orders"]`. Không khớp schema mới → tự thử schema tĩnh cũ.

## 6. Trợ lý AI đọc dữ liệu website
`/api/ai/chat` → `gemini_ai.answer_dispatch_question(q, STORE)`:
`build_ai_context` gom tuyến/đơn/xe/tài chính/giá nhiên liệu/cấm tải/sự cố;
`call_matcher_if_needed` chạy `ai_matcher` khi câu hỏi cần tính (ghép/điều phối lại/
đơn chưa gán/standby); rồi Gemini diễn giải (ngoại tuyến → trả lời theo luật bám dữ liệu).
Xem ngữ cảnh thô tại `/api/ai/context`.

## 7. Giá nhiên liệu → tài chính
`fuel_price.get_price()` trả **giá cố định 27.500đ/lít** (tham chiếu nội bộ) → `app._fin_params`
dùng làm giá chính → mọi P&L (`/api/financial`, dashboard, ghép backhaul) tính theo giá này.
Người dùng **chỉnh tay** ô giá ở Module 5 (override) khi cần. Giá XĂNG DẦU THỊ TRƯỜNG (thời
gian thực) do Trợ lý AI tra cứu trực tiếp qua Google khi được hỏi — KHÔNG crawl cố định.

## 8. Giao diện đã chỉnh
Bỏ "(dữ liệu tĩnh/động)" & step-tag; S1/S2/S3 → "Kịch bản 1/2/3"; "Cần xem xét" →
"Cần rà soát"; Module 3 bỏ trọng số, 1 nút "Chạy kế hoạch tuyến" góc phải + **timeline
tuyến (ETA)** + sửa card "Đơn chưa gán"/"Xe sử dụng" + KPI standby; bản đồ marker đánh số,
phân biệt depot/lấy/trả, popup ETA; Module 5 bỏ 3 dòng thừa, chart nhỏ + màu mới, **ô giá
dầu tự động chỉnh tay được**; Module 6 bỏ màu đỏ + label "Mã đơn"; Module 7 label "Mã đơn";
"Trợ lý điều phối AI" → **"Trợ lý AI"** dạng drawer phải **không che bản đồ**; ràng buộc cấm
tải thêm cột tải-trọng/nguồn/ngày hiệu lực.

## 9. Lưu ý trung thực
- Trợ lý AI trực tuyến tra cứu giá dầu real-time qua Google (cần GEMINI_API_KEY + Internet); giá tính chi phí/P&L cố định 27.500đ, chỉnh tay tại Module 5.
- Excel **không thể** tạo PivotTable/Slicer/Timeline native bằng thư viện Python → đã xuất
  **Excel Table** + sheet "Hướng dẫn" để bấm Insert ▸ PivotTable/Slicer (1 thao tác).
- "Nguồn quy định" cấm tải để nhãn hợp lý + cho chỉnh tay; nên thay bằng văn bản kiểm chứng.
