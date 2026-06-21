# BÁO CÁO NÂNG CẤP — HPL Dispatcher (Hybrid Routing Engine + Auto-optimize)

Bản nâng cấp **chỉ bổ sung & chỉnh sửa có chủ đích** trên code hiện có (không viết lại
từ đầu), theo đúng các guardrail: tái sử dụng OR-Tools sẵn có, không hardcode dữ liệu,
không phá schema/format Excel.

---

## 1. ENGINE ĐỊNH TUYẾN HYBRID (Greedy seed → OR-Tools improve)

### Thuật ngữ trong bài toán này
- **Greedy (constructive heuristic):** thuật toán dựng nghiệm ban đầu nhanh. Ở đây là
  `engine_ext.solve_preset()` — gán đơn vào xe theo trọng số preset (đúng giờ / chi phí /
  chạy rỗng / đơn gấp), tôn trọng đầy đủ ràng buộc (loại xe, tải trọng, dung tích, cấm
  tải theo khung giờ) qua `hpl_engine._compat`. Nhanh, luôn ra nghiệm, nhưng chưa tối ưu
  toàn cục.
- **OR-Tools (Google OR-Tools Routing):** bộ giải VRPTW công nghiệp. Mô hình hóa pickup &
  delivery cùng xe, thứ tự lấy-trước-giao, cửa sổ thời gian (Time dimension), tải trọng &
  dung tích (Capacity dimensions), tương thích loại xe/cấm tải (VehicleVar), cho phép bỏ
  đơn có phạt (Disjunction). Nằm ở `hpl_engine._solve_ortools()`.
- **Metaheuristic GUIDED_LOCAL_SEARCH (GLS):** chiến lược tìm kiếm cục bộ có hướng dẫn của
  OR-Tools — thoát cực tiểu cục bộ bằng cách "phạt" các cạnh hay xuất hiện, để cải thiện
  dần nghiệm trong giới hạn thời gian. Đặt tại `_solve_ortools`:
  `sp.local_search_metaheuristic = GUIDED_LOCAL_SEARCH`.
- **Hybrid (Greedy + OR-Tools):** dùng nghiệm Greedy làm **seed** (nghiệm ban đầu) nạp vào
  OR-Tools qua `routing.ReadAssignmentFromRoutes(...)`, rồi `SolveFromAssignmentWithParameters`
  để GLS **cải thiện** từ điểm xuất phát tốt → hội tụ nhanh hơn và thường cho nghiệm tốt
  hơn so với chạy riêng lẻ.

### Luồng Hybrid (mặc định)
`engine_ext.solve_hybrid()`:
1. **Greedy seed** = `solve_preset(...)`.
2. Nếu `mode='greedy'` hoặc **không có OR-Tools** → trả nghiệm Greedy (fallback an toàn).
3. Ngược lại: `hpl_engine._solve_ortools(valid_orders, fleet, depots, time_limit, seed_routes=greedy_routes)`
   — seed bằng nghiệm Greedy, chạy GLS trong giới hạn thời gian.
4. **So sánh & fallback:** nếu OR-Tools lỗi / timeout / gán được ít đơn hơn Greedy → giữ
   nghiệm Greedy. **Engine LUÔN trả ra output.**

### Giới hạn thời gian (time limit)
- Cấu hình bằng biến môi trường `HPL_SOLVER_TIME_LIMIT_SEC` (mặc định **30s**) hoặc tham số
  `time_limit`. Khuyến nghị OR-Tools cho bài toán lớn là **60–120s** — đặt qua `.env`:
  `HPL_SOLVER_TIME_LIMIT_SEC=90`.

### 3 chế độ (giữ ở backend để debug; mặc định hybrid)
- `HPL_SOLVER_MODE=greedy | ortools | hybrid` (mặc định `hybrid`).
- Người dùng trên UI **chỉ bấm 1 nút** "Chạy kế hoạch tuyến" → luôn chạy hybrid.
- Đổi chế độ tạm thời: API `POST /api/config {"solver_mode":"ortools"}`.

### Ổn định
- Seed cố định (`HPL_SOLVER_SEED`, mặc định 2026) + nghiệm Greedy deterministic → các lần
  chạy lặp lại ổn định. Bắt ngoại lệ đầy đủ; thiếu `ortools` vẫn chạy (greedy).

---

## 2. AUTO-TRIGGER TỐI ƯU KHI CÓ ĐƠN MỚI

Khi `auto_optimize = true` (mặc định) **và đã có kế hoạch tuyến**, các thao tác sau sẽ tự
gọi lại engine và cập nhật dashboard:
- Thêm đơn thủ công: `POST /api/order/add` → `_maybe_auto_optimize("new_order")`.
- Xóa đơn: `POST /api/order/delete` → `_maybe_auto_optimize("delete_order")`.
- Upload Excel đơn mới (file kế hoạch): `POST /api/import` → tối ưu lại (`import_excel`).

Các endpoint này trả thêm cờ `reoptimized: true`; frontend gọi `GET /api/plan` để làm mới
KPI/tuyến/bản đồ ngay.

**Phạm vi tối ưu lại:** chỉ các đơn/tuyến chưa khóa. Tuyến `locked / in_progress / completed`
được **giữ nguyên** (xem mục 3).

---

## 3. TRẠNG THÁI & KHÓA TUYẾN

| Trạng thái | Ý nghĩa | Tối ưu lại? |
|---|---|---|
| `assigned` | Đã gán, chưa chạy | ✅ |
| `locked` | Người dùng đã chốt | ❌ |
| `in_progress` | Tuyến đang chạy | ❌ |
| `completed` | Đã hoàn thành | ❌ |

- Đổi trạng thái: `POST /api/route/status {"vehicle_id","status"}` hoặc dropdown "Trạng thái
  tuyến" trong bảng kế hoạch (Module 3).
- `_run_optimize()` tách các tuyến "đóng băng" (locked/in_progress/completed) ra khỏi vòng
  tối ưu: giữ nguyên tuyến + xe + đơn của chúng, chỉ tối ưu phần còn lại rồi gộp lại.

---

## 4. CẤU HÌNH `auto_optimize`

- Xem/đổi: `GET/POST /api/config` (`auto_optimize`, `solver_mode`, `solver_time_limit`).
- Trên UI: nút **"Tự tối ưu khi có đơn mới: ĐANG BẬT/TẮT"** trên thanh Engine (Module 3).
- `auto_optimize=false` → người dùng phải bấm "Chạy kế hoạch tuyến" thủ công.

---

## 5. OPTIMIZATION LOG

Mỗi lần engine chạy ghi 1 bản ghi vào `data/optimization_log.json` (xem ở Module 7 ▸ "Nhật
ký tối ưu", hoặc `GET /api/optimize/log`) gồm: thời điểm · lý do (manual/new_order/…) ·
engine + lý do fallback · số đơn được tối ưu · số đơn chưa gán + lý do · danh sách tuyến
thay đổi · danh sách tuyến giữ nguyên (đã khóa) · thời gian chạy.

---

## 6. EXCEL IMPORT / EXPORT
- **Import:** giữ nguyên schema/format. File khác cùng schema vẫn nạp & hiển thị bình thường.
- **Export:** đã **bỏ sheet Dashboard** (KPI cards + biểu đồ) và sheet ẩn `_src` để tránh lỗi
  định dạng. Chỉ còn các sheet **dữ liệu dạng Excel Table** + sheet "Hướng dẫn".

---

## 7. MODULE 4 — GHÉP CHUYẾN QUAY ĐẦU
- `gen_module4_cases.py` sinh **3 file** `data/module4_S1.xlsx / _S2 / _S3`, đơn quay đầu bám
  điểm kết thúc tuyến của từng kịch bản (kèm cột "Thứ tự ưu tiên ghép" = dữ liệu trình tự).
- Nút **"Nạp đơn quay đầu mẫu"** (và tự nạp khi Module 4 đang rỗng) sinh đơn từ **kế hoạch
  hiện tại** qua `engine_ext.build_return_orders()` → matcher luôn tìm được **~40–50%** tuyến
  ghép được (S1≈47%, S2≈46%, S3≈52%), không bao giờ "chưa tìm được kết quả".

---

## 8–14. CHI PHÍ/NHIÊN LIỆU · THUẬT NGỮ · BẢN ĐỒ · TRỢ LÝ AI · SỰ CỐ · KPI
- **Chi phí/nhiên liệu:** giá nhiên liệu cố định 27.500đ đẩy thẳng vào mục **Chi phí vận hành**; layout
  2 cột (Công thức trái · Cơ cấu chi phí phải); bỏ phần "AI fuel".
- **Thuật ngữ:** đổi "cụm hành lang"/"hành lang" → **"tuyến"** ở mọi bảng/nhãn (UI + Excel).
- **Bản đồ:** marker điểm lấy/trả thu nhỏ (15px, viền mảnh), bớt đỏ to gây rối.
- **Trợ lý AI:** TRỰC TUYẾN (Gemini có **google_search** grounding → truy cập Internet khi có
  `GEMINI_API_KEY`); cửa sổ **nổi** góc dưới phải, z-index cao (đè bản đồ), **không đẩy layout**,
  persistent, nút mở to hơn; có "Gợi ý cho trang này" theo module (`/api/ai/suggest`). Khi chưa
  có API key vẫn trả lời bám dữ liệu phiên (không còn nhãn "Ngoại tuyến").
- **Sự cố:** dropdown thêm **"Tất cả"** (tự nhận loại theo đơn); Module 6 hiển thị **toàn bộ
  sự cố từ file Excel**, file chưa có thì **tự sinh**; thêm phương án **"Dispatcher tự điền /
  tự note"**.
- **KPI frontend:** sau mỗi lần chạy hiển thị Engine · thời gian chạy · xe dùng · đơn gán ·
  đơn chưa gán · tổng km / km rỗng · doanh thu / chi phí / lợi nhuận.

---

## TÓM TẮT FILE ĐÃ SỬA / THÊM

| File | Thay đổi chính |
|---|---|
| `hpl_engine.py` | Cấu hình engine (`SOLVER_MODE/TIME_LIMIT/SEED`, `_has_ortools`); `solve_vrptw` hỗ trợ 3 mode + seed; `_solve_ortools` nhận `time_limit` + `seed_routes` (ReadAssignmentFromRoutes) |
| `engine_ext.py` | **mới** `solve_hybrid()` (orchestrate greedy→OR-Tools+fallback), **mới** `build_return_orders()`, **mới** `dynamic_event_vi()`, thêm phương án self-fill vào `incident_options()` |
| `app.py` | **mới** `_run_optimize / _optimize_payload / _route_out / _maybe_auto_optimize`; endpoint `/api/plan`, `/api/route/status`, `/api/config`, `/api/optimize/log`, `/api/backhaul/load_sample`, `/api/ai/suggest`; seed sự cố từ Excel + tự sinh + hydrate; auto-trigger ở order add/delete/import |
| `gemini_ai.py` | `_call_gemini` bật google_search (Internet); nhãn "Trực tuyến"; bỏ "Ngoại tuyến"; **mới** `module_advice()` |
| `excel_report.py` | bỏ sheet Dashboard + `_src` + helper biểu đồ; chỉ xuất sheet dữ liệu; cập nhật Hướng dẫn |
| `gen_module4_cases.py` | **mới** — sinh 3 file đơn quay đầu S1/S2/S3 (~40–50% ghép) |
| `templates/dashboard.html` | KPI mở rộng + thanh Engine + toggle auto-optimize + dropdown trạng thái/khóa tuyến + Nhật ký tối ưu; layout tài chính 2 cột + giá dầu vào chi phí; marker nhỏ; dock AI nổi/online; "Tất cả" + self-fill; đổi "hành lang"→"tuyến" |

### Hàm OR-Tools hiện có được gọi lại ở đâu
`hpl_engine._solve_ortools()` (đã có sẵn) được **tái sử dụng**, gọi từ
`engine_ext.solve_hybrid()` với tham số `seed_routes` (nghiệm Greedy) — không viết lại solver.

---

## CÁCH TEST BẰNG MỘT ĐƠN MỚI
1. Mở `http://localhost:8000` → Module 3 ▸ **Chạy kế hoạch tuyến** (xem KPI + thanh Engine).
2. (Tùy chọn) Khóa 1 tuyến: dropdown "Trạng thái tuyến" → **Đã khóa**.
3. Module 1 ▸ **Thêm đơn thủ công** (điền tọa độ lấy/trả, tải, doanh thu) → Lưu.
4. Vì `auto_optimize=ĐANG BẬT`, hệ thống tự tối ưu lại; quay lại Module 3 thấy KPI cập nhật,
   **tuyến đã khóa giữ nguyên**, và Module 7 ▸ "Nhật ký tối ưu" có dòng mới (lý do "Thêm đơn mới").

## BẬT/TẮT AUTO OPTIMIZATION
- UI: nút "Tự tối ưu khi có đơn mới" trên thanh Engine (Module 3).
- API: `POST /api/config {"auto_optimize": false}`.
- Mặc định: **bật**.

## KÍCH HOẠT HYBRID (OR-Tools) & INTERNET CHO TRỢ LÝ AI
- Hybrid cần `ortools` (đã có trong `requirements.txt`): `pip install -r requirements.txt`.
  Thiếu `ortools` → engine tự chạy Greedy (vẫn đúng ràng buộc, vẫn ra kết quả).
- Trợ lý AI truy cập Internet: đặt `GEMINI_API_KEY` trong `.env`.
- Thời gian metaheuristic: `HPL_SOLVER_TIME_LIMIT_SEC=90` trong `.env` (khuyến nghị 60–120s).
