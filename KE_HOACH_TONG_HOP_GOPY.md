# BẢN GIAO TASK — HPL DISPATCHER · ĐỢT 1 (ĐÃ CHỐT)

> Trạng thái: **mọi mục "Cần làm rõ" đã được chốt bằng câu trả lời C1–C13 của chủ sản phẩm.** Tài liệu này là bản giao task sẵn-sàng-thực-thi cho cửa sổ mới: đọc Phần 1 (quyết định) → Phần 2 (lộ trình) → Phần 3 (spec AI), rồi bắt tay code. Phần 4 là bản tổng hợp & phân xử gốc (tham chiếu A–E). GIỮ NGUYÊN bảng màu HPL (navy #0B3D91 / đỏ #E2231A), chỉ tinh chỉnh cách dùng. Mọi thay đổi trên 1 file vanilla `templates/dashboard.html` + vài hàm backend; KHÔNG đổi framework, KHÔNG đập backend.

---

## 1. QUYẾT ĐỊNH ĐÃ CHỐT (C1–C13)

| C | Câu hỏi | ✅ Quyết định CHỐT | Hệ quả cho task |
|---|---|---|---|
| **C1** | Persist dữ liệu qua restart? | **GIỮ TRONG PHIÊN (RAM) là đủ. KHÔNG persist xuống đĩa.** | Bỏ hẳn task "persist file/DB" (L9 cũ). STORE in-memory giữ nguyên. localStorage (nếu làm) CHỈ cho UI-preference, tuyệt đối KHÔNG cache số nghiệp vụ. |
| **C2** | Vào M4/M5 khi chưa có kế hoạch? | **(a) Tự chạy lập tuyến NGẦM rồi hiện tài chính.** | Q11 chốt: guard "thiếu routes → await /api/plan (auto optimize) + toast 'Đang lập tuyến để tính tài chính…' → mới render". Lỗi/không có dữ liệu nền → empty-state CTA, KHÔNG màn lỗi đỏ. |
| **C3** | Số KPI M3? | **(B) Gộp 8 thẻ về 1 lưới + nhãn cụm `.sec-label` + 1 thẻ HERO.** Giữ đủ 8 chỉ số. | Q-mới L2: gộp `#plan-kpis`+`#plan-kpis2` thành 1 grid; thẻ **Lợi nhuận = hero** (cỡ lớn). ⚠ xóa cả lệnh gán `#plan-kpis2` (dòng 795) + reset (776). |
| **C4** | Mô hình sidebar? | **(A) Giữ ĐÁNH SỐ BƯỚC + gộp nông mục trùng (9 → ~6-7).** KHÔNG refactor 5 tab. | Q9 + A1.x: gộp Bản đồ toàn mạng vào M3 (nút mở rộng), M6+M7 thành "Vận hành" (tab), Ràng buộc → ⚙ Cài đặt. Giữ cơ chế `nav()` view-* hiện có. |
| **C5** | Drawer vs xếp dọc M3? | **(A) ROW DRAWER trượt phải khi bấm dòng; bản đồ M3 GIỮ NGUYÊN.** | L1: thu bảng 15/13 cột → 6-8 cột + panel chi tiết phải. Bỏ phương án xếp dọc (A2.11). Bản đồ vẫn cạnh bảng → bấm dòng vẫn thấy phản hồi. |
| **C6** | Phạm vi fullscreen? | **PHỦ KÍN TOÀN MÀN (ẩn sidebar + topbar).** | Q8: `.fs{position:fixed;inset:0;z-index:--z-overlay-1;background:#fff}` cho bảng & bản đồ + nút thoát + Esc. ⚠ gọi `map.invalidateSize()` sau khi vào/thoát fullscreen bản đồ. |
| **C7** | H2 trang 20 hay 24px? | **24px** (chốt bởi hội đồng): `--fs-2xl:24px`, `letter-spacing:-.3px`, `line-height:1.2`. | Q1 token typography: h2=24 (cách card h3=16 đủ 8px tách tầng), tạo cảm giác premium + phân cấp rõ. |
| **C8** | Count-up KPI? | **CÓ — chỉ 1 thẻ SỐ ĐẾM** (vd "Đơn được gán N/Tổng"), + `prefers-reduced-motion` hiện ngay + `tabular-nums`. **TUYỆT ĐỐI KHÔNG count-up số tiền/biên LN** (thẻ hero Lợi nhuận hiện tức thì, nổi bằng cỡ chữ). | Q4/L2: count-up tách khỏi thẻ hero tài chính. |
| **C9** | Đã có GEMINI_API_KEY? | **CÓ.** | Cần đảm bảo máy chạy có file `.env` (repo chỉ có `.env.example`) chứa `GEMINI_API_KEY` → trợ lý chạy ONLINE (google_search real-time hoạt động). Việc duy nhất: tạo `.env`. |
| **C10** | Danh mục câu hỏi vàng về đơn? | **Đã trích xuất 100% — xem Phần 3** (139 trường + 24 câu hỏi, kiểm chứng `file:line`). | Q13/A5.1: viết `get_order_detail` theo spec Phần 3. |
| **C11** | Real-time dữ liệu mở khác? | **Không viết crawler riêng — dựa `google_search` của Gemini (đã bật `web=True`).** | Đảm bảo `ask_gemini` luôn gọi `web=True` (đã đúng, gemini_ai.py:451) + prompt cho phép tra cứu chủ đề mở khi online. "Bên họ tự làm" phần nguồn khác. |
| **C12** | Badge nguồn + thời điểm dưới câu trả lời AI/giá dầu? | **BẬT** (mặc định — đúng tinh thần minh bạch real-time của chủ sản phẩm; backend đã trả `source`/`nguon`/`trang_thai`/`cap_nhat_luc`). | Q13: render badge nhỏ "Trực tuyến · Gemini · giờ" / "Trợ lý AI · dữ liệu phiên" dưới mỗi câu trả lời + cạnh giá dầu M5. |
| **C13** | Bỏ `loadLog()` ở init? | **BỎ — xác nhận** không nơi nào cần nhật ký sẵn trước khi mở M7. | Q12: xóa `loadLog()` khỏi init (dashboard.html:1345); M7 tự tải khi mở. |

**Tác động lên các mâu thuẫn (Phần 4-B):** Conflict #1 & #2 → auto-run ngầm + KHÔNG persist (C1,C2). #3 giữ radius 12. #4 shadow 2 lớp + hover-lift chọn lọc. #5 giữ topbar sáng. #6 count-up chỉ số đếm (C8). #7 gộp 1 lưới + hero (C3). #8 không thêm landing. #9 giữ đánh số (C4). #10 modal nặng + undo nhẹ. #11 không refactor badge.

---

## 2. LỘ TRÌNH THỰC THI (đã cập nhật theo quyết định chốt)

### ⚡ Quick wins — Đợt CSS/UX nền (làm trước, rủi ro thấp)
| # | Task | Chi tiết chốt | Công | Tham chiếu |
|---|---|---|---|---|
| **Q1** | **Token hóa `:root`** | type 8 cấp (**h2=`--fs-2xl`24px** per C7, card h3=16, xóa cỡ thập phân) + radius 4 cấp (**giữ --radius:12px**) + z-index (dock < overlay < modal < toast) + elevation 2 lớp ám navy + `--ease/--dur/--focus-ring`. | 3-4h | A3.1/A3.6/A6.1, #3 |
| **Q2** | **A11y nav + modal + toast** | nav `role=button`+`tabindex=0`+`aria-current`+`onkeydown(Enter/Space)`; focus-trap + **Esc-to-close** + `role=dialog`/`aria-modal` + trả focus cho #modal/#route-modal/#dock; toast `role=status`+`aria-live`; `aria-label` nút ×/Xóa (kèm mã đơn); skip-link. | 4h | A4.1-A4.4 |
| **Q3** | **Sửa contrast FAIL + focus ring 3px** | b-rev→`#8A5E00`; nhãn gauge `.seg` text-shadow; disabled .5→.6; **spinner trắng on-dark** (đang 1.00:1 tàng hình); focus ring 3px nhất quán (`.edit` 2px→3px). | 1.5h | A4.5/A4.6/A3.11 |
| **Q4** | **Màu brand + chuyển động** | chart/gauge về palette HPL `['#0B3D91','#1565C0','#4F86D6','#9DBDEA','#B07A00','#E2231A','#9AA7BD']`; `tabular-nums` cho `.kpi .val`/`.kv`/số tài chính; **`@media(prefers-reduced-motion)` block** (.pulse, count-up, keyframes). | 1.5h | A3.2-A3.4/A4.9, #6/C8 |
| **Q5** | **Quy ước màu nút + microcopy** | đỏ CHỈ phá hủy: Xuất Excel→`btn-line`, Xóa toàn bộ→`btn-red`; `api()` tách lỗi mạng vs nghiệp vụ; cảnh báo xóa toàn bộ log nêu số dòng + "không thể hoàn tác" (1290). | 1.5h | A3.5/A6.4 |
| **Q6** | **`saveCell` an toàn dữ liệu** | lưu giá trị cũ trước khi gửi; catch → khôi phục `el.textContent` + viền đỏ; đang lưu=amber, OK=green; chỉ báo "đang đồng bộ" topbar. | 2h | A6.3/A6.9 |
| **Q7** | **z-index dock < modal** | token z-* phân tầng (dock 1200→`--z-dock` dưới `--z-overlay`). | 0.5h | A6.2 |
| **Q12** | **Perf + dọn init** | breakpoint 1450/640; `defer` Leaflet + lazy-load Chart.js (chỉ khi mở M5); OSRM cache(Map)+AbortController timeout ~4s; debounce search 120ms; **bỏ `loadLog()` init (C13)**. | 3h | A2.4/A4.7/A4.8/A4.13/C13 |

### ⚡ Quick wins — Đợt tính năng theo yêu cầu trực tiếp
| # | Task | Chi tiết chốt | Công | Tham chiếu |
|---|---|---|---|---|
| **Q8** | **Nút FULLSCREEN bảng + bản đồ** | **phủ kín toàn màn (C6)** `.fs position:fixed inset:0` + nút thoát + Esc; ⚠ `invalidateSize()` sau vào/thoát map. | 3h | A2.2/C6 |
| **Q9** | **Gộp module trùng (C4)** | Bản đồ toàn mạng → nút "Mở rộng" trong M3 (dọn `drawFullMap` 950 + nhánh nav 612 + option `data-view='map'`); Ràng buộc → ⚙ Cài đặt (giữ `data-view='constraints'`). | 2h | A1.3/A1.4, #9 |
| **Q10** | **Thanh stepper bấm-được (KHÔNG khóa)** | render từ `STATE`/`/api/status`: Nạp→Kiểm định→Lập tuyến→Ghép→P&L→Xuất, mỗi bước trạng thái Chưa làm/Có lỗi/Sẵn sàng/Hoàn tất, bấm để nhảy; kích hoạt `.step-tag`. **KHÔNG `pointer-events:none`.** | 4h | A1.1/A1.5, #1/#8 |
| **Q11** | **Auto-run optimize ngầm (C2=a)** | guard vào M4/M5 thiếu `STATE.routes` → `await runOptimize()` ngầm + toast → render finance/backhaul; empty-state CTA nếu lỗi. | 3h | A1.2, #1/C2 |
| **Q13** | **AI tra cứu đơn (C9/C10/C11/C12)** | tạo `.env` với GEMINI key (C9); viết **`get_order_detail` theo Phần 3**; thêm vào `build_ai_context`/`_offline_assistant` nhánh "tra cứu 1 đơn" + bổ sung keywords `needs_matcher`; nút **"✨ Hỏi AI lý do"** cạnh đơn chưa gán; **badge nguồn+thời điểm (C12)**; đảm bảo `ask_gemini` web=True (C11). | 6-8h | A5.1-A5.5/C9-C12 |

### 🏗️ Dài hạn
| # | Task | Chi tiết chốt | Công | Tham chiếu |
|---|---|---|---|---|
| **L1** | **Row drawer chi tiết (C5=A)** | thu bảng Kế hoạch 15c & P&L 13c → 6-8 cột (Mã xe·Tuyến·Đơn·Tải%·Km rỗng·Lợi nhuận·Trạng thái); panel trượt phải khi bấm dòng (lỗi/gợi ý/tọa độ/tài chính/hành động); bản đồ giữ nguyên. | 8-10h | A2.1, #5/C5 |
| **L2** | **Gộp 1 lưới KPI + hero (C3=B)** | gộp 2 grid → 1 + `.sec-label` nhãn cụm + thẻ Lợi nhuận hero (cỡ lớn, hiện ngay) + count-up 1 thẻ đếm (C8); layout 3 tầng; %Tải → mini progress bar. ⚠ xóa `#plan-kpis2` (795)+reset(776). | 5h | A2.3/A2.9/A2.5, #7/C3 |
| **L3** | **Gộp M6+M7 → "Vận hành"** | tab nội bộ (Xử lý sự cố / Nhật ký), `logTab()` toggle theo ID riêng. | 5h | A1.6, #9/C4 |
| **L4** | **confirmBox + Undo-toast** | `#confirm-modal` RIÊNG cho thao tác nặng (xóa toàn bộ log, áp P&L, hoàn tất sự cố) + Undo-toast cho nhẹ (xóa 1 đơn/dòng). | 5h | A6.7, #10 |
| **L5** | **localStorage UI-preference** | nhớ module/sidebar/bộ lọc/density khi F5 — **KHÔNG cache routes/finance (C1).** | 3h | A1.12, #2/C1 |
| **L6** | **Command palette ⌘K + phím tắt 1–7** | index module + mã đơn/xe; Esc đóng lớp nổi. | 6-8h | A6.10 |
| **L7** | **Hợp nhất nguồn backhaul** | `/api/backhaul` → alias matcher + gộp lối nhập M1→M4. ⚠ đọc app.py:1061-1458 + ai_matcher.py xác nhận route UI gọi TRƯỚC; ⚠ loop drag&drop 1337. | 4h | A1.8/A1.9 |
| **L8** | **Test snapshot AI** | bộ test đảm bảo `get_order_detail` phủ 100% trường (Phần 3) cho mọi câu hỏi vàng. | 5h | A5.7/C10 |

> ❌ **ĐÃ LOẠI khỏi lộ trình:** persist xuống đĩa (C1 — giữ trong phiên đủ); wizard khóa cứng/`pointer-events:none`; topbar navy gradient; giảm radius 12→8; cắt KPI còn 4; landing Dashboard; refactor sidebar 5 tab; viết lại tool giá dầu/AI search (đã real-time); đổi màu `L.divIcon` sang `var()`; refactor badge (đã đạt). Chi tiết lý do: Phần 4-D.

### ⚠️ Lưu ý hồi quy kỹ thuật (kiểm trước mỗi commit)
1. **`map.invalidateSize()` BẮT BUỘC** sau mọi đổi layout chứa #map/#bk-map/#inc-map (fullscreen Q8, drawer L1, gộp grid). Pattern có sẵn (dashboard.html:613/946).
2. **Loop drag&drop dòng 1337:** nếu gộp lối nhập M1→M4 (L7) mà xóa card backhaul M1 → phải bỏ `'backhaul'` khỏi mảng key, nếu không `.previousElementSibling` của null ném TypeError lúc init → chết toàn bộ JS.
3. **Gộp 2 grid KPI (L2):** xóa CẢ lệnh gán `#plan-kpis2` (795) + reset (776).
4. **`L.divIcon` (902-904):** KHÔNG đổi màu sang `var()` (template string không nội suy CSS var → marker mất màu). Màu chart qua JS array thì đổi tự do (Q4).
5. **Xóa view-map (Q9):** dọn kèm `drawFullMap()` (950) + nhánh nav (612) + option `data-view='map'`.
6. **`#confirm-modal` (L4) phải RIÊNG** — không tái dùng #modal/#route-modal (xung đột trạng thái).
7. **Auto-run (Q11):** `/api/financial` & `/api/backhaul` chặn `if not routes` → phải `await` optimize XONG mới gọi; tránh race điều kiện.

---

## 3. SPEC C10 — `get_order_detail(store, order_id)` + DANH MỤC CÂU HỎI VÀNG (đã kiểm chứng 100%)

> Trích xuất & kiểm chứng đối kháng: **139 trường** (8 nhóm thực thể) · **24 câu hỏi vàng**. Mọi `field_key` đã xác minh tồn tại trong code theo `file:line`. Đây là nguồn chân lý để cửa sổ mới viết hàm `get_order_detail` + mở rộng router intent (A5.1/A5.3/Q13) — bảo đảm KHÔNG thiếu/sai trường nào khi điều phối viên hỏi về đơn.

### 3.1 Bản đồ trường đầy đủ (field inventory)

#### 1) Trường gốc của đơn (don_goc) — 51 trường

| field_key | Nhãn | Nguồn (file:line) | Ghi chú |
|---|---|---|---|
| `order_id` | Mã đơn | `_norm_static_order hpl_engine.py:432` | Khóa định danh; khớp Order_ID sheet S1/S2/S3. ĐÃ XÁC MINH. |
| `scenario` | Kịch bản | `_norm_static_order hpl_engine.py:433` | Scenario_ID. ĐÃ XÁC MINH. |
| `planning_date` | Ngày kế hoạch | `_norm_static_order hpl_engine.py:434` | Planning_Date. ĐÃ XÁC MINH. |
| `customer` | Khách hàng | `_norm_static_order hpl_engine.py:435` | Customer_Name. ĐÃ XÁC MINH. |
| `customer_group` | Nhóm khách hàng | `_norm_static_order hpl_engine.py:436` | Customer_Group. ĐÃ XÁC MINH. |
| `channel` | Kênh | `_norm_static_order hpl_engine.py:437` | Channel. ĐÃ XÁC MINH. |
| `product` | Nhóm sản phẩm | `_norm_static_order hpl_engine.py:438` | Product_Group. ĐÃ XÁC MINH. |
| `pickup_id` | Mã điểm lấy | `_norm_static_order hpl_engine.py:439` | Pickup_ID. ĐÃ XÁC MINH. |
| `pickup_name` | Tên điểm lấy | `_norm_static_order hpl_engine.py:440` | Pickup_Name. ĐÃ XÁC MINH. |
| `pickup_province` | Tỉnh lấy | `_norm_static_order hpl_engine.py:441` | Pickup_Province. ĐÃ XÁC MINH. |
| `pickup_district` | Huyện lấy | `_norm_static_order hpl_engine.py:442` | Pickup_District. ĐÃ XÁC MINH. |
| `pickup_lat` | Vĩ độ điểm lấy | `_norm_static_order hpl_engine.py:443 (_f)` | Pickup_Lat; thiếu -> hard error (validate_orders:637). ĐÃ XÁC MINH. |
| `pickup_lon` | Kinh độ điểm lấy | `_norm_static_order hpl_engine.py:444 (_f)` | Pickup_Lon. ĐÃ XÁC MINH. |
| `delivery_id` | Mã điểm trả | `_norm_static_order hpl_engine.py:445` | Delivery_ID. ĐÃ XÁC MINH. |
| `delivery_name` | Tên điểm trả | `_norm_static_order hpl_engine.py:446` | Delivery_Name; cũng là vị trí sự cố tĩnh (incident_from_static_order:1523). ĐÃ XÁC MINH. |
| `delivery_province` | Tỉnh trả | `_norm_static_order hpl_engine.py:447` | Delivery_Province. ĐÃ XÁC MINH. |
| `delivery_district` | Huyện trả | `_norm_static_order hpl_engine.py:448` | Delivery_District. ĐÃ XÁC MINH. |
| `delivery_lat` | Vĩ độ điểm trả | `_norm_static_order hpl_engine.py:449 (_f)` | Delivery_Lat. ĐÃ XÁC MINH. |
| `delivery_lon` | Kinh độ điểm trả | `_norm_static_order hpl_engine.py:450 (_f)` | Delivery_Lon. ĐÃ XÁC MINH. |
| `corridor` | Hành lang/Corridor | `_norm_static_order hpl_engine.py:451` | Corridor. ĐÃ XÁC MINH. |
| `route_axis` | Trục tuyến | `_norm_static_order hpl_engine.py:452` | Route_Axis. ĐÃ XÁC MINH. |
| `direct_km` | Khoảng cách trực tiếp (km) | `_norm_static_order hpl_engine.py:453 (_f)` | Direct_Distance_km; >100km -> soft warning backhaul (validate_orders:658). ĐÃ XÁC MINH. |
| `weight_kg` | Khối lượng (kg) | `_norm_static_order hpl_engine.py:454 (_f)` | Weight_kg; <=0 -> hard error (validate_orders:647). ĐÃ XÁC MINH. |
| `volume_m3` | Thể tích (m3) | `_norm_static_order hpl_engine.py:455 (_f)` | Volume_m3. ĐÃ XÁC MINH. |
| `pallet` | Số pallet | `_norm_static_order hpl_engine.py:456 (_f)` | Pallet_Qty. ĐÃ XÁC MINH. |
| `min_vehicle` | Loại xe tối thiểu | `_norm_static_order hpl_engine.py:457` | Min_Vehicle_Type; thiếu -> hard error (validate_orders:643). ĐÃ XÁC MINH. |
| `max_vehicle` | Loại xe tối đa cho phép | `_norm_static_order hpl_engine.py:458` | Max_Vehicle_Type_Allowed; veh_rank(min)>veh_rank(max) -> REVIEW Split (validate_orders:651). ĐÃ XÁC MINH. |
| `need_refrigeration` | Cần xe lạnh | `_norm_static_order hpl_engine.py:459 (_yes)` | Required_Refrigeration bool. ĐÃ XÁC MINH. |
| `can_consolidate` | Cho phép gom đơn | `_norm_static_order hpl_engine.py:460 (_yes default True)` | Can_Consolidate. ĐÃ XÁC MINH. |
| `dedicated` | Xe chuyên dụng/riêng | `_norm_static_order hpl_engine.py:461` | Dedicated_Vehicle (giá trị thô từ sheet, không qua _yes). ĐÃ XÁC MINH. |
| `inner_city` | Hạn chế nội đô | `_norm_static_order hpl_engine.py:462 (_yes)` | Inner_City_Restriction; dùng road_ban_conflict (hpl_engine.py:617). ĐÃ XÁC MINH. |
| `access_note` | Ghi chú tiếp cận | `_norm_static_order hpl_engine.py:463` | Access_Note. ĐÃ XÁC MINH. |
| `pickup_tw_start` | Khung giờ lấy - bắt đầu (phút) | `_norm_static_order hpl_engine.py:464 (time_to_min)` | Pickup_TW_Start; phút từ 0h, hiển thị qua eng.min_to_hhmm. ĐÃ XÁC MINH. |
| `pickup_tw_end` | Khung giờ lấy - kết thúc (phút) | `_norm_static_order hpl_engine.py:465 (time_to_min default 1440)` | Pickup_TW_End. ĐÃ XÁC MINH. |
| `drop_tw_start` | Khung giờ trả - bắt đầu (phút) | `_norm_static_order hpl_engine.py:466 (time_to_min)` | Drop_TW_Start; app.py:493 ghép chuỗi drop_tw. ĐÃ XÁC MINH. |
| `drop_tw_end` | Khung giờ trả - kết thúc (phút) | `_norm_static_order hpl_engine.py:467 (time_to_min default 1440)` | Drop_TW_End; nếu < pickup_tw_start -> hard error (validate_orders:641). ĐÃ XÁC MINH. |
| `tw_flex_min` | Độ linh hoạt khung giờ (phút) | `_norm_static_order hpl_engine.py:468 (_f default 30)` | TW_Flex_Min. ĐÃ XÁC MINH. |
| `pickup_service` | Thời gian phục vụ điểm lấy (phút) | `_norm_static_order hpl_engine.py:469 (_f default 25)` | Pickup_Service_Min; dùng route_timeline (engine_ext.py:848). ĐÃ XÁC MINH. |
| `drop_service` | Thời gian phục vụ điểm trả (phút) | `_norm_static_order hpl_engine.py:470 (_f default 25)` | Drop_Service_Min; dùng route_timeline (engine_ext.py:851). ĐÃ XÁC MINH. |
| `lead_time` | Lead time (phút) | `_norm_static_order hpl_engine.py:471 (_f)` | Lead_Time_Min; âm -> slack âm cho incident (hpl_engine.py:1534). ĐÃ XÁC MINH. |
| `revenue` | Doanh thu cước (VND) | `_norm_static_order hpl_engine.py:472 (_f)` | Freight_Revenue_VND; <=0 -> hard error (validate_orders:645). ĐÃ XÁC MINH. |
| `extra_stop_fee` | Phụ phí điểm dừng thêm (VND) | `_norm_static_order hpl_engine.py:473 (_f)` | Extra_Stop_Fee_VND; cộng vào revenue_total tuyến (engine_ext.py:171,173). ĐÃ XÁC MINH. |
| `waiting_fee` | Phí chờ thu được (VND) | `_norm_static_order hpl_engine.py:474 (_f)` | Waiting_Fee_Chargeable_VND; cộng vào revenue_total (engine_ext.py:172). ĐÃ XÁC MINH. |
| `late_penalty_30m` | Phạt trễ mỗi 30 phút (VND) | `_norm_static_order hpl_engine.py:475 (_f)` | Late_Penalty_VND_per_30m. ĐÃ XÁC MINH. |
| `priority` | Ưu tiên khách hàng/SLA | `_norm_static_order hpl_engine.py:476` | Customer_Priority. ĐÃ XÁC MINH. |
| `contract_route` | Tuyến hợp đồng | `_norm_static_order hpl_engine.py:477` | Contract_Route_ID. ĐÃ XÁC MINH. |
| `suggested_vehicle` | Loại xe đề xuất | `_norm_static_order hpl_engine.py:478` | Suggested_Vehicle_Type. ĐÃ XÁC MINH. |
| `suggested_action` | Hành động đề xuất (file) | `_norm_static_order hpl_engine.py:479` | Suggested_Action gốc trong sheet. ĐÃ XÁC MINH. |
| `validation_status` | Trạng thái kiểm định (gốc file) | `_norm_static_order hpl_engine.py:480` | Validation_Status gốc sheet (KHÁC computed_status do engine tính). ĐÃ XÁC MINH. |
| `risk_flag` | Cờ rủi ro | `_norm_static_order hpl_engine.py:481` | Risk_Flag; dùng trong _incident_hint (hpl_engine.py:683). ĐÃ XÁC MINH. |
| `notes` | Ghi chú | `_norm_static_order hpl_engine.py:482` | Notes. ĐÃ XÁC MINH. |

#### 2) Kiểm định & cờ (kiem_dinh) — 7 trường

| field_key | Nhãn | Nguồn (file:line) | Ghi chú |
|---|---|---|---|
| `issues` | Danh sách vấn đề (hard+soft) | `validate_orders hpl_engine.py:661,670` | hard+issues gộp; app.py:495 đẩy ra UI. ĐÃ XÁC MINH. |
| `hard_errors` | Lỗi cứng dữ liệu | `validate_orders hpl_engine.py:637-648,671` | Thiếu tọa độ/loại xe/doanh thu/khối lượng, giao trước giờ lấy. ĐÃ XÁC MINH (lưu ý: là 'hard' trong code, key dict='hard_errors'). |
| `soft_warnings` | Cảnh báo mềm cần can thiệp | `validate_orders hpl_engine.py:651-659,672` | min>max xe, vi phạm cấm tải, nội đô >=5T, tuyến >100km. ĐÃ XÁC MINH (key='soft_warnings', biến nội bộ='issues'). |
| `valid` | Hợp lệ (không lỗi cứng) | `validate_orders hpl_engine.py:673` | len(hard)==0. ĐÃ XÁC MINH. |
| `computed_status` | Trạng thái kiểm định tính toán | `validate_orders hpl_engine.py:662-667,674` | OK/REVIEW/ERROR; app.py:494 'raw_status'. ĐÃ XÁC MINH. |
| `incident_hint` | Gợi ý loại sự cố động | `_incident_hint hpl_engine.py:681-690 (gán :676)` | Traffic Congestion & Police Check / Vehicle Mismatch / Empty-run Risk / General Exception. ĐÃ XÁC MINH. |
| `status_lifecycle` | Trạng thái vòng đời/nghiệp vụ | `ext.lifecycle_status engine_ext.py:119-126; app.py:494 (key 'status')` | SỬA: lifecycle_status chỉ ánh xạ computed_status -> 'Không thể xử lý'/'Cần rà soát'/'Hợp lệ'. KHÔNG có trạng thái 'đã gán/đang chạy/hoàn tất' ở cấp đơn — trạng thái đó nằm ở TUYẾN (route.status). Spec gốc mô tả sai phạm vi, đã sửa. |

#### 3) Gán xe / tuyến (gan_tuyen) — 22 trường

| field_key | Nhãn | Nguồn (file:line) | Ghi chú |
|---|---|---|---|
| `vehicle_id` | Mã xe gán | `_build_route hpl_engine.py:1077; _route_out app.py:562` | Tra route có oid trong route['orders']. ĐÃ XÁC MINH. |
| `plate` | Biển số xe | `_build_route hpl_engine.py:1077; _route_out app.py:562` | veh.plate. ĐÃ XÁC MINH. |
| `vehicle_type` | Loại xe thực gán | `_build_route hpl_engine.py:1078; _route_out app.py:563` | So với min/max_vehicle. ĐÃ XÁC MINH. |
| `driver` | Tài xế | `_build_route hpl_engine.py:1078; _route_out app.py:563` | veh.driver_name or driver. ĐÃ XÁC MINH. |
| `corridor` | Hành lang tuyến xe | `_build_route hpl_engine.py:1079; _route_out app.py:564` | veh.corridor. ĐÃ XÁC MINH. |
| `orders` | Danh sách mã đơn trên tuyến | `_build_route hpl_engine.py:1081; _route_out app.py:565` | list order_id. ĐÃ XÁC MINH. |
| `order_objs` | Object đơn đầy đủ trên tuyến | `_build_route hpl_engine.py:1082` | Bản đơn đã gán; dùng nội bộ + route_pnl_detailed (engine_ext.py:167). ĐÃ XÁC MINH. |
| `n_orders` | Số đơn trên tuyến | `_build_route hpl_engine.py:1083; _route_out app.py:564` | ĐÃ XÁC MINH. |
| `stops` | Chuỗi điểm dừng | `_build_route hpl_engine.py:1084; _route_out app.py:578` | mỗi stop: type(depot/pickup/delivery), name, lat, lon, order_id, tw, eta (eta gắn ở route_timeline engine_ext.py:837,856). ĐÃ XÁC MINH. |
| `distance_km` | Tổng km tuyến | `_build_route hpl_engine.py:1085; _route_out app.py:565` | ĐÃ XÁC MINH. |
| `productive_km` | Km có tải | `_build_route hpl_engine.py:1086` | distance - empty. ĐÃ XÁC MINH (lưu ý: _route_out KHÔNG xuất ra; phải đọc trực tiếp từ route). |
| `empty_km` | Km chạy rỗng | `_build_route hpl_engine.py:1087; _route_out app.py:566; get_route_context gemini_ai.py:312` | ĐÃ XÁC MINH. |
| `total_weight` | Tổng khối lượng tuyến (kg) | `_build_route hpl_engine.py:1088; _route_out app.py:567` | ĐÃ XÁC MINH. |
| `total_volume` | Tổng thể tích tuyến (m3) | `_build_route hpl_engine.py:1089; _route_out app.py:567` | ĐÃ XÁC MINH. |
| `total_revenue` | Tổng cước đơn trên tuyến (chưa phụ phí) | `_build_route hpl_engine.py:1090` | sum revenue đơn; KHÁC pnl.revenue_total (có phụ phí). _route_out KHÔNG xuất; đọc trực tiếp route. ĐÃ XÁC MINH. |
| `fill_weight_pct` | Fill-rate theo tải (%) | `_build_route hpl_engine.py:1091; _route_out app.py:568; gemini_ai.py:313` | % so max_weight_kg xe. ĐÃ XÁC MINH. |
| `fill_volume_pct` | Fill-rate theo thể tích (%) | `_build_route hpl_engine.py:1092; _route_out app.py:568` | ĐÃ XÁC MINH. |
| `status` | Trạng thái tuyến | `_run_optimize app.py:534 (setdefault 'assigned'); _route_out app.py:573` | assigned/locked... ĐÃ XÁC MINH. |
| `locked` | Tuyến đã khóa/đóng băng | `_frozen_route app.py:92; _route_out app.py:574` | BỔ SUNG: trong route dict KHÔNG có key 'locked'; phải gọi app._frozen_route(r) để suy ra. ĐÃ XÁC MINH/SỬA. |
| `has_backhaul` | Tuyến có ghép chiều về | `_route_out app.py:572` | bool route.get('has_backhaul'). ĐÃ XÁC MINH. |
| `pnl` | Khối P&L gắn vào tuyến | `_run_optimize app.py:541-542 (từ financials_detailed->per_route route_pnl_detailed)` | BỔ SUNG: route['pnl'] là nguồn của toàn bộ entity pnl_tuyen; nếu chưa chạy tối ưu thì rỗng. ĐÃ XÁC MINH. |
| `timeline` | Timeline ETA gắn vào tuyến | `_run_optimize app.py:547 (route_timeline); _route_out app.py:577` | BỔ SUNG: route['timeline'] CHỈ dựng cho tuyến MỚI; tuyến đóng băng giữ timeline cũ, fallback đọc stop['eta']. ĐÃ XÁC MINH. |

#### 4) Thời gian & ETA (thoi_gian_eta) — 7 trường

| field_key | Nhãn | Nguồn (file:line) | Ghi chú |
|---|---|---|---|
| `vi_tri_pickup_index` | Vị trí stop điểm lấy của đơn trong tuyến | `route['stops'] _build_route hpl_engine.py:1084 (lọc type=='pickup' & order_id==oid)` | BỔ SUNG: tính bằng cách duyệt stops; không phải field sẵn. Hợp lệ vì stop có order_id. |
| `vi_tri_delivery_index` | Vị trí stop điểm trả của đơn trong tuyến | `route['stops'] _build_route hpl_engine.py:1084 (lọc type=='delivery' & order_id==oid)` | BỔ SUNG: tính từ stops. |
| `timeline` | Timeline ETA cả tuyến | `route_timeline engine_ext.py:821-870; _run_optimize app.py:547; _route_out app.py:577` | list bước {time,type,name,action,order_id}. ĐÃ XÁC MINH. |
| `stop.eta` | ETA từng điểm (lấy/trả) | `route_timeline engine_ext.py:837,856 (gắn vào stop)` | min_to_hhmm tại mỗi stop -> ETA điểm lấy/điểm trả của đơn. ĐÃ XÁC MINH. |
| `step.action` | Hành động từng bước | `route_timeline engine_ext.py:849,852,855,865,868` | lấy hàng/giao hàng/chờ khung giờ/backhaul/về depot. ĐÃ XÁC MINH. |
| `step.order_id` | Đơn của từng bước ETA | `route_timeline engine_ext.py:858 (s.get('order_id'))` | lọc step theo order_id để lấy ETA đúng đơn. ĐÃ XÁC MINH. |
| `step.time` | Giờ dự kiến từng bước | `route_timeline engine_ext.py:835,857,863,867` | BỔ SUNG: chuỗi hhmm; eta_pickup/eta_delivery lấy từ step.time của bước pickup/delivery có order_id==oid. |

#### 5) Đơn chưa gán (chua_gan) — 6 trường

| field_key | Nhãn | Nguồn (file:line) | Ghi chú |
|---|---|---|---|
| `reason` | Lý do chưa gán | `unassigned_reason engine_ext.py:873-895; _unassigned_rows app.py:711` | Thiếu tọa độ/không đủ xe/không xe phù hợp/không đủ tải/cấm tải/tuyến dài/không đủ thời gian. ĐÃ XÁC MINH. |
| `suggestion` | Gợi ý xử lý | `unassigned_reason engine_ext.py:876-895; _unassigned_rows app.py:719` | Cặp với reason. ĐÃ XÁC MINH. |
| `handle_score` | Điểm dễ xử lý (0-70) | `rank_unassigned_orders ai_matcher.py:421-430` | SỬA: spec gốc ghi 'do_kho_rank/do_kho' — KHÔNG TỒN TẠI. Field thật là 'handle_score' (vi phạm cứng=30/55/60, dễ=70). Càng cao càng dễ. |
| `hard_block` | Bị chặn cứng (tải/loại xe/cấm tải/tọa độ) | `rank_unassigned_orders ai_matcher.py:420,430` | BỔ SUNG: bool, đi kèm handle_score; phân biệt đơn vi phạm cứng vs chỉ thiếu điều phối. |
| `tw` | Khung giờ trả hiển thị | `_unassigned_rows app.py:717` | min_to_hhmm(drop_tw_start)-min_to_hhmm(drop_tw_end). ĐÃ XÁC MINH (chỉ ở row UI; trong get_order_detail tự dựng từ don_goc). |
| `incident_hint_unassigned` | Gợi ý sự cố cho đơn chưa gán | `_unassigned_rows app.py:719 (o['incident_hint'])` | Cùng giá trị với kiem_dinh.incident_hint. ĐÃ XÁC MINH. |

#### 6) Ghép chiều về (backhaul) — 17 trường

| field_key | Nhãn | Nguồn (file:line) | Ghi chú |
|---|---|---|---|
| `to_pickup_km` | Km từ điểm xe rảnh tới điểm lấy chiều về | `score_backhaul_match ai_matcher.py:270 (calculate_empty_km_reduction)` | >r_pickup -> violation+REJECT. ĐÃ XÁC MINH. |
| `to_pickup_min` | Phút điều xe tới điểm lấy chiều về | `score_backhaul_match ai_matcher.py:271` | ĐÃ XÁC MINH. |
| `return_km` | Km chiều về sau ghép | `score_backhaul_match ai_matcher.py:272 (fin['return_km'])` | ĐÃ XÁC MINH. |
| `fill_before` | Fill chiều về trước ghép (%) | `score_backhaul_match ai_matcher.py:256,273` | =0 (xe chạy rỗng chiều về). ĐÃ XÁC MINH. |
| `fill_after` | Fill chiều về sau ghép (%) | `score_backhaul_match ai_matcher.py:257,273` | ĐÃ XÁC MINH. |
| `revenue_add` | Doanh thu bổ sung | `score_backhaul_match ai_matcher.py:274 (calculate_incremental_profit)` | ĐÃ XÁC MINH. |
| `cost_add` | Chi phí bổ sung | `score_backhaul_match ai_matcher.py:274` | ĐÃ XÁC MINH. |
| `profit_add` | Lợi nhuận bổ sung | `score_backhaul_match ai_matcher.py:275; cộng total_gain ai_matcher.py:333` | <=0 -> violation+REJECT. ĐÃ XÁC MINH. |
| `empty_km_reduced` | Km rỗng giảm được | `score_backhaul_match ai_matcher.py:275` | ĐÃ XÁC MINH (cộng dồn empty_km_avoided ai_matcher.py:334,347). |
| `score` | Điểm ghép backhaul 0-100 | `score_backhaul_match ai_matcher.py:293,301` | 30%dist+25%profit+15%fill+15%empty+8%type+7%time. ĐÃ XÁC MINH. |
| `decision` | Quyết định ghép | `score_backhaul_match ai_matcher.py:282,295,301` | RECOMMEND(score>=58)/CONSIDER/REJECT. ĐÃ XÁC MINH. |
| `violations` | Vi phạm ràng buộc ghép | `score_backhaul_match ai_matcher.py:244,281,301` | tải/dung tích/loại xe/cấm tải/bán kính/lợi nhuận. ĐÃ XÁC MINH. |
| `has_violation` | Có vi phạm (bool) | `score_backhaul_match ai_matcher.py:281,301` | BỔ SUNG: dùng để biết REJECT; recommend_backhaul_matches bỏ qua match has_violation (ai_matcher.py:327). |
| `reason` | Lý do ghép/từ chối | `score_backhaul_match ai_matcher.py:283,302` | ĐÃ XÁC MINH. |
| `n_matched` | Số xe ghép được (toàn cục) | `recommend_backhaul_matches ai_matcher.py:346; get_backhaul_context gemini_ai.py:337` | ĐÃ XÁC MINH. |
| `total_gain` | Tổng lợi nhuận bổ sung (toàn cục) | `recommend_backhaul_matches ai_matcher.py:347` | ĐÃ XÁC MINH. |
| `result_wrapper` | Bọc kết quả 1 tuyến (chứa match) | `recommend_backhaul_matches ai_matcher.py:337-343` | BỔ SUNG QUAN TRỌNG: results[] = {vehicle_id, vehicle_type, driver, corridor, end_lat/lon, depot_lat/lon, match:{...}}. order_id NẰM TRONG result['match']['order_id'], không phải cấp ngoài. Khi tra đơn phải lọc theo result['match']['order_id']==oid. |

#### 7) Sự cố liên quan (su_co) — 15 trường

| field_key | Nhãn | Nguồn (file:line) | Ghi chú |
|---|---|---|---|
| `case_id` | Mã sự cố | `app.py:946,951` | SC-HHMMSS-seq. ĐÃ XÁC MINH (build_ai_context gemini_ai.py:390 đọc key 'ma'). |
| `event_type` | Loại sự cố | `app.py:951,932; incident_from_static_order hpl_engine.py:1541` | từ incident_hint. ĐÃ XÁC MINH. |
| `priority` | Mức ưu tiên sự cố | `app.py:952` | 'Cao' nếu computed_status ERROR, ngược lại 'Trung bình'. ĐÃ XÁC MINH. |
| `vehicle` | Xe liên quan sự cố | `app.py:956; gemini_ai.py:391` | xe trên tuyến chứa đơn, hoặc xe đề xuất (rec), hoặc '—'. ĐÃ XÁC MINH. |
| `route_id` | Tuyến liên quan sự cố | `app.py:958` | =vehicle_id tuyến chứa đơn, hoặc '—'. ĐÃ XÁC MINH. |
| `status` | Trạng thái xử lý sự cố | `app.py:959 (khởi tạo 'Đang xử lý'); gemini_ai.py:391` | Đang xử lý/Hoàn tất (cập nhật qua endpoint quyết định). ĐÃ XÁC MINH. |
| `decision` | Phương án đã chọn | `app.py:959 (khởi tạo None); gemini_ai.py:392` | SỬA: lúc tạo decision=None; được điền sau khi dispatcher chọn. ĐÃ XÁC MINH. |
| `options` | Các phương án xử lý | `ext.incident_options engine_ext.py:461; app.py:935,960` | top-level inc_record['options']=opt['options']. ĐÃ XÁC MINH. |
| `candidates` | Xe thay thế ứng viên | `incident_from_static_order hpl_engine.py:1515-1532,1546; NẰM TRONG inc_record['incident']['candidates'] app.py:960` | SỬA: candidates KHÔNG ở top-level inc_record mà trong inc_record['incident']. Mỗi candidate có: vehicle,dist_km,eta_min,capacity_ok,within_radius,engine_score,engine_feasible,recovery_feasible (hpl_engine.py:1518-1527). |
| `recommended_vehicle` | Xe thay thế khuyến nghị | `incident_from_static_order hpl_engine.py:1531,1546 (key 'recommended_vehicle')` | SỬA: spec gốc gọi nhầm; field là 'recommended_vehicle' (candidate khả thi đầu tiên), nằm trong inc_record['incident']. |
| `recommended_action` | Hành động khuyến nghị (nhãn) | `incident_from_static_order hpl_engine.py:1535,1545 (slack_action)` | nhãn ngắn theo slack; mô tả đầy đủ ở key 'action_desc' (hpl_engine.py:1545). Nằm trong inc_record['incident']. ĐÃ XÁC MINH/BỔ SUNG action_desc. |
| `action_desc` | Mô tả hành động khuyến nghị | `incident_from_static_order hpl_engine.py:1535,1545 (slack_action)` | BỔ SUNG: chuỗi mô tả đầy đủ đi kèm recommended_action. |
| `slack_min` | Slack thời gian (phút) | `incident_from_static_order hpl_engine.py:1534,1545` | từ -lead_time (âm) hoặc -45. Nằm trong inc_record['incident']. ĐÃ XÁC MINH. |
| `soft_skills` | Gợi ý kỹ năng mềm xử lý | `ext.incident_options app.py:960 (opt['soft_skills'])` | BỔ SUNG: top-level inc_record['soft_skills'] — kịch bản giao tiếp khách/tài xế. |
| `analysis` | Phân tích AI sự cố | `ai.incident_analysis app.py:940,961` | BỔ SUNG: inc_record['analysis'] + analysis_source — diễn giải phương án. |

#### 8) Tài chính P&L tuyến chở đơn (pnl_tuyen) — 14 trường

| field_key | Nhãn | Nguồn (file:line) | Ghi chú |
|---|---|---|---|
| `revenue_freight` | Doanh thu cước tuyến | `route_pnl_detailed engine_ext.py:170,228` | sum revenue đơn. ĐÃ XÁC MINH. |
| `revenue_total` | Tổng doanh thu (gồm phụ phí) | `route_pnl_detailed engine_ext.py:173,229` | revenue+extra_stop_fee+waiting_fee; _route_out app.py:569 'revenue'. ĐÃ XÁC MINH. |
| `fuel` | Chi phí nhiên liệu | `route_pnl_detailed engine_ext.py:182,230` | productive_km*lpk*giá dầu real-time (fuel.get_diesel_price). ĐÃ XÁC MINH. |
| `toll` | Phí cầu đường | `route_pnl_detailed engine_ext.py:189,231` | _intercity_km*phí BOT. ĐÃ XÁC MINH. |
| `driver_cost` | Chi phí tài xế | `route_pnl_detailed engine_ext.py:196,235` | lương+phụ cấp+tăng ca. ĐÃ XÁC MINH (chi tiết: driver_base,driver_allowance,overtime cũng có). |
| `vehicle_cost` | Chi phí xe | `route_pnl_detailed engine_ext.py:202,239` | khấu hao+bảo dưỡng+bảo hiểm. ĐÃ XÁC MINH (depreciation,maintenance,insurance riêng cũng có). |
| `empty_cost` | Chi phí chạy rỗng | `route_pnl_detailed engine_ext.py:185-186,241` | phần empty_km vượt 30km; =0 nếu has_backhaul. ĐÃ XÁC MINH. |
| `handling` | Chi phí bốc xếp | `route_pnl_detailed engine_ext.py:205,240` | n_orders*chi_phi_boc_xep_don. ĐÃ XÁC MINH. |
| `overhead` | Overhead quản lý | `route_pnl_detailed engine_ext.py:208,242` | revenue_total*ty_le_quan_ly. ĐÃ XÁC MINH. |
| `total_cost` | Tổng chi phí tuyến | `route_pnl_detailed engine_ext.py:210,243; _route_out app.py:569 'cost'` | ĐÃ XÁC MINH. |
| `profit` | Lợi nhuận tuyến | `route_pnl_detailed engine_ext.py:212,244; _route_out app.py:570; gemini_ai.py:314` | revenue_total - total_cost. ĐÃ XÁC MINH. |
| `margin` | Biên lợi nhuận tuyến (%) | `route_pnl_detailed engine_ext.py:213,245; _route_out app.py:570; gemini_ai.py:314` | ĐÃ XÁC MINH. |
| `risk_late` | Rủi ro trễ giờ | `route_pnl_detailed engine_ext.py:217,246; _route_out app.py:571; gemini_ai.py:316` | drive_min vượt nguong_gio_lam hoặc overtime>30'. ĐÃ XÁC MINH. |
| `overtime` | Chi phí tăng ca | `route_pnl_detailed engine_ext.py:195,234` | BỔ SUNG: dùng giải thích risk_late & chi phí tài xế. |

### 3.2 Danh mục câu hỏi vàng (dispatcher hỏi về 1 đơn)

| # | Câu hỏi | Intent | Trường cần | Nguồn | Từ khóa nhận diện |
|---|---|---|---|---|---|
| 1 | Đơn này chở gì, khối lượng, thể tích, bao nhiêu pallet, có cần xe lạnh không? | `noi_dung_hang` | `product`, `weight_kg`, `volume_m3`, `pallet`, `need_refrigeration` | _norm_static_order hpl_engine.py:438,454-456,459 | chở gì, sản phẩm, khối lượng, kg, thể tích, m3, pallet, hàng gì, xe lạnh |
| 2 | Đơn lấy ở đâu, giao ở đâu (tên/tỉnh/huyện/tọa độ)? | `diem_lay_tra` | `pickup_name`, `pickup_province`, `pickup_district`, `pickup_lat`, `pickup_lon`, `delivery_name`, `delivery_province`, `delivery_district`, `delivery_lat`, `delivery_lon` | _norm_static_order hpl_engine.py:440-450 | lấy ở đâu, giao ở đâu, điểm lấy, điểm trả, tỉnh, huyện, tọa độ, địa chỉ |
| 3 | Khung giờ lấy và khung giờ giao của đơn, độ linh hoạt và lead time? | `khung_gio` | `pickup_tw_start`, `pickup_tw_end`, `drop_tw_start`, `drop_tw_end`, `tw_flex_min`, `lead_time` | _norm_static_order hpl_engine.py:464-468,471; eng.min_to_hhmm | khung giờ, giờ lấy, giờ giao, time window, mấy giờ, tw, lead time |
| 4 | Doanh thu, phụ phí, phí chờ và mức phạt trễ của đơn này bao nhiêu? | `doanh_thu_phi` | `revenue`, `extra_stop_fee`, `waiting_fee`, `late_penalty_30m` | _norm_static_order hpl_engine.py:472-475 | doanh thu, cước, giá, phụ phí, phí chờ, phạt trễ, tiền |
| 5 | Đơn ưu tiên mức nào, thuộc hợp đồng/nhóm khách/kênh nào, có phải xe chuyên dụng? | `uu_tien_sla` | `priority`, `customer_group`, `contract_route`, `channel`, `dedicated` | _norm_static_order hpl_engine.py:436-437,461,476-477 | ưu tiên, sla, priority, hợp đồng, nhóm khách, kênh, chuyên dụng, dedicated |
| 6 | Đơn yêu cầu loại xe nào, tối đa loại nào, đề xuất xe gì, có cho gom đơn? | `yeu_cau_xe` | `min_vehicle`, `max_vehicle`, `need_refrigeration`, `suggested_vehicle`, `can_consolidate` | _norm_static_order hpl_engine.py:457-460,478 | loại xe, xe tối thiểu, xe tối đa, xe lạnh, cần lạnh, min vehicle, gom đơn |
| 7 | Đơn này có bị vướng giờ cấm tải nội đô không, ghi chú tiếp cận là gì? | `cam_tai` | `inner_city`, `min_vehicle`, `soft_warnings`, `access_note` | road_ban_conflict hpl_engine.py:617-628; validate_orders hpl_engine.py:653-656; _norm_static_order:462-463 | cấm tải, nội đô, giờ cấm, đường nhỏ, inner city, tiếp cận |
| 8 | Trạng thái kiểm định của đơn (OK/REVIEW/ERROR) và vì sao? | `trang_thai_kiem_dinh` | `computed_status`, `issues`, `hard_errors`, `soft_warnings`, `valid`, `status_lifecycle` | validate_orders hpl_engine.py:661-674; lifecycle_status engine_ext.py:119; app.py:494-495 | kiểm định, trạng thái, lỗi, cảnh báo, review, error, vì sao, tại sao đỏ |
| 9 | Đơn đã được gán cho xe nào, tài xế nào, hành lang nào? | `gan_xe` | `vehicle_id`, `plate`, `vehicle_type`, `driver`, `corridor`, `orders` | _build_route hpl_engine.py:1077-1081 (tra route có oid trong route['orders']) | xe nào, gán xe, tài xế, tuyến nào, ai chở, biển số |
| 10 | Đơn nằm ở vị trí thứ mấy trong tuyến, các stop trước/sau là gì? | `vi_tri_trong_tuyen` | `stops`, `n_orders`, `vi_tri_pickup_index`, `vi_tri_delivery_index` | _build_route hpl_engine.py:1084 (duyệt stops lọc type & order_id==oid) | vị trí, thứ tự, stop, điểm dừng, trước sau, sequence |
| 11 | ETA dự kiến tới điểm lấy và điểm trả của đơn là mấy giờ? | `eta_diem` | `timeline`, `stop.eta`, `step.order_id`, `step.time`, `pickup_service`, `drop_service` | route_timeline engine_ext.py:837,856-858; _run_optimize app.py:547 (fallback stop['eta'] cho tuyến đóng băng) | eta, mấy giờ tới, dự kiến đến, giờ lấy thực tế, giờ giao thực tế, timeline |
| 12 | Tuyến chở đơn này đầy tải bao nhiêu phần trăm (fill-rate), tổng tải/thể tích? | `fill_rate` | `fill_weight_pct`, `fill_volume_pct`, `total_weight`, `total_volume` | _build_route hpl_engine.py:1088-1092; _route_out app.py:567-568; gemini_ai.py:313 | fill, đầy tải, tải trọng, phần trăm tải, fill-rate, tận dụng xe |
| 13 | Vì sao đơn này chưa được gán xe, độ khó xử lý và nên xử lý ra sao? | `chua_gan` | `reason`, `suggestion`, `handle_score`, `hard_block`, `incident_hint_unassigned` | unassigned_reason engine_ext.py:873-895; rank_unassigned_orders ai_matcher.py:412-433 | chưa gán, không gán, tại sao chưa có xe, sao bị loại, xử lý đơn rớt, độ khó |
| 14 | Đơn này (đơn bổ sung) có thể ghép chiều về (backhaul) cho xe nào không, lợi bao nhiêu? | `backhaul` | `score`, `decision`, `to_pickup_km`, `profit_add`, `empty_km_reduced`, `fill_after`, `reason`, `violations`, `has_violation` | score_backhaul_match ai_matcher.py:232-303; recommend_backhaul_matches ai_matcher.py:309-350 (lọc result['match']['order_id']==oid) | ghép, chiều về, backhaul, quay đầu, tận dụng chiều rỗng, ghép đơn |
| 15 | Đơn này có đang dính sự cố nào không, ứng viên xe thay thế và phương án xử lý? | `su_co` | `case_id`, `event_type`, `status`, `priority`, `vehicle`, `route_id`, `decision`, `options`, `candidates`, `recommended_vehicle`, `recommended_action`, `slack_min` | app.py:950-963 (top-level case); candidates/recommended_vehicle/recommended_action/slack_min trong inc_record['incident'] (incident_from_static_order hpl_engine.py:1537-1550) | sự cố, incident, gặp vấn đề, xe thay thế, phương án, đang xử lý |
| 16 | Đơn này đóng góp bao nhiêu vào lợi nhuận tuyến (doanh thu/chi phí/biên)? | `dong_gop_pnl` | `revenue`, `extra_stop_fee`, `waiting_fee`, `revenue_total`, `total_cost`, `profit`, `margin`, `fill_weight_pct` | route_pnl_detailed engine_ext.py:165-249; route['pnl'] app.py:541-542; _route_out app.py:569-570 | lợi nhuận, biên, p&l, đóng góp, có lãi không, margin, doanh thu chi phí |
| 17 | Quãng đường đơn này bao xa, thuộc hành lang/corridor nào, tuyến chạy rỗng nhiều không? | `khoang_cach_corridor` | `direct_km`, `corridor`, `route_axis`, `empty_km`, `productive_km` | _norm_static_order hpl_engine.py:451-453; _build_route hpl_engine.py:1086-1087 | bao xa, km, khoảng cách, corridor, hành lang, chạy rỗng, quãng đường |
| 18 | Loại xe tối thiểu của đơn có vượt loại tối đa cho phép không (cần split/chuyển tải)? | `split_mismatch` | `min_vehicle`, `max_vehicle`, `soft_warnings`, `incident_hint` | validate_orders hpl_engine.py:651-652; _incident_hint hpl_engine.py:686 | split, tách đơn, chuyển tải, xe vượt, mismatch, không vừa xe |
| 19 | Đơn có rủi ro trễ giờ giao không, phạt trễ ra sao? | `rui_ro_tre` | `risk_late`, `overtime`, `lead_time`, `drop_tw_end`, `late_penalty_30m`, `timeline` | route_pnl_detailed engine_ext.py:217,246; route_timeline engine_ext.py:844-846 | trễ, muộn, rủi ro trễ, kịp giờ, trễ giờ giao, risk late |
| 20 | Tóm tắt toàn bộ một đơn (mọi trường) cho điều phối viên. | `tong_hop_don` | `order_id`, `customer`, `product`, `weight_kg`, `pickup_name`, `delivery_name`, `computed_status`, `vehicle_id`, `margin`, `reason`, `timeline` | get_order_detail (gom tất cả nguồn trên) | chi tiết đơn, tóm tắt đơn, thông tin đơn, đơn này thế nào, full đơn, xem đơn |
| 21 | Trạng thái nghiệp vụ/vòng đời của đơn là gì (Hợp lệ/Cần rà soát/Không thể xử lý)? | `trang_thai_nghiep_vu` | `status_lifecycle`, `computed_status` | lifecycle_status engine_ext.py:119-126; app.py:494 | trạng thái, hợp lệ, cần rà soát, không thể xử lý, vòng đời, nghiệp vụ |
| 22 | File gốc đánh trạng thái kiểm định và gợi ý hành động cho đơn này là gì (so với hệ thống tính)? | `trang_thai_file_goc` | `validation_status`, `suggested_action`, `risk_flag`, `notes` | _norm_static_order hpl_engine.py:479-482 | file gốc, validation status, suggested action, risk flag, ghi chú, sheet ghi gì |
| 23 | Đơn này lập cho ngày nào (Planning_Date), thuộc kịch bản nào? | `ngay_kich_ban` | `planning_date`, `scenario` | _norm_static_order hpl_engine.py:433-434 | ngày, planning date, kịch bản, scenario, ngày kế hoạch |
| 24 | Nếu đơn dính sự cố, cơ cấu chi phí/phương án so sánh và gợi ý kỹ năng mềm là gì? | `phuong_an_su_co` | `options`, `soft_skills`, `analysis`, `candidates`, `recommended_action`, `action_desc` | ext.incident_options engine_ext.py:461; ai.incident_analysis app.py:940; inc_record['options'/'soft_skills'/'analysis'] app.py:960-961 | phương án, so sánh, kỹ năng mềm, soft skill, phân tích sự cố, chi phí phương án |

### 3.3 Mẫu câu trả lời theo câu hỏi (answer_shape)

- **1. Đơn này chở gì, khối lượng, thể tích, bao nhiêu pallet, có cần xe lạnh không?** → Đơn {order_id} ({customer}): {product}, {weight_kg}kg / {volume_m3}m3 / {pallet} pallet{; cần xe lạnh nếu need_refrigeration}.
- **2. Đơn lấy ở đâu, giao ở đâu (tên/tỉnh/huyện/tọa độ)?** → Lấy tại {pickup_name} ({pickup_district},{pickup_province}) [{pickup_lat},{pickup_lon}] -> giao {delivery_name} ({delivery_district},{delivery_province}) [{delivery_lat},{delivery_lon}].
- **3. Khung giờ lấy và khung giờ giao của đơn, độ linh hoạt và lead time?** → Khung giờ lấy {hhmm(pickup_tw_start)}-{hhmm(pickup_tw_end)}, giao {hhmm(drop_tw_start)}-{hhmm(drop_tw_end)}, linh hoạt +-{tw_flex_min}', lead time {lead_time}'.
- **4. Doanh thu, phụ phí, phí chờ và mức phạt trễ của đơn này bao nhiêu?** → Cước {revenue}d, phụ phí điểm dừng {extra_stop_fee}d, phí chờ {waiting_fee}d, phạt trễ {late_penalty_30m}d/30 phút.
- **5. Đơn ưu tiên mức nào, thuộc hợp đồng/nhóm khách/kênh nào, có phải xe chuyên dụng?** → Ưu tiên {priority}, nhóm KH {customer_group}, kênh {channel}, hợp đồng {contract_route}{; xe chuyên dụng nếu dedicated}.
- **6. Đơn yêu cầu loại xe nào, tối đa loại nào, đề xuất xe gì, có cho gom đơn?** → Yêu cầu xe tối thiểu {min_vehicle}, tối đa {max_vehicle}{; cần lạnh}, đề xuất {suggested_vehicle}, {cho/không cho} gom đơn.
- **7. Đơn này có bị vướng giờ cấm tải nội đô không, ghi chú tiếp cận là gì?** → {inner_city? Đơn nội đô}; {nếu soft_warnings chứa 'cấm tải': nêu khung cấm & loại xe}; ghi chú: {access_note}.
- **8. Trạng thái kiểm định của đơn (OK/REVIEW/ERROR) và vì sao?** → Trạng thái {computed_status} ({status_lifecycle}). Lỗi cứng: {hard_errors}. Cảnh báo: {soft_warnings}.
- **9. Đơn đã được gán cho xe nào, tài xế nào, hành lang nào?** → Đơn {order_id} thuộc tuyến xe {vehicle_id} ({vehicle_type}, biển {plate}), tài xế {driver}, hành lang {corridor}.
- **10. Đơn nằm ở vị trí thứ mấy trong tuyến, các stop trước/sau là gì?** → Trong tuyến xe {vehicle_id} đơn này là stop lấy #i / trả #j trên {n_orders} đơn; trước là {prev_stop.name}, sau là {next_stop.name}.
- **11. ETA dự kiến tới điểm lấy và điểm trả của đơn là mấy giờ?** → ETA điểm lấy ~{eta pickup}, ETA điểm trả ~{eta delivery} (lọc step/stop theo order_id).
- **12. Tuyến chở đơn này đầy tải bao nhiêu phần trăm (fill-rate), tổng tải/thể tích?** → Tuyến xe {vehicle_id} fill theo tải {fill_weight_pct}%, theo thể tích {fill_volume_pct}% ({total_weight}kg/{total_volume}m3).
- **13. Vì sao đơn này chưa được gán xe, độ khó xử lý và nên xử lý ra sao?** → Đơn chưa gán vì {reason} (độ dễ xử lý {handle_score}/70{, vi phạm cứng nếu hard_block}). Gợi ý: {suggestion}.
- **14. Đơn này (đơn bổ sung) có thể ghép chiều về (backhaul) cho xe nào không, lợi bao nhiêu?** → Ghép vào chiều về xe {vehicle_id} (điểm {score}, {decision}): cách {to_pickup_km}km, +{profit_add}d, giảm {empty_km_reduced}km rỗng, fill {fill_after}%. {reason}
- **15. Đơn này có đang dính sự cố nào không, ứng viên xe thay thế và phương án xử lý?** → Đơn {order_id}: sự cố {case_id} loại {event_type}, trạng thái {status}, xe {vehicle}; đề xuất {recommended_vehicle} / hành động {recommended_action} (slack {slack_min}').
- **16. Đơn này đóng góp bao nhiêu vào lợi nhuận tuyến (doanh thu/chi phí/biên)?** → Đơn góp cước {revenue}d (+phụ phí {extra_stop_fee}+{waiting_fee}) vào tuyến xe {vehicle_id} biên {margin}%, lợi nhuận tuyến {profit}d.
- **17. Quãng đường đơn này bao xa, thuộc hành lang/corridor nào, tuyến chạy rỗng nhiều không?** → Đơn dài {direct_km}km trên hành lang {corridor} (trục {route_axis}); tuyến chở có {empty_km}km rỗng / {productive_km}km có tải.
- **18. Loại xe tối thiểu của đơn có vượt loại tối đa cho phép không (cần split/chuyển tải)?** → {Nếu veh_rank(min)>veh_rank(max): Cần Split/Chuyển tải vì xe tối thiểu {min_vehicle} > tối đa {max_vehicle}}; gợi ý sự cố {incident_hint}.
- **19. Đơn có rủi ro trễ giờ giao không, phạt trễ ra sao?** → Tuyến chở đơn {risk_late? CÓ : KHÔNG} rủi ro trễ (tăng ca {overtime}d); lead time {lead_time}', phạt trễ {late_penalty_30m}d/30'.
- **20. Tóm tắt toàn bộ một đơn (mọi trường) cho điều phối viên.** → Thẻ đơn đầy đủ: nội dung + điểm lấy/trả + khung giờ + tài chính + kiểm định + gán xe/ETA/fill + chưa gán/backhaul + sự cố + P&L.
- **21. Trạng thái nghiệp vụ/vòng đời của đơn là gì (Hợp lệ/Cần rà soát/Không thể xử lý)?** → Đơn {order_id}: {status_lifecycle} (ánh xạ từ computed_status={computed_status}).
- **22. File gốc đánh trạng thái kiểm định và gợi ý hành động cho đơn này là gì (so với hệ thống tính)?** → File ghi Validation_Status={validation_status}, Suggested_Action={suggested_action}, Risk_Flag={risk_flag}; hệ thống tính lại computed_status để đối chiếu.
- **23. Đơn này lập cho ngày nào (Planning_Date), thuộc kịch bản nào?** → Đơn {order_id} thuộc kịch bản {scenario}, ngày kế hoạch {planning_date}.
- **24. Nếu đơn dính sự cố, cơ cấu chi phí/phương án so sánh và gợi ý kỹ năng mềm là gì?** → Các phương án: {options[*].name/cost}; kỹ năng mềm: {soft_skills}; phân tích: {analysis}; khuyến nghị {recommended_action} ({action_desc}).

### 3.4 Spec hàm `get_order_detail` (cấu trúc + pseudo-logic)

HÀM: get_order_detail(store, order_id) -> dict. Đặt trong gemini_ai.py (đã import eng=hpl_engine, ext=engine_ext, matcher=ai_matcher, fuel). Trả {'order_id':..., 'tim_thay':False} nếu không tìm thấy đơn. Chỉ dùng dữ liệu ĐÃ CÓ trong STORE (giữ trong phiên/RAM là ĐỦ); giá dầu (fuel.get_diesel_price) và Gemini google_search ĐÃ real-time nên P&L và nhánh online dùng số mới nhất.

LƯU Ý PHẠM VI TRUY CẬP STORE (đã đối chiếu app.py:64-84): KHÔNG có key 'working_orders'. Đơn gốc nằm trong STORE['working'] (dict keyed theo sid) và build qua helper app._working_orders(sid) / app._validated(sid). get_order_detail nằm ở gemini_ai (không import app trực tiếp để tránh vòng) -> nên TỰ build validated từ STORE: lấy sid=STORE.get('_scenario'); nếu cần đơn đã-kiểm-định, gọi eng.validate_orders(STORE['working'].get(sid) or STORE['static']['scenarios'].get(sid)). Hoặc nhận sẵn 'validated' do app truyền vào. KHÔNG dựa vào STORE.get('working_orders') (không tồn tại).

CẤU TRÚC DICT TRẢ VỀ (các nhóm = thực thể):
{
 'order_id': ..., 'tim_thay': True/False, 'nguon_don': 'working'|'static',
 'don_goc': {... toàn bộ ~52 field _norm_static_order: order_id..notes, kèm chuỗi hiển thị pickup_tw/drop_tw qua eng.min_to_hhmm ...},
 'kiem_dinh': {computed_status, issues, hard_errors, soft_warnings, valid, incident_hint, status_lifecycle},
 'gan_tuyen': None | {vehicle_id, plate, vehicle_type, driver, corridor, n_orders, fill_weight_pct, fill_volume_pct, empty_km, productive_km, distance_km, total_weight, total_volume, has_backhaul, locked, vi_tri:{pickup_index, delivery_index, prev_stop, next_stop}},
 'thoi_gian_eta': None | {eta_pickup, eta_delivery, steps_cua_don:[step trong timeline có order_id==oid]},
 'pnl_tuyen': None | {revenue_total, total_cost, profit, margin, fuel, toll, driver_cost, vehicle_cost, empty_cost, handling, overhead, overtime, risk_late, dong_gop_doanh_thu_don},
 'chua_gan': None | {reason, suggestion, handle_score, hard_block},
 'backhaul': None | {co_the_ghep:bool, vehicle_id, score, decision, to_pickup_km, profit_add, empty_km_reduced, fill_after, reason, violations, has_violation},
 'su_co': None | {case_id, event_type, status, priority, vehicle, route_id, decision, options, soft_skills, analysis, candidates, recommended_vehicle, recommended_action, action_desc, slack_min},
}

PSEUDO-LOGIC GOM (bám STORE keys THẬT):
1) oid=str(order_id). sid=STORE.get('_scenario'). raw = STORE['working'].get(sid) nếu có, else (STORE['static'] và STORE['static']['scenarios'].get(sid)). validated = eng.validate_orders(raw). o = next((x for x in validated if str(x['order_id'])==oid), None). Nếu None -> return {'order_id':order_id,'tim_thay':False}. nguon_don='working' nếu lấy từ STORE['working'] else 'static'.
   -> don_goc = {k: o[k] for k in các key _norm_static_order} + pickup_tw/drop_tw hiển thị.
   -> kiem_dinh: o['computed_status'],o['issues'],o['hard_errors'],o['soft_warnings'],o['valid'],o['incident_hint']; status_lifecycle=ext.lifecycle_status(o).
2) routes=STORE.get('_routes') or []. route=next((r for r in routes if oid in [str(x) for x in (r.get('orders') or [])]), None). Nếu có:
   - gan_tuyen lấy từ route (_build_route hpl_engine.py:1076-1093): vehicle_id,plate,vehicle_type,driver,corridor,n_orders,fill_weight_pct,fill_volume_pct,empty_km,productive_km,distance_km,total_weight,total_volume; has_backhaul=bool(route.get('has_backhaul')); locked=ext-tương-đương app._frozen_route(route) [route dict KHÔNG có sẵn key 'locked', phải suy từ status/has_backhaul theo logic _frozen_route].
   - vi_tri: enumerate(route['stops']) tìm idx stop type=='pickup' & str(stop.get('order_id'))==oid -> pickup_index; tương tự delivery_index; prev_stop/next_stop = name của stop liền kề.
   - thoi_gian_eta: từ route.get('timeline') lọc step['order_id']==oid -> eta_pickup (step type pickup .time), eta_delivery (step type delivery .time); nếu thiếu timeline (tuyến đóng băng) đọc stop['eta'] đã gắn (engine_ext.py:837,856).
   - pnl_tuyen: pnl=route.get('pnl') or {} (gắn app.py:541-542 từ route_pnl_detailed engine_ext.py:165-249). Lấy revenue_total,total_cost,profit,margin,fuel,toll,driver_cost,vehicle_cost,empty_cost,handling,overhead,overtime,risk_late. dong_gop_doanh_thu_don = eng._f(o['revenue'])+eng._f(o['extra_stop_fee'])+eng._f(o['waiting_fee']).
3) Nếu KHÔNG ở route -> tra chưa gán: una=STORE.get('_unassigned') or [] (LIST các dict đơn). hit=next((u for u in una if str(u.get('order_id'))==oid), None). Nếu hit: reason,sug=ext.unassigned_reason(o, STORE['static']['fleet']); ranked=matcher.rank_unassigned_orders(una, STORE['static']['fleet'], routes); ro=next((x for x in ranked['orders'] if str(x['order_id'])==oid), {}); handle_score=ro.get('handle_score'); hard_block=ro.get('hard_block'). gan_tuyen/thoi_gian_eta/pnl_tuyen=None.
4) Backhaul (chỉ khi đơn là đơn-bổ-sung): nếu oid trong [str(n.get('order_id')) for n in STORE.get('new_backhaul_orders') or []]: res=matcher.recommend_backhaul_matches(routes, STORE['new_backhaul_orders'], STORE['static']['fleet'], fuel.get_diesel_price(), STORE.get('_radius') or 30); hit=next((r for r in res['results'] if str(r['match']['order_id'])==oid), None); nếu hit -> m=hit['match']; backhaul={co_the_ghep:True, vehicle_id:hit['vehicle_id'], score:m['score'], decision:m['decision'], to_pickup_km:m['to_pickup_km'], profit_add:m['profit_add'], empty_km_reduced:m['empty_km_reduced'], fill_after:m['fill_after'], reason:m['reason'], violations:m['violations'], has_violation:m['has_violation']}. Đơn chính (không phải đơn bổ sung) -> None.
5) Sự cố: inc=next((i for i in STORE.get('incidents') or [] if str(i.get('order_id'))==oid), None). Nếu có -> su_co lấy TOP-LEVEL: case_id,event_type,status,priority,vehicle,route_id,decision,options,soft_skills,analysis (app.py:951-961); và NESTED inc['incident'] (khi source tĩnh): candidates,recommended_vehicle,recommended_action,action_desc,slack_min (incident_from_static_order hpl_engine.py:1537-1550). Lưu ý inc['incident'] có thể None với sự cố từ Excel động (_incident_from_dynamic_case app.py:994) -> guard None.
6) Trả dict. Tích hợp: build_ai_context (gemini_ai.py:377) thêm key 'don_dang_hoi'=get_order_detail(store, oid) khi router/needs_matcher bắt được order_id; _offline_assistant (gemini_ai.py:539) đọc ctx['don_dang_hoi'] để trả từng câu vàng thay vì chỉ liệt kê mã đơn.

## Ghi chú kiểm chứng
FIELD ĐÃ SỬA (sai tên / không tồn tại trong code):
1. chua_gan.do_kho / do_kho_rank -> KHÔNG TỒN TẠI. rank_unassigned_orders (ai_matcher.py:412-433) trả mỗi đơn với 'handle_score' (điểm dễ xử lý 0-70) và 'hard_block' (bool). Đã thay bằng 2 field thật này.
2. su_co.candidates / recommended_action / slack_min -> KHÔNG ở top-level inc_record. Chúng nằm trong inc_record['incident'] (incident_from_static_order). Top-level chỉ có case_id,order_id,event_type,priority,vehicle,driver,route_id,status,decision,options,soft_skills,analysis (app.py:951-961). Đã đính chính nguồn.
3. su_co.decision: lúc tạo = None (app.py:959), điền sau khi dispatcher chọn — đã ghi rõ.
4. candidate fields: ngoài dist_km,eta_min,capacity_ok,recovery_feasible còn engine_score & engine_feasible & within_radius (hpl_engine.py:1518-1527); xe khuyến nghị là key 'recommended_vehicle' (không phải 'recommended'). Đã sửa.
5. gan_tuyen.locked: route dict KHÔNG có key 'locked'; phải suy bằng app._frozen_route(route). Đã ghi.
6. status_lifecycle (entity kiem_dinh): spec gốc mô tả 'đã gán/đang chạy/hoàn tất' ở cấp ĐƠN là SAI; lifecycle_status (engine_ext.py:119-126) chỉ ánh xạ computed_status -> 'Hợp lệ/Cần rà soát/Không thể xử lý'. Trạng thái vận hành nằm ở route.status (cấp TUYẾN). Đã sửa nhãn & note.
7. PSEUDO-LOGIC: 'STORE.get(\"working_orders\")' và 'oid in una' (una là list dict) là SAI. Đã thay bằng STORE['working'][sid] + so sánh str(order_id), và duyệt list đơn chưa gán bằng next().
8. backhaul result: order_id nằm trong result['match']['order_id'] (ai_matcher.py:337-343), không ở cấp ngoài. Đã ghi rõ cách lọc.

FIELD BỔ SUNG (có thật, dispatcher có thể hỏi, spec gốc thiếu):
- gan_tuyen: total_weight, total_volume, total_revenue, pnl (con trỏ tới route['pnl']), timeline (con trỏ).
- pnl_tuyen: overtime (giải thích risk_late & chi phí tài xế).
- backhaul: has_violation.
- chua_gan: hard_block.
- su_co: soft_skills, analysis, action_desc, recommended_vehicle.
- thoi_gian_eta: step.time, vi_tri_pickup_index/delivery_index.
- don_goc đã đủ 52 field (giữ nguyên), nhấn mạnh các field hay bị bỏ: dedicated, access_note, suggested_action, validation_status, risk_flag, planning_date, customer_group, channel, tw_flex_min, lead_time, late_penalty_30m, can_consolidate — đều đã có question ánh xạ.

CÂU HỎI BỔ SUNG để đạt 100% coverage: Q21 (trạng thái nghiệp vụ lifecycle), Q22 (validation_status/suggested_action/risk_flag/notes gốc file vs computed), Q23 (planning_date + scenario), Q24 (options/soft_skills/analysis/action_desc phương án sự cố). Q03/Q05/Q06/Q07/Q12/Q13/Q15/Q19 đã mở rộng fields_needed để phủ tw_flex/lead_time, dedicated, can_consolidate, access_note, total_weight/volume, handle_score/hard_block, recommended_vehicle, overtime.

KHẲNG ĐỊNH COVERAGE: Sau sửa, MỌI field_key trong inventory đều ĐÃ XÁC MINH tồn tại trong dict mà code thật sinh ra (đúng tên, đúng file:line). Không còn field bịa. Toàn bộ 52 field _norm_static_order + 6 field kiểm định + ~15 field gán tuyến/P&L + timeline + chưa gán + backhaul + sự cố đều được ít nhất 1 câu hỏi vàng (Q01-Q24) tham chiếu -> phủ 100% câu hỏi dispatcher về 1 đơn. KHÔNG bịa field ngoài inventory; giá dầu & google_search của Gemini ĐÃ real-time nên không cần cảnh báo 'số liệu cũ'.


---

## 4. PHỤ LỤC — BẢN TỔNG HỢP & PHÂN XỬ GỐC (A–E, tham chiếu)

## (Bản tổng hợp & phân xử gốc — Đợt 1)

Hội đồng đã gom **86 góp ý đã khử trùng** từ 4 nguồn (S1 báo cáo gốc 67 phát hiện, S2/S3/S4) cộng 5 yêu cầu trực tiếp của chủ sản phẩm, phân xử **11 mâu thuẫn lớn** (9 mâu thuẫn cốt lõi (i)–(ix) + 2 mâu thuẫn về xác nhận thao tác và badge). Thông điệp chính: sản phẩm có nền nhận diện vững và backend đã mạnh hơn người dùng tưởng (giá dầu + Gemini search ĐÃ real-time); khoảng cách tới hạng nhất nằm ở **3 trục đánh bóng lớp trình bày** — (1) tôn trọng triết lý *stateless* của chủ sản phẩm bằng auto-run ngầm thay vì khóa cứng, (2) giảm mật độ bảng/bản đồ qua drawer + fullscreen, (3) hoàn thiện hệ design-token + accessibility cấp WCAG-A. Tất cả thực thi NGAY trên vanilla, giữ nguyên bảng màu HPL.

---

## PHẦN A — BẢN TỔNG HỢP THỐNG NHẤT

### A1. IA, ĐIỀU HƯỚNG & LUỒNG CÔNG VIỆC

| # | Góp ý (đã khử trùng) | Nguồn | Ưu tiên |
|---|---|---|---|
| A1.1 | **Thanh QUY TRÌNH (stepper) bấm-được, KHÔNG khóa** ở đầu vùng nội dung: Nạp dữ liệu → Kiểm định → Lập tuyến → Ghép chiều về → Tính P&L → Xuất báo cáo, mỗi bước hiện trạng thái (Chưa làm / Có lỗi / Sẵn sàng / Hoàn tất), bấm để nhảy module. Đây là lời giải hợp nhất cho "next-best-action / key nhất để tự dùng". | S1, S3, S4, Người dùng | **Nên làm ngay** (xem Mâu thuẫn #1, #5) |
| A1.2 | **Auto-run optimize NGẦM** khi vào M4/M5 mà `STATE.routes` rỗng (gọi `/api/plan` rồi mới tính finance/backhaul), kèm toast "Đang lập tuyến để tính tài chính…". KHÔNG khóa cứng module. | Người dùng, S2, S3, S4, S1 | **Nên làm ngay** (xem Mâu thuẫn #1) |
| A1.3 | **Gộp "Bản đồ điều phối toàn mạng" (view-map) vào bản đồ M3** bằng nút Mở rộng/Toàn màn hình — bỏ 1 mục sidebar trùng ~90%. | S1, S2, S3, S4, Người dùng | **Nên làm ngay** |
| A1.4 | **Chuyển "Ràng buộc vận hành" (glyph R)** khỏi dãy bước đánh số sang nhóm Cấu hình/Cài đặt (icon ⚙, đáy sidebar), giữ `data-view='constraints'`. | S1, S2, S3, S4 | **Nên làm ngay** |
| A1.5 | **Kích hoạt `.step-tag`** (đã có CSS, chưa render) gắn nhãn bước ("Bước 1/6", "Bước 4 · cần Lập tuyến trước") đầu mỗi view — củng cố stepper, chi phí cực thấp. | S2 | **Nên làm ngay** |
| A1.6 | **Gộp M6 (Sự cố) + M7 (Nhật ký)** thành mục "Vận hành trong ngày" với tab nội bộ (Xử lý sự cố / Nhật ký read-only). | S3, S4, S2 | **Nên cân nhắc** |
| A1.7 | **Gộp M3 + bản đồ** thành luồng liền mạch trong view-plan (sắp lại layout, giữ liên kết bấm-dòng→bản đồ). | S3, S4, S1 | **Nên cân nhắc** (xem Mâu thuẫn #5 Bố cục) |
| A1.8 | **Gộp lối nhập backhaul:** bỏ ô nhập 3PL trùng ở M1, chỉ giữ điểm nhập ở M4 (#f-bk4). | S2, S1 | **Nên cân nhắc** (⚠ hồi quy loop drag&drop 1337) |
| A1.9 | **Hợp nhất nguồn chân lý ghép chiều về:** biến route `/api/backhaul` thành alias gọi engine matcher (một nguồn duy nhất). | S1 | **Nên cân nhắc** (cần đọc app.py 1061–1458 + ai_matcher.py trước) |
| A1.10 | **Tái cấu trúc sidebar 9 → ~6-7 mục:** GIỮ đánh số bước + gộp các mục trùng (map, sự cố+nhật ký, ràng buộc→cài đặt). | S3, S4, S1 | **Nên cân nhắc** (xem Mâu thuẫn #9) |
| A1.11 | **Đồng bộ bộ chọn kịch bản M2/M3:** đổi nhãn "Kịch bản (dùng chung toàn phiên)" + toast; đổi kịch bản ở M3 phải đánh dấu KPI "cần lập lại" (tránh đọc số kịch bản cũ). | S2, S1 | **Nên cân nhắc** |
| A1.12 | **Làm rõ phạm vi stateless/persist** + tùy chọn localStorage cho UI-preference (module/sidebar/bộ lọc), KHÔNG cache dữ liệu nghiệp vụ. | Người dùng, S2 | **Cần làm rõ** (xem Mâu thuẫn #2, Phần C) |
| A1.13 | Landing "Tổng quan/Dashboard" làm màn vào đầu. | S4 | **Cần làm rõ** → Loại theo mặc định (xem Mâu thuẫn #8) |

### A2. BỐ CỤC & MẬT ĐỘ THÔNG TIN

| # | Góp ý | Nguồn | Ưu tiên |
|---|---|---|---|
| A2.1 | **Thu bảng Kế hoạch (15 cột) & P&L (13 cột) còn 6-8 cột thiết yếu**, đẩy chi tiết vào ROW DRAWER (panel phải khi bấm dòng: lỗi/gợi ý/tọa độ/tài chính/hành động). Neo ~7 cột: Mã xe, Tuyến, Đơn, Tải%, Km rỗng, Lợi nhuận, Trạng thái. | S1, S2, S3, S4, Người dùng | **Nên làm ngay** (xem Mâu thuẫn #5, Phần C) |
| A2.2 | **Nút TOGGLE FULLSCREEN/Mở rộng** cho cả BẢNG và BẢN ĐỒ (class `.fs` position:fixed inset:0, KHÔNG dùng Fullscreen API). Yêu cầu trực tiếp người dùng. | Người dùng, S2, S3, S1 | **Nên làm ngay** (⚠ `invalidateSize()` sau resize map) |
| A2.3 | **Layout 3 tầng mỗi module:** Tổng quan KPI → Hành động chính → Chi tiết bảng/map, dùng `.sec-label` tạo nhịp dọc + viền trái amber cho card "Đơn chưa gán". | S1, S3 | **Nên làm ngay** |
| A2.4 | **Thêm breakpoint 1450px** (g4→3 cột) **và 640px** (g3/g4→1 cột) + `white-space:nowrap` cho `.val` để số tiền không gãy dòng. | S1, S2 | **Nên làm ngay** |
| A2.5 | **%Tải vẽ mini progress bar** (>90% xanh, <50% amber) thay text thuần — dùng tint palette, 2-3 ngưỡng. | S4 | **Nên cân nhắc** |
| A2.6 | **Thu form tham số:** bọc `#fin-params` (M5) trong `<details>` gập mặc định; nhóm form M4 (9 input, KHÔNG phải 12) theo 2 cột logic. Giá nhiên liệu vẫn nổi ở toolbar. | S2, S3, S4 | **Nên cân nhắc** |
| A2.7 | **Giảm card-lồng-card + làm gọn #engine-info** thành banner xanh nhạt (`--blue-l` + viền trái, bỏ shadow); làm phẳng 1 cấp div ở M4. | S2, S3 | **Nên cân nhắc** |
| A2.8 | **Sticky cột định danh đầu** (Mã xe/Mã đơn) khi cuộn ngang — lớp phòng hờ cho màn hẹp (z-index góc cao hơn header). | S1, S2, S3 | **Nên cân nhắc** (xem Mâu thuẫn — thừa nếu đã làm A2.1) |
| A2.9 | KPI M3: GIỮ 8 thẻ, gắn nhãn cụm + nâng thẻ Lợi nhuận thành hero. | S1, S2, S3 | **Cần làm rõ** (xem Mâu thuẫn #7, Phần C) |
| A2.10 | Bỏ max-height scroll-lồng ở bảng CHÍNH; giữ cho bảng PHỤ. | S1, S2 | **Cần làm rõ** (xem Mâu thuẫn #6) |
| A2.11 | Bỏ wrapper g2 M3, xếp dọc bảng/bản đồ. | S2 | **Cần làm rõ** (xem Mâu thuẫn #5 — ưu tiên drawer trước) |

### A3. TYPOGRAPHY, THẨM MỸ, BRAND & MICRO-INTERACTION

| # | Góp ý | Nguồn | Ưu tiên |
|---|---|---|---|
| A3.1 | **Token hóa thang typography vào `:root`** (8 cấp: 2xs10/xs11/sm12/md13/base14/lg16/xl20/2xl24) — xóa hết cỡ thập phân (12.3/12.5/12.7/13.5/14.5). `.card h3` 14.5→16. | S1, S2, S3, S4 | **Nên làm ngay** |
| A3.2 | **`font-variant-numeric:tabular-nums`** cho `.kpi .val`, `.kv`, số trong `.formula`/bảng tài chính (chống giật ngang + tiền đề count-up). | S1, S2 | **Nên làm ngay** |
| A3.3 | **Đổi màu chart chi phí về palette HPL:** `['#0B3D91','#1565C0','#4F86D6','#9DBDEA','#B07A00','#E2231A','#9AA7BD']` (bỏ cam/tím/teal lệch brand). | S1, S2, S3 | **Nên làm ngay** |
| A3.4 | **Gauge segment "Thấp"** #E67700 → amber brand `#B07A00`; thêm `text-shadow` cho nhãn `.seg` trắng 10px (đang FAIL AA). | S1, S2 | **Nên làm ngay** |
| A3.5 | **Quy ước màu nút theo ngữ nghĩa:** đỏ CHỈ cho phá hủy/lỗi. "Xuất Excel" đỏ→`btn-line`; "Xóa toàn bộ nhật ký"→`btn-red`. | S1, S2, S3, S4 | **Nên làm ngay** |
| A3.6 | **Hệ token bo góc 4 cấp** (sm8/md10/r12/lg14/xl16) — GIỮ 12px cho card/kpi, gom literal lẻ về thang. | S1, S2, S3 | **Nên làm ngay** (xem Mâu thuẫn #3) |
| A3.7 | **Shadow 2 lớp ám navy nhẹ + hover-lift CHỈ cho `.kpi/.opt/.preset`** (KHÔNG transform card bọc Leaflet/canvas). | S1, S2, S4 | **Nên làm ngay** (xem Mâu thuẫn #4) |
| A3.8 | **Micro-interaction nền:** token `--ease cubic-bezier(.4,0,.2,1)` + `--dur`, fade-in `.view` khi đổi module, hover row rõ hơn (`--blue-l`), `:active scale(.97)`. | S1, S2, S3, S4 | **Nên làm ngay** |
| A3.9 | **`prefers-reduced-motion` toàn cục:** tắt `.pulse` infinite, count-up, mọi keyframes lớn. | S1, S2 | **Nên làm ngay** |
| A3.10 | **GIỮ topbar nền sáng** (#fff) — KHÔNG navy gradient; chỉ thêm viền dưới navy 2px nếu cần điểm nhấn. | S1, S3 | **Nên làm ngay** (xem Mâu thuẫn #6 brand) |
| A3.11 | **Badge 1 hệ class duy nhất** + sửa contrast `.b-rev` (#B07A00/#FFF6E2 = 3.47:1 FAIL) → amber tối `~#8A5E00` (5.31:1). | S1, S2, S3 | **Nên làm ngay** (Lưu ý: refactor badge phần lớn ĐÃ đạt — chỉ còn việc sửa contrast) |
| A3.12 | **Heading nhỏ trong card → `--ink`** (giữ navy chỉ cho h2 trang + logo) tạo 3 tầng phân cấp. | S1, S2 | **Nên cân nhắc** |
| A3.13 | **Sidebar item active: thêm dải đỏ 3px trái** (giữ nền navy) làm signature brand (tránh đụng badge đỏ góc phải). ĐÍNH CHÍNH: active hiện là nền navy đặc, KHÔNG phải xanh lợt. | S4 | **Nên cân nhắc** |
| A3.14 | **AI dock gọn hơn:** nút icon nhỏ có badge "Gợi ý", panel slide/fade theo ngữ cảnh module, tắt `.pulse` khi reduced-motion. | S1, S3, S4 | **Nên cân nhắc** |
| A3.15 | **drawIndicator:** cỡ số 24px inline → token `--fs-2xl`. | S1 | **Nên cân nhắc** |
| A3.16 | COUNT-UP số KPI: CHỈ số đếm nguyên (xe/đơn/km), KHÔNG số tài chính + tabular-nums + reduced-motion. | S2, S4 | **Cần làm rõ** (xem Mâu thuẫn #7 Typo, Phần C) |
| A3.17 | H2 trang 20 vs 24px. | S1/S3 vs S4 | **Cần làm rõ** (xem Phần C) |

### A4. ACCESSIBILITY (WCAG 2.1 AA) & PERFORMANCE

| # | Góp ý | Nguồn | Ưu tiên |
|---|---|---|---|
| A4.1 | **Bàn phím + ngữ nghĩa nav sidebar:** `role=button` + `tabindex=0` + `onkeydown(Enter/Space)` + `aria-current`. Rào cản WCAG-A tuyệt đối. | S1, S2 | **Nên làm ngay** |
| A4.2 | **Focus-trap + Esc-to-close + `role=dialog`/`aria-modal`/`aria-labelledby` + trả focus** cho #modal, #route-modal, #dock. Hiện Esc KHÔNG đóng được gì. | S1, S2, S4 | **Nên làm ngay** |
| A4.3 | **`aria-label` cho mọi nút icon-only** (× đóng, "Xóa" đơn — kèm mã định danh để tránh xóa nhầm). | S1, S2 | **Nên làm ngay** |
| A4.4 | **toast `role=status` + `aria-live`** (polite cho ok/info, assertive cho err) + **skip-link** "Bỏ qua tới nội dung". | S1, S2 | **Nên làm ngay** |
| A4.5 | **Sửa 4 cặp contrast FAIL:** b-rev, nhãn gauge, disabled .5→.6, **spinner navy/navy = 1.00:1 (tàng hình) → biến thể trắng on-dark.** | S1, S2 | **Nên làm ngay** |
| A4.6 | **Focus ring nhất quán 3px** qua token `--focus-ring` (gộp `.edit` 2px → 3px) + `:focus-visible` cho nav/btn/modal-x/preset/tr clickable. | S1, S2 | **Nên làm ngay** |
| A4.7 | **OSRM in-memory cache** (Map theo chuỗi tọa độ) + **AbortController timeout ~4s**, fail nhanh về null (đường thẳng). GIỮ provider OSRM public. Giải "bản đồ chậm" của người dùng. | S1, Người dùng | **Nên làm ngay** (xem Phần C: đường thẳng có cần nhãn "ước lượng"?) |
| A4.8 | **defer Leaflet + lazy-load Chart.js** (chỉ tải khi mở M5) — bỏ 2 script render-blocking khỏi `<head>`. | S1 | **Nên làm ngay** |
| A4.9 | **`prefers-reduced-motion`** chặn animation lặp (= A3.9, gộp 1 đợt). | S1, S2 | **Nên làm ngay** |
| A4.10 | **contenteditable:** `role=textbox` + `aria-label` theo cột cho ô `.edit`. | S1, S2 | **Nên cân nhắc** |
| A4.11 | **CLS:** đưa height map (#map2 v.v.) vào CSS theo id thay vì inline + nền placeholder; `invalidateSize()` sau mọi đổi layout. | S1, S2 | **Nên cân nhắc** |
| A4.12 | **Skeleton loading** thay spinner cho vùng bảng dày + KPI (guard reduced-motion cho shimmer). | S1, S2 | **Nên cân nhắc** |
| A4.13 | **Debounce ~120ms** cho 3 ô tìm kiếm (oninput render lại toàn bảng mỗi keystroke). | S1, S2 | **Nên cân nhắc** |
| A4.14 | **Bảng accessible:** `scope=col` thead + `<caption class=sr-only>` + tr clickable thêm `tabindex/role/onkeydown(Enter)`. | S1 | **Nên cân nhắc** |
| A4.15 | Bỏ `loadLog()` thừa ở init (lý do ĐÚNG: M7 tự tải khi mở, KHÔNG phải "nav('log') đã chạy"). | S1 | **Cần làm rõ** (xem Phần C) |

### A5. TOOL AI & CHỨC NĂNG

| # | Góp ý | Nguồn | Ưu tiên |
|---|---|---|---|
| A5.1 | **Hàm `get_order_detail(store, order_id)`** gom ĐỦ trường 1 đơn (trọng lượng/thể tích/khung giờ/tọa độ/doanh thu/cấm tải) + tra trong `_routes` (tuyến/xe/vị trí stop/ETA) + tra `_unassigned` (lý do + gợi ý). Nhét `don_tra_cuu` vào context cho cả nhánh online + offline. **GAP THẬT** — đúng yêu cầu "không thiếu/sai trường nào". | Người dùng, S3, S4 | **Nên làm ngay** (xem Phần C) |
| A5.2 | **Nút "✨ Hỏi AI lý do"** cạnh mỗi đơn chưa gán, prefill "Vì sao đơn <id> chưa gán và nên xử lý thế nào?" → POST `/api/assistant`, hiển thị trong dock/popover. Backend đã sẵn (`rank_unassigned_orders` trả reason+suggestion). | S4 | **Nên làm ngay** |
| A5.3 | **Mở rộng router intent `_offline_assistant`** thêm nhánh "tra cứu 1 đơn theo mã" (dùng chung `get_order_detail` với nhánh online) — demo dự thi nhiều khả năng chạy offline. | Người dùng | **Nên làm ngay** |
| A5.4 | **Badge minh bạch nguồn + thời điểm + trạng thái** dưới mỗi câu trả lời AI và cạnh giá dầu ("Trực tuyến · Gemini · 19/06 14:20" / "Trợ lý AI · dữ liệu phiên"). Backend đã trả sẵn `source`/`nguon`/`trang_thai`/`cap_nhat_luc`. | Người dùng, S3 | **Nên cân nhắc** |
| A5.5 | **Bổ sung từ khóa `needs_matcher`** ("đơn này chở gì", "đơn X chi tiết", "tại sao đơn X") + cho phép `score_vehicle_order_match` chạy cho 1 đơn cụ thể (xếp hạng xe phù hợp). | Người dùng, S4 | **Nên cân nhắc** |
| A5.6 | **ĐÍNH CHÍNH (không cần làm lại):** giá dầu ĐÃ real-time (30020 chỉ là FALLBACK); Gemini ĐÃ bật `google_search` grounding khi có API key. Việc còn lại = cấu hình `.env` + minh bạch nguồn trên UI. | Người dùng, S1 | **Không nên** (xem Phần D) |
| A5.7 | Danh mục câu hỏi vàng về đơn (để viết test snapshot). | Người dùng | **Cần làm rõ** (Phần C) |
| A5.8 | Phạm vi real-time ngoài giá dầu (cấm đường/thời tiết/tỷ giá?). | Người dùng | **Cần làm rõ** (Phần C) |

### A6. DESIGN SYSTEM, MICROCOPY & AN TOÀN THAO TÁC

| # | Góp ý | Nguồn | Ưu tiên |
|---|---|---|---|
| A6.1 | **Token hóa đầy đủ `:root`:** thêm 5 trục thiếu (type/space/radius-scale/z-index/elevation) trên nền token màu đã có. | S1, S2 | **Nên làm ngay** |
| A6.2 | **Sửa z-index:** dock AI (1200/1201) đang ĐÈ modal (200/201) → phân tầng token: dock < overlay < modal < toast. Khi mở modal P&L mà dock mở, dock che nội dung. | S1, S2 | **Nên làm ngay** |
| A6.3 | **`saveCell` lỗi vẫn hiện giá trị mới như đã lưu → AN TOÀN DỮ LIỆU:** lưu giá trị cũ trước khi gửi, catch thì khôi phục `el.textContent` + viền đỏ; đang lưu=amber; OK=green. | S2 | **Nên làm ngay** |
| A6.4 | **Microcopy:** tách lỗi mạng vs lỗi nghiệp vụ trong `api()`; cảnh báo xóa toàn bộ nhật ký nêu rõ số dòng + "dữ liệu kiểm toán, KHÔNG THỂ hoàn tác" (hiện 1290 cảnh báo YẾU hơn 1286). | S1 | **Nên làm ngay** |
| A6.5 | **Token màu chart/gauge** lệch brand → palette HPL (= A3.3/A3.4, thuộc semantic-color token). | S1, S2, S3 | **Nên làm ngay** |
| A6.6 | **Affordance ô sửa:** `.edit` viền dashed nhạt (`#cdd9ec`) báo sửa được + role/aria. | S1, S2 | **Nên cân nhắc** |
| A6.7 | **confirm() 6 chỗ → PHỐI HỢP:** modal `#confirm-modal` RIÊNG cho thao tác NẶNG (xóa toàn bộ log, áp dụng P&L, hoàn tất sự cố) + Undo-toast cho thao tác NHẸ (xóa 1 đơn, xóa 1 dòng log). | S1, S2, S4 | **Nên cân nhắc** (xem Mâu thuẫn #10) |
| A6.8 | **Empty-state có icon + CTA bấm được** (bọc `<div>` vì `.empty` đặt trên `<td>`) — "Chạy kế hoạch tuyến". | S1, S2, S3, S4 | **Nên cân nhắc** |
| A6.9 | **Chỉ báo "đang đồng bộ"** nhỏ trên topbar (idle/saving/error) — cùng cơ chế với A6.3. | S2 | **Nên cân nhắc** |
| A6.10 | **Command palette ⌘/Ctrl+K** + phím tắt 1–7 nhảy module, / focus tìm, Esc đóng (gộp với A4.2). | S2 | **Nên cân nhắc** (cần JS mới đáng kể) |
| A6.11 | Density toggle (.compact). | S2 | **Cần làm rõ** → Loại theo mặc định (Phần D) |
| A6.12 | Lưu trạng thái phiên localStorage. | S2 | **Cần làm rõ** (= A1.12, xem Mâu thuẫn #2) |
| A6.13 | Sticky action bar cuối module. | S2 | **Cần làm rõ** (trùng next-best-action, Phần C) |

---

## PHẦN B — NHẬT KÝ MÂU THUẪN (Conflict Log)

| # | Góp ý A ↔ Góp ý B | Mâu thuẫn ở điểm nào | Quan điểm hội đồng | Khuyến nghị + lý do |
|---|---|---|---|---|
| **1 (i)** | **Người dùng:** STATELESS, tự do nhảy module, không ép optimize trước tài chính ↔ **S2 rank6 + S4:** KHÓA cứng/wizard ép thứ tự M4/M5 (`pointer-events:none`+🔒) | Triết lý điều hướng cốt lõi: tự do vs ép tuần tự + khóa. Mâu thuẫn lớn nhất, chi phối toàn bộ kiến trúc nav. | Lead UX: theo người dùng — chuyên gia không bị chặn. Lead FE: phụ thuộc dữ liệu là THẬT (`/api/financial`, `/api/backhaul` chặn `if not routes`, finance tính TỪ routes). A11y: `pointer-events:none` phá focus bàn phím. Designer: `_run_optimize` tái dùng được → auto-run ngầm khả thi. | **KHÔNG khóa cứng. Dung hòa 3 lớp:** (1) vào M4/M5 thiếu routes → auto-run optimize ngầm + toast; (2) nếu lỗi → empty-state có CTA (KHÔNG màn lỗi đỏ); (3) stepper CHỈ hiển thị trạng thái + bấm được. Giữ `nav()` free-jump. **Lý do:** trọng số chủ sản phẩm cao + sự thật code → auto-run là cách DUY NHẤT vừa "bấm đâu cũng được" vừa không trả màn lỗi (best practice B2B Linear/Stripe). |
| **2 (ii)** | **Người dùng:** "đã lưu trên hệ thống thì vào thẳng" ↔ **Kiến trúc:** STORE là dict RAM, không persist; routes/financial=None tới khi optimize; restart mất sạch | Kỳ vọng "đã lưu" không khớp hiện trạng — không có lớp persist. | Lead FE: grep không có localStorage/pickle/sqlite. Designer: localStorage chỉ khôi phục UI-state, KHÔNG khôi phục routes/finance (ở RAM server). | **Đợt này:** (1) làm rõ phạm vi "stateless" = sống trong phiên server (Phần C); (2) tận dụng `_autoload()` demo + auto-run; (3) localStorage CHỈ cho UI-preference, KHÔNG cache dữ liệu nghiệp vụ; persist xuống đĩa để "dài hạn" nếu người dùng cần. **Lý do:** cache số tài chính ở client = lệch nguồn chân lý = rủi ro quyết định sai. |
| **3 (iii)** | **S3:** giảm radius 12→8px toàn cục ↔ **S1/S2:** GIỮ 12px, chuẩn hóa literal về thang token | Giá trị radius nền + cách xử lý ~12 literal lẫn lộn (3–16px). | Designer: 12px mềm mà chắc cho B2B; 8px làm card cứng/mỏng. Lead FE: vấn đề thật là sự hỗn loạn, không phải con số. | **GIỮ 12px** cho card/kpi. Token 4 cấp: sm8 (field/chip) / md10 (tbl-wrap/map/opt) / r12 (card/kpi) / lg14 (modal) / xl16 (dock). Find-replace literal lẻ. **Lý do:** đẳng cấp đến từ tính nhất quán (token scale), không từ radius nhỏ hơn; giữ 12 bảo toàn nhận diện (đề bài cấm thay đổi ở mức tinh chỉnh). |
| **4 (iv)** | **S1/S4:** tăng shadow 2 lớp + hover-lift card ↔ **S3:** giảm shadow, dùng border | Hướng elevation + có/không hover-lift transform. | Lead UX: hiện .06 alpha gần vô hình, card/nền chênh sáng ~1.07:1 → "phẳng đều", cần tăng nhẹ. A11y: transform card bọc Leaflet/canvas làm NHÒE tile. | **Điểm giữa:** tăng shadow 2 lớp tinh tế ám navy (vd `0 1px 3px rgba(11,61,145,.06), 0 4px 12px rgba(11,61,145,.05)`); hover-lift translateY CHỈ `.kpi/.opt/.preset`; card map/canvas chỉ đổi box-shadow khi hover, KHÔNG transform; guard reduced-motion. **Lý do:** hiện trạng quá phẳng cần hierarchy (điều S3 chưa thấy) nhưng giữ tinh tế (đúng tinh thần S3); ngoại lệ transform là ràng buộc kỹ thuật cứng. |
| **5 (v)** | **S4:** topbar navy gradient chữ trắng ↔ **S1/S3:** GIỮ topbar sáng | Nền topbar — độ nặng thị giác, contrast control, brand. | Lead UX: khung trái đã navy đặc → thêm topbar navy "nặng đầu". A11y: chip-ai + btn-line thiết kế cho nền sáng sẽ FAIL trên navy = nợ a11y mới. Designer: B2B chuộng nền sáng để dữ liệu nổi. | **GIỮ topbar sáng (#fff).** Điểm nhấn brand: viền dưới navy 2px mảnh thay 1px xám. Loại đề xuất navy gradient. **Lý do:** đề bài "chỉ đánh bóng, giữ nhận diện" — phủ mảng navy lớn là thay đổi lớn; lợi ích thẩm mỹ không bù rủi ro contrast hàng loạt + khó đọc chip trạng thái. |
| **6 (vi)** | **S2/S4:** count-up mọi KPI (cả số tài chính) ↔ **S1/S2:** số tài chính đọc chính xác tức thì + tabular-nums + reduced-motion | Animate vs đọc chính xác số tiền/biên LN dưới áp lực. | S4: count-up tạo "wow" dự thi. A11y: vi phạm WCAG 2.3.3 nếu không guard; `.kpi .val` chưa có tabular-nums → giật layout. Lead UX: số tiền nhảy từ 0 dễ đọc nhầm. | **Count-up CHỈ số ĐẾM nguyên (xe/đơn/km), tốt nhất 1 KPI hero/màn. TUYỆT ĐỐI KHÔNG count-up tiền/biên LN.** Bắt buộc: tabular-nums trước + `@media(prefers-reduced-motion)` hiện ngay số cuối. **Lý do:** giữ "wow" cho dự thi mà không hi sinh tính chính xác P&L; tabular-nums là tiền đề kỹ thuật. |
| **7 (vii)** | **S2 rank11:** GIỮ 2 grid KPI (8 thẻ) + nhãn cụm ↔ **S2 rank42 (tự mâu thuẫn) / S3:** cắt 4 / **Người dùng #1:** "gộp 2 thẻ" | Số lượng & trình bày 8 KPI ở M3 — mâu thuẫn 3 chiều. | A11y+UX: dispatcher cần cả 8 số (km rỗng % = chỉ số tối ưu cốt lõi, standby, biên LN); cắt 4 GIẤU số ra-quyết-định. Designer: người dùng muốn "gộp" → 1 lưới + nhãn cụm. Lead FE: gộp phải xóa cả lệnh gán #plan-kpis2 (795) + reset (776), nếu không lỗi null. | **GIỮ 8 thẻ (không cắt 4).** Gộp 2 grid về 1 lưới liền mạch theo ý người dùng + `.sec-label` nhãn cụm + nâng thẻ Lợi nhuận thành hero (`green hero`, .val 28px). Quyết định cuối thuộc chủ sản phẩm (Phần C). **Lý do:** control tower là bài toán mật-độ-cao CÓ CHỦ ĐÍCH; "bớt ngợp" = phân tầng, không phải mất số. |
| **8 (viii)** | **S4:** thêm landing Dashboard ↔ **S3/Người dùng:** next-best-action + "giảm thứ tranh trung tâm" | Thêm màn mới vs định hướng ở trạng thái trống. | Lead FE: mở app routes=None → Dashboard RỖNG. Lead UX: Dashboard rỗng phản tác dụng; stepper rẻ hơn. | **KHÔNG thêm landing Dashboard đợt này.** Thay bằng thanh stepper (phục vụ next-best-action tốt hơn, công thấp, không thêm module). **Lý do:** stepper + Dashboard phục vụ mục tiêu gần giống; Dashboard rỗng trừ khi auto-run (chi phí/lợi ích không thuyết phục). |
| **9 (ix)** | **S1:** sidebar 6 bước ĐÁNH SỐ + 1 cài đặt ↔ **S3:** nhóm theo CHỨC NĂNG (không số) ↔ **S4:** 5 tab lớn có tab con | Mô hình IA sidebar — 3 biến thể. | S1: đánh số khớp stepper + ghi chú người dùng "tự làm theo bước". S3: nhóm chức năng phản ánh tư duy dispatcher. Lead FE: 5 tab cần đập cơ chế `nav()` view-* = nhiều hồi quy. | **GIỮ ĐÁNH SỐ BƯỚC + gộp NÔNG các mục trùng (9→6-7):** map vào nút mở rộng, M6+M7 thành tab, ràng buộc xuống cài đặt ⚙. KHÔNG refactor sâu 5 tab. **Lý do:** đánh số củng cố stepper + khớp người dùng; gộp nông đạt "bớt ngợp" với hồi quy thấp hơn nhiều so với đập cơ chế view. |
| **10** | **S2:** custom modal cho MỌI confirm() ↔ **S4:** Undo-toast cho mọi xóa | Cách thay 6 confirm() — modal trước vs thực thi ngay + hoàn tác. | Lead UX: hai hướng BỔ TRỢ theo mức nguy hiểm/khả hồi. Lead FE: dòng 1290 (xóa toàn bộ log) hiện cảnh báo YẾU hơn 1286 (xóa 1 dòng) — sai phân cấp. | **PHỐI HỢP theo mức:** NẶNG/không hồi (xóa toàn bộ log, áp dụng P&L, hoàn tất sự cố) → `confirmBox()` = `#confirm-modal` RIÊNG nêu rõ hậu quả + "KHÔNG THỂ hoàn tác"; NHẸ/khả hồi (xóa 1 đơn, 1 dòng log) → thực thi ngay + Undo-toast. SỬA microcopy 1290. **Lý do:** ma sát tương xứng mức nguy hiểm; `#confirm-modal` phải riêng (tránh xung đột trạng thái với #modal/#route-modal). |
| **11** | **S1 #44:** refactor badge inline-style về class ↔ **Code thật:** badge ĐÃ dùng class .badge + modifier nhất quán | Tiền đề S1 #44 đã lỗi thời. | Lead FE: mọi nơi render đã `class="badge ${bd}"`; không còn inline cần gom. | **Không refactor badge** (đã đạt). Việc THẬT còn lại: sửa contrast `.b-rev` FAIL AA (= A3.11). **Lý do:** tránh tốn công làm lại; tập trung vào lỗi contrast thực sự. |

---

## PHẦN C — GÓP Ý CẦN LÀM RÕ

**C1. Phạm vi stateless & persist dữ liệu** *(quan trọng nhất — quyết định khối lượng việc)*
Khi anh nói "đã lưu trên hệ thống thì vào thẳng module bất kỳ", anh muốn dữ liệu (đơn đã sửa, kế hoạch tuyến, P&L) tồn tại **QUA việc restart server / đóng trình duyệt** không? Hiện STORE chỉ ở RAM (app.py:66-83), mất sạch khi restart, và routes/financial=None tới khi chạy optimize. Anh cần lưu xuống đĩa (file/DB) hay chỉ giữ trong phiên chạy là đủ?
→ *Vì sao:* quyết định có phải xây lớp persistence mới (đáng kể) hay chỉ dùng auto-run + localStorage UI-preference.

**C2. Hành vi khi vào M4/M5 mà chưa có kế hoạch**
(a) Hệ thống TỰ chạy lập tuyến ngầm rồi hiện kết quả tài chính (kèm toast), hay (b) hiện empty-state "Chưa có kế hoạch, bấm để lập" để anh tự quyết? *(Tài chính tính TỪ tuyến nên không có tuyến thì không có số.)*
→ *Vì sao:* định hình toàn bộ luồng M4/M5 và trải nghiệm "bấm đâu cũng được". Hội đồng nghiêng về (a) auto-run.

**C3. Số KPI ở M3 (8 vs 4 vs gộp 1 lưới)**
Khi điều phối thực tế, anh có cần nhìn đồng thời cả 8 chỉ số (xe dùng/đơn gán/chưa gán/standby + km/km rỗng/DT-CP/lợi nhuận) ngay sau optimize không? Và chọn: (A) giữ 2 grid có nhãn cụm, (B) gộp 1 lưới + nhãn cụm + 1 thẻ hero, hay (C) 4 số kết quả gán đủ rồi?
→ *Vì sao:* ảnh hưởng thông tin ra-quyết-định + rủi ro hồi quy JS #plan-kpis2. Hội đồng khuyến nghị (B).

**C4. Mô hình sidebar cuối cùng**
(A) giữ đánh số bước 1→6 + gộp mục trùng (khuyến nghị hội đồng); (B) nhóm chức năng không đánh số; (C) 5 tab lớn có tab con?
→ *Vì sao:* quyết định khối lượng refactor — (A) rẻ/an toàn, (C) đập cơ chế view = nhiều hồi quy.

**C5. Drawer chi tiết tuyến vs xếp dọc bảng/bản đồ**
(A) panel trượt phải khi bấm dòng [bản đồ giữ nguyên], hay (B) bảng full-width trên + bản đồ dưới [phải cuộn xuống]? Hai cách KHÔNG kết hợp được cho cùng màn M3.
→ *Vì sao:* nếu chọn (B), bấm dòng không thấy bản đồ phản hồi ngay. Hội đồng nghiêng (A) drawer.

**C6. Phạm vi nút fullscreen**
Phủ KÍN toàn màn hình (ẩn sidebar/topbar) hay chỉ phóng to card trong vùng nội dung?
→ *Vì sao:* ảnh hưởng cách triển khai (`.fs position:fixed inset:0` vs phóng trong content) + bắt buộc `invalidateSize()` + nút thoát/Esc.

**C7. H2 tiêu đề trang** — giữ 20px (S1/S3) hay nâng 24px tracking -0.5px (S4)?
→ *Vì sao:* ảnh hưởng chiều cao page-head + nhịp dọc; cần chốt 1 giá trị để token hóa thang typography sạch.

**C8. Count-up KPI** — anh có muốn hiệu ứng count-up không? Nếu có, chỉ áp 1 KPI hero (số đếm), bọc reduced-motion + tabular-nums; số tài chính hiện ngay. Đồng ý phạm vi này?

---

### TOOL AI — ĐÍNH CHÍNH + CÂU HỎI

> **ĐÍNH CHÍNH QUAN TRỌNG (tránh làm lại thừa + rủi ro hồi quy):**
> - **Giá dầu ĐÃ real-time.** `fuel_price.py` đã crawl Petrolimex (urllib/requests), parse JSON+HTML, cache TTL 24h, có `refresh_now()` cho UI, đẩy giá động vào P&L. **30020 chỉ là `FALLBACK_PRICE`** (fuel_price.py:36) khi mất mạng/chưa cấu hình — KHÔNG phải hard-code.
> - **Gemini ĐÃ có google_search.** `_call_gemini` thêm `tools=[{google_search:{}}]` khi `web=True` (gemini_ai.py:117); `ask_gemini` gọi `web=True`. Khi có `GEMINI_API_KEY`, trợ lý ĐÃ tra Internet real-time. Hiện chạy offline `_offline_assistant` vì **thư mục KHÔNG có file `.env`** (chỉ có `.env.example`) — đó là lý do cảm giác "cố định", KHÔNG do code.
> - **GAP THẬT:** `get_route_context` (gemini_ai.py:296-323) chỉ truyền `'don': r.get('orders')` = list mã đơn, KHÔNG có chi tiết từng đơn → AI không đủ trường để trả chính xác khi hỏi về 1 đơn. Đây là việc cần làm (A5.1).

**C9. Cấu hình real-time:** Máy chạy demo đã có `GEMINI_API_KEY` và `FUEL_PRICE_URL` trong `.env` chưa? Nếu chưa, cần đặt để thoát chế độ dự phòng.

**C10. Danh mục câu hỏi vàng về đơn:** Anh liệt kê giúp 8-12 câu hỏi cụ thể dispatcher hay hỏi (vd: "đơn X gồm gì", "đơn X gán xe nào, ETA bao nhiêu", "vì sao đơn X chưa gán", "đơn X lãi/lỗ bao nhiêu", "đơn X có ghép chiều về được không", "sự cố ảnh hưởng đơn X thế nào")?
→ *Vì sao:* "TẤT CẢ câu hỏi" là vô hạn — có danh mục mới viết được `get_order_detail` + test snapshot đảm bảo phủ 100% trường.

**C11. Phạm vi real-time ngoài giá dầu:** Anh có muốn AI tra cứu real-time loại dữ liệu mở nào khác (tin cấm đường/cấm tải theo địa phương, thời tiết tuyến, tỷ giá/phụ phí)? Nếu có, cần nguồn ưu tiên để quyết định dùng `google_search` (đã có) hay viết crawler riêng.

**C12. Hiển thị nguồn AI/giá dầu:** Anh có muốn mỗi câu trả lời + giá dầu kèm badge nguồn + thời điểm không? (Backend đã trả sẵn — chỉ cần frontend render.)

**C13. Bỏ `loadLog()` ở init:** Có nơi nào cần dữ liệu nhật ký SẴN trước khi mở M7 không (export, AI dock đọc log)? Nếu không, xác nhận bỏ.

---

## PHẦN D — GÓP Ý NÊN LOẠI BỎ

| Góp ý | Lý do | Mức |
|---|---|---|
| **Wizard/stepper ÉP THỨ TỰ + KHÓA cứng (Disable) M4/M5** (S2 rank6, S4) | Đi ngược yêu cầu trực tiếp chủ sản phẩm ("ai quan tâm gì bấm đấy") + ngược best-practice công cụ vận hành. Phụ thuộc dữ liệu là thật nhưng giải đúng = auto-run ngầm + stepper bấm-được, KHÔNG khóa. Khóa cứng biến lỗi-dữ-liệu thành rào-cản-điều-hướng. | **Loại hẳn** |
| **Khóa nav `.nav-item.locked{pointer-events:none}` + 🔒** (S2 rank6) | `pointer-events:none` phá focus bàn phím + bị screen reader bỏ qua → mâu thuẫn CHÍNH mục tiêu a11y rank1 của S2. Dùng `aria-disabled` + thông báo trạng thái (vẫn focus được). | **Loại hẳn** |
| **Topbar navy gradient nền tối** (S4) | Khung trái đã navy đặc → "nặng đầu"; chip-ai + btn-line FAIL contrast trên navy = nợ a11y mới, buộc sửa hàng loạt control; ngược "chỉ đánh bóng, giữ nhận diện". Thay bằng viền dưới navy 2px. | **Loại hẳn** |
| **Viết lại tool giá dầu vì "cố định 30020"** | Sai hiện trạng — `fuel_price.py` đã là pipeline real-time đầy đủ; 30020 là FALLBACK. Viết lại = lãng phí + rủi ro hồi quy. Việc đúng: cấu hình `.env` + minh bạch nguồn UI. | **Loại hẳn** |
| **Viết lại "tool AI search real-time" vì cho rằng chưa có** | Sai hiện trạng — Gemini đã bật `google_search` khi `web=True`. Việc còn lại: đặt API key + hiển thị nhãn "Trực tuyến · Gemini". | **Loại hẳn** |
| **Nhồi TOÀN BỘ dữ liệu mọi đơn vào mỗi prompt AI** | Phản tác dụng: tăng token, chậm, tốn phí, loãng context → mô hình dễ sai. Đúng: chỉ inject `get_order_detail(order_id)` của đơn đang hỏi. | **Loại hẳn** |
| **Đổi màu marker `L.divIcon` sang `var()`** | Template string KHÔNG nội suy CSS var → marker MẤT MÀU. Giữ literal hex (902-904) như ngoại lệ có chủ đích. (Màu chart qua JS array thì đổi tự do — nên làm.) | **Loại hẳn** |
| **Refactor badge inline-style về class** (S1 #44 gốc) | Đã đạt — badge hiện đã dùng class nhất quán. Việc còn lại: sửa contrast `.b-rev`. | **Loại hẳn** |
| **Count-up cho số TÀI CHÍNH/P&L** (S4) | Số tiền nhảy từ 0 tạo giá trị trung gian sai lệch ~1s → đọc nhầm dưới áp lực; vi phạm reduced-motion nếu không guard; `.kpi .val` chưa tabular-nums → giật. Chỉ count-up số đếm + 1 hero. | **Loại theo mặc định (cho tùy chọn)** |
| **Giảm đại trà radius 12→8px** (S3) | Card mật-độ-cao trông cứng/mỏng + sửa hàng loạt literal dễ sót. Giải đúng: token scale, GIỮ 12. | **Loại theo mặc định (cho tùy chọn)** |
| **Cắt M3 KPI xuống 4 chỉ số** (S3) | Giấu số vận hành quan trọng (km rỗng %, standby, biên LN). Giải đúng: GIỮ 8 + phân tầng. | **Loại theo mặc định (cho tùy chọn)** |
| **Landing Dashboard làm màn vào đầu** (S4) | routes=None khi mở → Dashboard RỖNG, phản tác dụng. Stepper phục vụ tốt hơn, công thấp hơn. | **Loại theo mặc định (cho tùy chọn)** |
| **Refactor sidebar sâu 5 tab có tab con** (S4) | Cần đập cơ chế `nav()` view-* = nhiều hồi quy cho sản phẩm dự thi. Gộp nông đạt cùng mục tiêu, rủi ro thấp hơn. | **Loại theo mặc định (cho tùy chọn)** |
| **Density toggle `.compact`** (S2) | Tính năng phụ làm phình phạm vi + thêm trạng thái phải test trên mọi bảng. Để "dài hạn", làm SAU khi token hóa spacing. | **Loại theo mặc định (cho tùy chọn)** |

---

## PHẦN E — LỘ TRÌNH HÀNH ĐỘNG

### ⚡ Quick wins (làm ngay, tác động lớn, công thấp)

| # | Hành động | Ước công | Nguồn / Conflict |
|---|---|---|---|
| Q1 | **Token hóa `:root`** (type 8 cấp + radius 4 cấp + z-index + elevation + `--ease`/`--dur`/`--focus-ring`) + xóa cỡ thập phân + find-replace literal | ~3-4h | A3.1/A3.6/A6.1, Conflict #3 |
| Q2 | **A11y nav + modal + toast:** role/tabindex/aria-current/onkeydown nav; focus-trap + Esc + role=dialog modal/dock; toast aria-live; aria-label nút icon; skip-link | ~4h | A4.1-A4.4 |
| Q3 | **Sửa 4 cặp contrast FAIL** (b-rev→#8A5E00, gauge text-shadow, disabled .6, spinner trắng on-dark) + focus ring 3px nhất quán | ~1.5h | A4.5/A4.6/A3.11, Conflict #11 |
| Q4 | **Màu chart/gauge về palette HPL** + tabular-nums KPI/.kv + `prefers-reduced-motion` block | ~1.5h | A3.2-A3.4/A4.9, Conflict #6 |
| Q5 | **Quy ước màu nút** (Xuất Excel bỏ đỏ, xóa toàn bộ→đỏ) + microcopy lỗi mạng/nghiệp vụ + cảnh báo xóa log 1290 | ~1.5h | A3.5/A6.4 |
| Q6 | **`saveCell` an toàn dữ liệu** (khôi phục giá trị cũ khi lỗi + trạng thái màu) + chỉ báo "đang đồng bộ" topbar | ~2h | A6.3/A6.9 |
| Q7 | **Sửa z-index dock < modal** (token z-* phân tầng) | ~0.5h | A6.2 |
| Q8 | **Nút fullscreen/mở rộng** bảng + bản đồ (`.fs` + `invalidateSize()`) — *yêu cầu trực tiếp người dùng* | ~3h | A2.2, C6 |
| Q9 | **Gộp view-map vào nút mở rộng M3** (dọn drawFullMap + nhánh nav + option) + chuyển Ràng buộc → ⚙ cài đặt | ~2h | A1.3/A1.4, Conflict #9 |
| Q10 | **Thanh stepper bấm-được** (render từ STATE/api/status, không khóa) + kích hoạt `.step-tag` | ~4h | A1.1/A1.5, Conflict #1/#8 |
| Q11 | **Auto-run optimize ngầm** khi vào M4/M5 thiếu routes + toast + empty-state CTA | ~3h | A1.2, Conflict #1, C2 |
| Q12 | **Breakpoint 1450/640px** + defer Leaflet/lazy Chart.js + OSRM cache+timeout + debounce tìm kiếm | ~3h | A2.4/A4.7/A4.8/A4.13 |
| Q13 | **AI: `get_order_detail` + intent tra cứu đơn** (online + offline) + nút "✨ Hỏi AI lý do" cạnh đơn chưa gán + badge nguồn | ~5-6h | A5.1-A5.4, C10 |

### 🏗️ Dài hạn (đầu tư nhiều)

| # | Hành động | Ước công | Nguồn |
|---|---|---|---|
| L1 | **Row drawer chi tiết tuyến** (thu bảng 15/13 cột → 6-8, panel phải) — *yêu cầu người dùng "kéo kéo mãi khá rối"* | ~8-10h | A2.1, Conflict #5, C5 |
| L2 | **Gộp 2 grid KPI + nhãn cụm + thẻ hero** + layout 3 tầng `.sec-label` + %Tải progress bar | ~5h | A2.3/A2.9/A2.5, Conflict #7 |
| L3 | **Gộp M6+M7 thành "Vận hành"** với tab nội bộ (logTab toggle theo ID riêng) | ~5h | A1.6, Conflict #9 |
| L4 | **confirmBox() `#confirm-modal` riêng + Undo-toast** theo mức nguy hiểm | ~5h | A6.7, Conflict #10 |
| L5 | **localStorage UI-preference** (module/sidebar/bộ lọc) — KHÔNG cache dữ liệu nghiệp vụ | ~3h | A1.12, Conflict #2, C1 |
| L6 | **Command palette ⌘K + phím tắt 1–7** (index module + mã đơn/xe) | ~6-8h | A6.10 |
| L7 | **Hợp nhất nguồn backhaul** (`/api/backhaul` → alias matcher) + gộp lối nhập M1→M4 | ~4h | A1.8/A1.9 (cần đọc app.py 1061+ trước) |
| L8 | **Bộ test snapshot AI** đảm bảo phủ 100% trường đơn (sau khi có danh mục C10) | ~5h | A5.7, C10 |
| L9 | **Persist xuống đĩa** (file/DB) — CHỈ nếu C1 xác nhận cần dữ liệu sống qua restart | ~8h+ | Conflict #2, C1 |

### ⚠️ Lưu ý hồi quy kỹ thuật (bẫy phá chức năng — kiểm trước khi commit)

1. **`map.invalidateSize()` BẮT BUỘC** sau MỌI đổi layout chứa #map/#bk-map/#inc-map (fullscreen, bỏ g2, drawer) — nếu không tile xám/lệch. Pattern đã có sẵn (line 613/946).
2. **Loop drag&drop dòng 1337:** xóa drop card backhaul ở M1 mà QUÊN bỏ `'backhaul'` khỏi mảng key → `querySelector('#f-backhaul').previousElementSibling` của null ném TypeError lúc init, **chết toàn bộ JS** (kể cả refreshStatus). Kiểm tra mảng key thực tế; `#f-bk4` (M4) KHÔNG nằm trong loop này.
3. **Gộp 2 grid KPI:** phải xóa CẢ lệnh gán `#plan-kpis2` (line 795) VÀ dòng reset 776 (`'#plan-kpis2'.innerHTML=''`) — nếu không innerHTML ghi vào phần tử không còn = lỗi null.
4. **`L.divIcon` (902-904):** KHÔNG đổi màu sang `var()` — template string không nội suy CSS var, marker mất màu. Giữ literal hex như ngoại lệ.
5. **Xóa view-map:** phải dọn KÈM `drawFullMap()` (line 950) + nhánh `if(v==='map')setTimeout(drawFullMap,80)` (line 612) + option nav `data-view='map'` — nếu không route chết/gọi hàm không tồn tại.
6. **A1.9 backhaul alias:** chưa đủ căn cứ — phải đọc `app.py:1061-1458` + `ai_matcher.py` xác nhận route UI thật sự gọi (`/api/backhaul` vs `/api/matcher/backhaul`) TRƯỚC khi alias.
7. **`#confirm-modal` phải RIÊNG** — KHÔNG tái dùng #modal/#route-modal (xung đột trạng thái).

---

*Cấu trúc báo cáo này giữ đánh số tham chiếu (A1.x, Conflict #n, Q/L) để các đợt góp ý sau dán vào đúng mục, cập nhật trạng thái mà không phải viết lại.*

Hai file nguồn đã đối chiếu: `/private/tmp/claude-501/-Users-leanhduc/b1538405-d560-4707-9990-512153ac98d5/scratchpad/feedback_batch1.md` (S2/S3/S4 + ghi chú người dùng) và thư mục dự án `/Users/leanhduc/Downloads/Gi-i-g-c-ng-c-main 2/` (lưu ý: `BAO_CAO_DANH_GIA_UX.md` gốc của S1 không còn trong thư mục — nội dung S1 đã được bóc tách đầy đủ trong nguyên liệu panel).


---

## PHỤ LỤC — DỮ LIỆU PANEL THÔ (để đối chiếu / cập nhật đợt sau)

*Tổng hợp ĐỢT 1 · 19/06/2026 10:32 · 89 góp ý khử trùng (6 chủ đề) · 10 mâu thuẫn · 11 cần làm rõ · 14 đề xuất loại.*

### Conflict log (panel)

**#1. GHI CHÚ NGƯỜI DÙNG #4 (chủ sản phẩm, trọng số cao nhất): DÙNG STATELESS — tự do nhảy vào bất kỳ module nào, KHÔNG bắt chạy tối ưu tuyến rồi mới ra tài chính ('ai quan tâm gì bấm đấy') ↔ S2 rank6 + S4: KHÓA cứng / WIZARD ép thứ tự — disable M4 (Ghép chiều về) & M5 (Tài chính) khi chưa chạy M3, dùng .nav-item.locked{pointer-events:none}+🔒**
- Mâu thuẫn: Triết lý điều hướng cốt lõi: tự do nhảy module (stateless) vs ép tuần tự + khóa cứng. Đây là mâu thuẫn lớn nhất, chi phối toàn bộ kiến trúc nav.
  - Lead UI/UX: Theo ghi chú người dùng — công cụ vận hành dùng cả ngày, dispatcher thành thạo phải được bấm thẳng vào module họ cần; khóa cứng biến lỗi-dữ-liệu thành rào-cản-điều-hướng, hạ trải nghiệm chuyên gia.
  - Lead Frontend (sự thật code): Phụ thuộc dữ liệu là THẬT — /api/financial (app.py:870-875) và /api/backhaul (app.py:819-824) ĐỀU chặn cứng `if not d or not routes: return error`. Finance được tính TỪ routes (financials_detailed(routes,...) app.py:877), nên không có routes thì KHÔNG có gì để tính. Stateless 'thật sự bỏ qua optimize' là bất khả thi ở tầng dữ liệu.
  - A11y/Perf: pointer-events:none (đề xuất của S2) khiến nav-item KHÔNG focus được bằng bàn phím và bị một số screen reader bỏ qua — đi ngược chính mục tiêu a11y rank1 của S2. Người dùng bàn phím sẽ không hiểu vì sao bấm không được. Phải dùng aria-disabled + thông báo trạng thái, KHÔNG chặn cứng.
  - Product Designer: Hai mục tiêu có thể dung hòa — vì _maybe_auto_optimize/_run_optimize (app.py:643,505) đã tự chạy engine khi load demo/import (app.py:338-339), hoàn toàn khả thi gọi optimize NGẦM khi người dùng vào M4/M5 mà chưa có routes.
- ✅ Khuyến nghị: KHÔNG khóa cứng module. Giải pháp dung hòa 3 lớp: (1) Khi người dùng vào M4/M5 mà STATE.routes rỗng → TỰ CHẠY optimize ngầm (gọi /api/plan) rồi mới tính finance/backhaul, kèm toast 'Đang lập tuyến để tính tài chính…'; (2) Nếu auto-run lỗi/không có dữ liệu nền → hiện empty-state có CTA 'Chạy kế hoạch tuyến' (KHÔNG phải màn lỗi đỏ); (3) Thanh quy trình (stepper) phía trên CHỈ hiển thị trạng thái từng bước (Chưa làm/Có lỗi/Sẵn sàng/Hoàn tất) và BẤM ĐƯỢC để nhảy — không disable bước nào. Giữ nav() free-jump hiện có (dashboard.html:600).
- Lý do: Best practice cho công cụ vận hành B2B (Linear/Stripe-grade): không bao giờ chặn người dùng thành thạo bằng wizard cưỡng bức; xử lý tiền-đề ngầm thay vì đẩy gánh nặng thứ tự sang người dùng. Trọng số chủ sản phẩm cao + sự thật code (finance cần routes) → auto-run ngầm là cách DUY NHẤT vừa tôn trọng 'bấm đâu cũng được' vừa không trả màn lỗi. Backend đã có sẵn _run_optimize tái dùng được, frontend chỉ cần guard 'nếu thiếu routes thì await optimize trước'.

**#2. Người dùng: 'miễn là đã lưu rồi trên hệ thống thì vào thẳng module bất kỳ' ↔ Thực tế kiến trúc: STORE là dict RAM thuần (app.py:66-83), KHÔNG persist; _routes/_financial = None tới khi optimize; restart server mất sạch**
- Mâu thuẫn: Kỳ vọng 'đã lưu trên hệ thống' không khớp hiện trạng — chưa chạy optimize thì không có gì để 'vào thẳng', và không có lớp persist nào.
  - Lead Frontend (code): grep toàn app.py KHÔNG có localStorage/sessionStorage/pickle/sqlite/persist (đã xác minh). STORE là in-memory dict; _autoload() (app.py:209) chỉ nạp lại demo mỗi lần khởi động → có dữ liệu NỀN nhưng routes/financial vẫn None tới khi optimize.
  - Lead UI/UX: Cần nói thẳng với chủ sản phẩm rằng 'lưu trên hệ thống' hiện chỉ đúng TRONG PHIÊN server đang chạy. Không nên hứa hành vi persist mà code không có.
  - Product Designer: localStorage có thể khôi phục TRẠNG THÁI UI (module đang xem, sidebar, bộ lọc, density) khi F5 — nhưng KHÔNG khôi phục routes/finance (nằm ở RAM server). Phải tách rạch ròi: localStorage chỉ giữ UI-preference, KHÔNG cache dữ liệu nghiệp vụ (tránh hiển thị số cũ lệch backend).
- ✅ Khuyến nghị: Trong đợt này: (1) Làm rõ với người dùng phạm vi 'stateless' = sống trong phiên server (xem clarification). (2) Tận dụng _autoload() demo làm dữ liệu nền + auto-run optimize (giải pháp mâu thuẫn (i)) để 'vào thẳng module' luôn có số. (3) CHỈ thêm localStorage cho UI-preference (module/sidebar/bộ lọc/density), KHÔNG cache routes/finance. Persist xuống đĩa (file/DB) để 'dài hạn', chỉ làm nếu người dùng xác nhận cần dữ liệu sống qua restart.
- Lý do: Không hứa hành vi mà tầng dữ liệu không hỗ trợ. Cache dữ liệu nghiệp vụ ở client là phản pattern (số liệu tài chính lệch nguồn chân lý = rủi ro ra quyết định sai). UI-preference localStorage là an toàn, rẻ, đúng kỳ vọng 'quay lại đúng chỗ' mà không đụng tính toàn vẹn dữ liệu.

**#3. S3: GIẢM border-radius 12px → ~8px toàn cục ↔ S1/S2: GIỮ --radius:12px cho card/kpi, chỉ chuẩn hóa ~12 giá trị literal lẻ về thang token 3 cấp (sm8/md10/lg12/xl16)**
- Mâu thuẫn: Giá trị radius nền + cách xử lý các literal radius hỗn loạn (3,5,6,7,8,9,10,11,12,14,16px).
  - Product Designer: 12px cho card/kpi mềm mà vẫn chắc, phù hợp B2B mật độ cao; hạ đại trà xuống 8 làm card to trông cứng/mỏng, mất cảm giác 'control tower' cao cấp.
  - Lead Frontend: Vấn đề THẬT không phải 12 quá lớn mà là ~12 giá trị radius lẫn lộn (đã xác minh: card var(--radius)=12px dòng 69, btn 9px:38, btn-sm 7px:45, field 8px:110, modal 14px:166, dock 16px:192, badge 6px:99, tag 5px:105). Hạ toàn cục về 8 buộc sửa hàng loạt literal, dễ sót gây lệch.
  - Lead UI/UX: Token hóa thành scale là việc kỷ luật hệ thống thiết kế; giữ 12 cho bề mặt lớn, các phần tử nhỏ (badge/tag/chip) dùng cấp nhỏ hơn theo thang.
- ✅ Khuyến nghị: GIỮ --radius:12px cho card/kpi. Chuẩn hóa thành thang token 4 cấp: --r-sm:8px (field/chip/indicator), --r-md:10px (tbl-wrap/map/opt/play), --r:12px (card/kpi), --r-lg:14px (modal), --r-xl:16px (dock-panel). Find-replace các literal lẻ về thang, KHÔNG hạ giá trị nền.
- Lý do: Đẳng cấp sản phẩm đến từ tính nhất quán (token scale), không từ con số radius nhỏ hơn. Giữ 12 bảo toàn cảm nhận thương hiệu hiện có (đề bài cấm thay đổi nhận diện ở mức tinh chỉnh), trong khi token hóa loại bỏ sự hỗn loạn thực sự gây 'thiếu kỷ luật thị giác'.

**#4. S1/S4: TĂNG độ sâu — shadow 2 lớp ám navy + hover-lift (translateY) cho card ↔ S3: GIẢM shadow, dùng border + nền nhẹ thay nhiều bóng đổ**
- Mâu thuẫn: Hướng elevation (token --shadow-*) + có/không hover-lift transform, ảnh hưởng độ nặng thị giác.
  - Lead UI/UX: Hiện --shadow .06 alpha gần vô hình (dòng 18); card #FFF trên nền #F4F7FB chênh sáng chỉ ~1.07:1 → trang 'phẳng đều', không tách khối. Cần TĂNG NHẸ độ sâu để có phân tầng.
  - Product Designer (theo S3): Quá nhiều bóng đổ làm rối; border + nền tint nhẹ sạch hơn cho control tower.
  - A11y/Perf (cảnh báo kỹ thuật): hover translateY trên card BỌC Leaflet/Chart.js (#map/#bk-map/#inc-map/canvas dòng 115) làm NHÒE tile/canvas — đã được S2 cảnh báo. Tuyệt đối không transform các card này.
  - Lead Frontend: --shadow-l hiện dùng chung 4 ngữ cảnh; cần token elevation phân cấp.
- ✅ Khuyến nghị: Điểm giữa: TĂNG shadow lên 2 lớp tinh tế ám navy (vd --shadow:0 1px 3px rgba(11,61,145,.06), 0 4px 12px rgba(11,61,145,.05)) để tách khối — KHÔNG dùng border thay thế (mâu thuẫn với việc giữ shadow). Hover-lift translateY(-2px) CHỈ áp cho .kpi/.opt/.preset; với .card chứa Leaflet/canvas chỉ đổi box-shadow khi hover, KHÔNG transform. Guard prefers-reduced-motion.
- Lý do: Hiện trạng quá phẳng (xác minh chênh sáng card/nền ~1.07:1) cần tăng nhẹ độ sâu để có hierarchy — đây là điều S3 chưa thấy. Nhưng giữ tinh tế (ám navy, 2 lớp mảnh) để không 'loè loẹt' đúng tinh thần S3. Ngoại lệ transform cho card map/canvas là ràng buộc kỹ thuật cứng, không thương lượng.

**#5. S4: TOPBAR đổi nền trắng → NAVY GRADIENT linear-gradient(navy-d,navy), chữ/logo trắng ↔ S1/S3: GIỮ topbar nền sáng (#fff)**
- Mâu thuẫn: Nền topbar — ảnh hưởng độ nặng thị giác đầu trang, tương phản các control, và nhận diện brand.
  - Lead UI/UX: Khung trái ĐÃ navy đặc (sidebar active background:var(--navy) dòng 53 + logo navy dòng 31 + nhiều chip/nút navy). Thêm topbar navy làm giao diện 'nặng đầu', mất khoảng thở.
  - A11y/Perf: chip-ai (.chip nền blue-l chữ navy dòng 35) và nút .btn-line (nền trắng dòng 44) đang thiết kế cho nền sáng — đặt trên navy gradient sẽ FAIL contrast, buộc làm lại toàn bộ control topbar = phát sinh nợ a11y mới.
  - Product Designer: Control tower B2B chuộng nền sáng trung tính để DỮ LIỆU là nhân vật chính; chip trạng thái phiên (cần đọc liên tục) đọc tốt nhất trên nền sáng.
  - Lead Frontend: .topbar background:#fff border-bottom 1px (dòng 29) — đổi gradient kéo theo sửa hàng loạt selector con.
- ✅ Khuyến nghị: GIỮ topbar nền sáng (#fff). Nếu muốn điểm nhấn brand: thay border-bottom 1px xám bằng viền dưới navy 2px mảnh (đề xuất khi người dùng đồng ý) — KHÔNG phủ gradient. Loại đề xuất topbar navy.
- Lý do: Đề bài yêu cầu 'chỉ đánh bóng, giữ nhận diện' — phủ mảng navy lớn là thay đổi lớn chứ không phải tinh chỉnh. Lợi ích thẩm mỹ không bù rủi ro: nặng thị giác + buộc sửa contrast hàng loạt control (nợ a11y) + làm chip trạng thái khó đọc. Khung trái đã đủ navy để giữ nhận diện.

**#6. S2/S4: COUNT-UP số KPI chạy từ 0 lên (~1s, 'cảm giác hệ thống tính toán mạnh mẽ'), gồm cả số tài chính ↔ S1/S2: số tài chính cần đọc CHÍNH XÁC tức thì + tabular-nums + prefers-reduced-motion**
- Mâu thuẫn: Animate count-up vs đọc số chính xác — đặc biệt với số tiền/biên lợi nhuận dưới áp lực thời gian.
  - S4: count-up tạo cảm giác hệ thống mạnh mẽ, tăng 'wow' khi trình diễn dự thi.
  - A11y/Perf: vi phạm WCAG 2.3.3 nếu không guard reduced-motion; .kpi .val (dòng 81) chưa có tabular-nums → count-up bây giờ sẽ GIẬT layout ngang. Hiện file KHÔNG có khối prefers-reduced-motion nào (đã xác minh grep rỗng) và .pulse chạy infinite (dòng 190-191).
  - Lead UI/UX: số tiền nhảy từ 0 lên trong ~1s dễ bị đọc nhầm giá trị trung gian ngay khoảnh khắc dispatcher liếc → hại quyết định P&L.
  - Product Designer: STATE có cả số đếm (xe/đơn/km) lẫn số tài chính (profit/margin) — phải tách loại.
- ✅ Khuyến nghị: Count-up CHỈ cho số ĐẾM NGUYÊN (số xe, đơn đã/chưa gán, km) và tốt nhất chỉ 1 KPI 'hero' mỗi màn. TUYỆT ĐỐI KHÔNG count-up tiền/biên lợi nhuận (hiển thị tức thì). BẮT BUỘC kèm: (a) font-variant-numeric:tabular-nums cho .kpi .val/.kv trước (chống giật ngang), (b) @media(prefers-reduced-motion:reduce) hiện ngay số cuối.
- Lý do: Số tài chính count-up hại trực tiếp người vận hành đọc nhanh dưới áp lực + vi phạm reduced-motion. tabular-nums là điều kiện tiên quyết kỹ thuật (đã xác minh thiếu). Giới hạn count-up vào số đếm + 1 hero giữ được hiệu ứng 'wow' cho dự thi mà không hi sinh tính chính xác.

**#7. S2 rank11: GIỮ 2 grid KPI (8 thẻ) + gắn nhãn cụm ('Kết quả gán' / 'Quãng đường & tài chính') ↔ S2 rank42 (tự mâu thuẫn): GỘP 2 grid thành 1 lưới liền mạch / S3: tối đa 4 KPI mỗi màn / Người dùng #1: 'gộp 2 thẻ'**
- Mâu thuẫn: Số lượng & cách trình bày 8 KPI ở M3 — mâu thuẫn 3 chiều (S2 tự mâu thuẫn nội bộ, lệch S3, và người dùng muốn gộp).
  - A11y/Perf + Lead UI/UX (giữ 8): dispatcher cần cả 8 số để ra quyết định ngay (xe dùng/đơn gán/chưa gán/standby + km/km rỗng/DT-CP/lợi nhuận). Cắt còn 4 (S3) GIẤU số vận hành quan trọng (km rỗng % = chỉ số tối ưu cốt lõi, standby, biên LN) → hại.
  - Product Designer (theo người dùng #1): người dùng muốn 'gộp' — nghiêng về 1 lưới liền mạch nhưng GIỮ nhãn cụm (.sec-label) để vẫn có phân tầng ngữ nghĩa.
  - Lead Frontend (hồi quy): hai grid hiện là #plan-kpis (dòng 359) + #plan-kpis2 (360), gán JS tại applyPlan (4 thẻ + 4 thẻ). Nếu GỘP phải xóa CẢ lệnh gán #plan-kpis2 (dòng 795) VÀ dòng reset 776 ('#plan-kpis2').innerHTML='' — nếu không innerHTML ghi vào phần tử không còn = lỗi null.
- ✅ Khuyến nghị: GIỮ 8 thẻ (không cắt còn 4). Dung hòa: gộp 2 grid về 1 lưới liền mạch theo ý người dùng NHƯNG thêm .sec-label nhãn cụm + nâng 1 thẻ Lợi nhuận thành hero (cls 'green hero', .val 28px) làm điểm neo. Nếu giữ 2 grid riêng cũng chấp nhận được — quyết định cuối thuộc chủ sản phẩm (xem clarification). Bắt buộc dọn hồi quy nếu gộp (xóa gán + reset #plan-kpis2).
- Lý do: Control tower là bài toán mật-độ-cao CÓ CHỦ ĐÍCH, khác dashboard tiêu dùng — cắt 4 thẻ giấu dữ liệu ra-quyết-định. Người dùng muốn 'bớt ngợp' chứ không muốn mất số; giải pháp đúng là phân tầng (nhãn cụm + hero) chứ không cắt. Cảnh báo hồi quy #plan-kpis2 là bẫy phá JS đã xác minh.

**#8. S4: thêm landing 'TỔNG QUAN / Dashboard' làm màn vào đầu tiên (KPI gộp + chart mini + sự cố gấp) ↔ S3/Người dùng: 'next-best-action' khi mở app + tinh thần 'giảm số module, đừng thêm thứ tranh trung tâm'**
- Mâu thuẫn: Thêm 1 màn mới vs mục tiêu định hướng ở trạng thái trống — và liên hệ với stateless.
  - S4: landing Dashboard cho cảm giác 'control tower' chuyên nghiệp ngay khi vào.
  - Lead Frontend (code): khi mở app, _autoload() nạp demo (app.py:209) nhưng _routes/_financial=None (app.py:272); /api/plan trả has_plan:false routes:[] tới khi optimize. → Dashboard landing sẽ RỖNG nếu không tự chạy optimize.
  - Lead UI/UX: ở trạng thái trống, một Dashboard rỗng phản tác dụng 'next-best-action'; thanh stepper (đã đề xuất) phục vụ mục tiêu định hướng tốt hơn với công sức thấp hơn nhiều.
  - Product Designer: nếu vẫn muốn Dashboard, phải cho nó tự chạy optimize ngầm (kết nối với giải pháp mâu thuẫn (i)) hoặc chấp nhận vỏ rỗng có CTA.
- ✅ Khuyến nghị: KHÔNG thêm landing Dashboard riêng trong đợt này (loại theo mặc định). Thay bằng THANH QUY TRÌNH (stepper) cố định đầu vùng nội dung — phục vụ next-best-action tốt hơn ở trạng thái trống, công thấp, không thêm module. Nếu chủ sản phẩm vẫn muốn cảm giác control-tower, cân nhắc auto-run optimize khi vào để Dashboard có số (đội thêm độ phức tạp).
- Lý do: Stepper và landing Dashboard phục vụ mục tiêu gần giống nhau; stepper rẻ hơn nhiều và không tạo màn rỗng phản tác dụng. Thêm module mới đi ngược tinh thần 'giảm thứ tranh trung tâm' của S3. Sự thật code (routes=None khi mở) khiến Dashboard rỗng trừ khi auto-run — chi phí/lợi ích không thuyết phục so với stepper.

**#9. S1: sidebar '6 bước ĐÁNH SỐ + 1 nhóm Cài đặt' (giữ ẩn dụ quy trình tuần tự) ↔ S3: sidebar nhóm theo CHỨC NĂNG (Dữ liệu/Điều phối/Tối ưu/Vận hành/Cấu hình, không đánh số) — và S4: 5 tab lớn có tab con**
- Mâu thuẫn: Mô hình IA sidebar — 3 biến thể khác nhau cho cùng mục tiêu 'giảm 9 mục, bớt ngợp'.
  - S1: giữ đánh số bước khớp ẩn dụ quy trình + thanh stepper + ghi chú người dùng 'tự làm theo bước'.
  - S3: nhóm theo chức năng phản ánh mô hình tư duy dispatcher hơn cấu trúc kỹ thuật 'Module 1,2,3…'.
  - S4: 5 tab lớn + tab nội bộ — gọn nhất nhưng cần refactor cơ chế view (nav toggle theo id view-*) + thêm lớp tab nội bộ = nhiều rủi ro hồi quy.
  - Lead Frontend: sidebar hiện 9 mục/3 nhóm (dòng 230-241); đánh số bước đã có (.num). Gộp sâu (5 tab) cần refactor nav() + thêm tab logic; gộp nông (gộp mục trùng) rẻ và an toàn hơn.
- ✅ Khuyến nghị: Hợp nhất 1 khuyến nghị: GIỮ ĐÁNH SỐ BƯỚC (khớp thanh stepper + ghi chú người dùng) NHƯNG gộp các mục trùng để giảm từ 9 → ~6-7: (1) gộp 'Bản đồ toàn mạng' vào nút mở rộng của bản đồ M3 (bỏ 1 mục); (2) gộp M6 Sự cố + M7 Nhật ký thành 'Vận hành trong ngày' với tab nội bộ; (3) chuyển 'Ràng buộc vận hành' (glyph R) sang nhóm Cấu hình/Cài đặt icon ⚙ ở đáy (giữ data-view='constraints'). KHÔNG refactor sâu 5 tab.
- Lý do: Đánh số bước củng cố thanh stepper và khớp yêu cầu 'tự làm theo bước' của người dùng. Gộp mục trùng (map, sự cố+nhật ký, ràng buộc xuống cài đặt) đạt mục tiêu 'bớt ngợp' của cả 3 nguồn mà rủi ro hồi quy thấp hơn nhiều so với 5-tab của S4 (vốn cần đập cơ chế view). Đây là điểm hội tụ thực dụng nhất.

**#10. S2: thay confirm() bằng custom modal (#confirm-modal riêng) cho mọi thao tác ↔ S4: mô hình 'Undo' qua toast (Xóa ngay → Toast 'Đã xóa. [Hoàn tác]')**
- Mâu thuẫn: Cách thay thế 6 confirm() OS — modal xác nhận trước vs thực thi ngay + hoàn tác.
  - S2: confirm() OS phá brand, không phân biệt mức nguy hiểm → modal tùy chỉnh nhấn mạnh hậu quả.
  - S4: Undo-toast mượt hơn, không chặn luồng cho thao tác thường xuyên.
  - Lead UI/UX: hai hướng BỔ TRỢ, không loại trừ — phân theo mức nguy hiểm/khả hồi.
  - Lead Frontend (code): 6 confirm() đã xác minh: dòng 715 (xóa 1 đơn — NHẸ/khả hồi), 1226 (áp dụng phương án P&L — NẶNG), 1237/1244 (hoàn tất sự cố — NẶNG), 1286 (xóa 1 dòng log — NHẸ), 1290 (xóa TOÀN BỘ log kiểm toán — NẶNG nhất). LƯU Ý: dòng 1290 hiện cảnh báo YẾU HƠN dòng 1286 ('Xóa toàn bộ nhật ký?' vs '...không thể hoàn tác') dù hậu quả nặng hơn — sai phân cấp.
- ✅ Khuyến nghị: PHỐI HỢP cả hai theo mức: (A) Thao tác NẶNG/không hoàn tác (xóa TOÀN BỘ nhật ký kiểm toán 1290, áp dụng phương án P&L 1226, hoàn tất sự cố 1237/1244) → confirmBox() = #confirm-modal RIÊNG (KHÔNG tái dùng #modal/#route-modal tránh xung đột trạng thái), nêu rõ hậu quả + số lượng + 'KHÔNG THỂ hoàn tác'. (B) Thao tác NHẸ/khả hồi (xóa 1 đơn 715, xóa 1 dòng log 1286) → thực thi ngay + toast 'Đã xóa. [Hoàn tác]'. Đồng thời SỬA microcopy dòng 1290 (đang yếu hơn 1286).
- Lý do: Best practice: mức độ ma sát phải tương xứng mức nguy hiểm — modal cho hành động phá hủy không hồi phục, undo-toast cho hành động thường xuyên khả hồi. Hai cơ chế bổ trợ chứ không xung đột. confirmBox phải là modal riêng (đã xác minh #modal/#route-modal dùng cho mục đích khác). Việc dòng 1290 cảnh báo yếu hơn 1286 là bug phân cấp thật cần sửa ngay.

### Cần làm rõ (panel)
1. **Phạm vi stateless & persist dữ liệu** — Khi anh nói 'đã lưu trên hệ thống thì vào thẳng module bất kỳ', anh muốn dữ liệu (đơn đã sửa, kế hoạch tuyến, P&L) tồn tại QUA việc restart server / đóng trình duyệt không? Hiện STORE chỉ ở RAM (app.py:66-83), mất sạch khi restart, và routes/financial = None tới khi chạy optimize. Anh cần lưu xuống đĩa (file/DB) hay chỉ giữ trong phiên chạy là đủ? _(vì sao: Quyết định có cần xây lớp persistence mới (đáng kể) hay chỉ dùng auto-run optimize + localStorage UI-preference. Ảnh hưởng trực tiếp tới giải pháp mâu thuẫn stateless và khối lượng công việc.)_
2. **Hành vi khi vào M4/M5 mà chưa có kế hoạch** — Khi dispatcher bấm thẳng vào Tài chính/Ghép chiều về mà chưa lập tuyến, anh muốn (a) hệ thống TỰ chạy lập tuyến ngầm rồi hiện kết quả tài chính (kèm toast 'Đang lập tuyến…'), hay (b) hiện empty-state 'Chưa có kế hoạch, bấm để lập' để anh tự quyết? Lưu ý: tài chính tính TỪ tuyến (app.py:877) nên không có tuyến thì không có số để hiện. _(vì sao: Đây là cốt lõi của việc tôn trọng stateless mà không trả màn lỗi. Quyết định (a) hay (b) định hình toàn bộ luồng M4/M5 và trải nghiệm 'bấm đâu cũng được'.)_
3. **Số KPI ở M3 (8 vs 4 vs gộp 1 lưới)** — Khi điều phối thực tế, anh có cần nhìn đồng thời cả 8 chỉ số (xe dùng / đơn gán / chưa gán / standby + tổng km / km rỗng / DT-CP / lợi nhuận) ngay khi vừa chạy tối ưu không? Và anh muốn (A) giữ 2 grid có nhãn cụm, (B) gộp 1 lưới liền mạch + nhãn cụm + 1 thẻ hero, hay (C) 4 số kết quả gán đủ rồi, 4 số tài chính để ở M5? _(vì sao: S2 tự mâu thuẫn nội bộ (giữ 8 vs gộp), S3 muốn cắt 4, người dùng muốn 'gộp 2 thẻ'. Hội đồng khuyến nghị giữ 8 nhưng cần chủ sản phẩm chốt vì ảnh hưởng cả thông tin ra-quyết-định lẫn rủi ro hồi quy JS (#plan-kpis2).)_
4. **Mô hình sidebar cuối cùng** — Anh chọn mô hình sidebar nào: (A) giữ đánh số bước 1→6 + nhóm Cài đặt, gộp các mục trùng (khuyến nghị của hội đồng); (B) gom theo nhóm chức năng Dữ liệu/Điều phối/Tối ưu/Vận hành/Cấu hình (không đánh số); hay (C) 5 tab lớn có tab con? _(vì sao: 3 nguồn (S1/S3/S4) đề 3 mô hình khác nhau. Lựa chọn quyết định khối lượng refactor: (A) rẻ/an toàn, (C) cần đập cơ chế view = nhiều rủi ro hồi quy. Cần chốt trước khi đụng nav.)_
5. **Drawer chi tiết tuyến vs xếp dọc bảng/bản đồ** — Anh muốn xem chi tiết 1 tuyến bằng (A) panel trượt từ bên phải khi bấm dòng [bản đồ giữ nguyên vị trí], hay (B) bảng full-width trên + bản đồ dưới [phải cuộn xuống xem bản đồ]? Hai cách KHÔNG kết hợp được cho cùng màn M3. _(vì sao: Nếu chọn (B), bấm dòng bảng không thấy bản đồ phản hồi ngay (focusRoute vẫn chạy nhưng ngoài tầm nhìn). Quyết định này định hình giải pháp giảm mật độ bảng 15 cột — vấn đề người dùng than 'kéo kéo mãi khá rối'.)_
6. **Phạm vi nút fullscreen bảng & bản đồ** — Nút fullscreen (anh yêu cầu ở ghi chú #3) cần phủ KÍN toàn màn hình (ẩn cả sidebar/topbar) hay chỉ phóng to card trong vùng nội dung? Phủ toàn màn cho bản đồ thường tiện hơn nhưng cần nút thoát rõ ràng (Esc). _(vì sao: Ảnh hưởng cách triển khai (class .fs position:fixed inset:0 vs phóng trong content) và việc bắt buộc gọi map.invalidateSize() sau resize. Cũng quyết định độ phức tạp focus/Esc.)_
7. **TOOL AI — cấu hình real-time hiện tại** — Máy chạy demo đã có GEMINI_API_KEY và FUEL_PRICE_URL trong file .env chưa? (Hiện thư mục KHÔNG có file .env, chỉ có .env.example; GEMINI_API_KEY không set trong shell.) Nếu chưa cấu hình, trợ lý đang chạy chế độ offline (_offline_assistant, gemini_ai.py:539) và giá dầu dùng fallback 30020 (fuel_price.py:36) — ĐÂY là lý do cảm giác 'cố định', KHÔNG phải do code hard-code. _(vì sao: Yêu cầu 'AI search real-time, không cố định 30020' phần lớn ĐÃ có sẵn trong code (fuel_price.py crawl Petrolimex + cache; gemini_ai.py:117 bật google_search khi web=True). Cái thiếu là API key + minh bạch nguồn trên UI, KHÔNG phải viết lại tool. Cần xác nhận để tránh làm lại thừa và rủi ro hồi quy.)_
8. **TOOL AI — danh mục câu hỏi vàng về đơn** — Anh liệt kê giúp 8-12 câu hỏi cụ thể dispatcher hay hỏi về 1 đơn (vd: 'đơn X gồm những gì', 'đơn X gán xe nào, ETA bao nhiêu', 'vì sao đơn X chưa gán', 'đơn X lãi/lỗ bao nhiêu', 'đơn X có ghép chiều về được không', 'sự cố ảnh hưởng đơn X thế nào')? Có danh mục này em mới viết được hàm get_order_detail(store, order_id) + bộ test snapshot đảm bảo 'KHÔNG thiếu/sai trường nào'. _(vì sao: Đây là GAP THẬT đã xác minh: get_route_context (gemini_ai.py:296-323) chỉ truyền 'don': r.get('orders') = list mã đơn, KHÔNG có chi tiết từng đơn (trọng lượng/thể tích/khung giờ/tọa độ/doanh thu/cấm tải). 'TẤT CẢ câu hỏi' là vô hạn — không có danh mục thì không thể chứng minh phủ 100% trường dữ liệu.)_
9. **TOOL AI — phạm vi real-time ngoài giá dầu** — Ngoài giá dầu, anh có muốn AI tra cứu real-time loại dữ liệu mở nào khác không (tin cấm đường/cấm tải theo địa phương, thời tiết tuyến, tỷ giá/phụ phí)? Nếu có, cần nguồn ưu tiên để quyết định dùng google_search grounding (đã có) hay viết crawler riêng như fuel_price. _(vì sao: Nếu chỉ là giá dầu thì coi như đã xong (pipeline đã có). Nếu mở rộng, quyết định kiến trúc (grounding sẵn vs crawler mới) và khối lượng công việc.)_
10. **Hiển thị nguồn AI/giá dầu (badge minh bạch)** — Anh có muốn mỗi câu trả lời AI và mỗi lần hiện giá dầu đều kèm badge nguồn + thời điểm cập nhật (vd 'Trực tuyến · Gemini · 19/06 14:20' / 'Trợ lý AI · dữ liệu phiên') để chứng minh tính real-time không? _(vì sao: Backend đã trả 'source' ở mọi câu trả lời (app.py:1240) và get_fuel_price_for_ai trả nguon/trang_thai/cap_nhat_luc (fuel_price.py:195). Niềm tin vào 'real-time' đến từ việc THẤY nguồn — chỉ cần frontend render badge, rẻ và tăng độ tin cậy cho dự thi.)_
11. **Cỡ H2 tiêu đề trang** — H2 tiêu đề module nên giữ 20px (S1/S3) hay nâng lên 24px tracking -0.5px (S4)? 24px tạo phân cấp mạnh hơn nhưng đẩy page-head cao thêm, ảnh hưởng nhịp dọc trên màn hẹp. _(vì sao: Ảnh hưởng chiều cao page-head và nhịp dọc toàn site; cần chốt 1 giá trị để token hóa thang typography sạch.)_

### Đề xuất loại bỏ (panel)
1. **Wizard/stepper ÉP THỨ TỰ + KHÓA cứng (Disable) module M4/M5 khi chưa chạy M3 (S2 rank6, S4)** [Loại hẳn] — Đi ngược yêu cầu trực tiếp của chủ sản phẩm (ghi chú #4: 'ai quan tâm gì bấm đấy, không bắt chạy optimize rồi mới ra tài chính') và ngược best-practice cho công cụ vận hành dùng cả ngày — người dùng thành thạo bị chặn ở thao tác họ hiểu rõ. Phụ thuộc dữ liệu là THẬT (finance cần routes, đã xác minh app.py:870-877) nhưng giải pháp đúng là TỰ CHẠY tiền đề ngầm (auto-run optimize, _run_optimize app.py:505 tái dùng được) + hiển thị trạng thái qua stepper bấm-được, KHÔNG khóa cứng. Khóa cứng biến lỗi-dữ-liệu thành rào-cản-điều-hướng.
2. **Khóa module bằng .nav-item.locked{pointer-events:none} + glyph 🔒 (S2 rank6)** [Loại hẳn] — pointer-events:none khiến mục KHÔNG focus được bằng bàn phím và bị một số screen reader bỏ qua → mâu thuẫn CHÍNH mục tiêu a11y rank1 của chính S2. Người dùng bàn phím không hiểu vì sao bấm không được. Nếu cần báo phụ thuộc, dùng aria-disabled + thông báo trạng thái (vẫn truy cập/focus được, bấm thì tự chạy tiền đề), KHÔNG chặn cứng.
3. **Count-up animation cho số TÀI CHÍNH / P&L (S4: 'từ 0 lên trong ~1s')** [Loại theo mặc định (cho phép tùy chọn)] — Animate số tiền/biên lợi nhuận từ 0 lên tạo giá trị trung gian sai lệch trong ~1s, gây đọc nhầm cho dispatcher liếc nhanh dưới áp lực thời gian — hại quyết định P&L. Vi phạm prefers-reduced-motion nếu không guard (đã xác minh file chưa có khối reduced-motion nào) và .kpi .val chưa có tabular-nums (dòng 81) nên sẽ giật layout ngang. Chỉ chấp nhận count-up cho số ĐẾM nguyên (xe/đơn/km) ở 1 KPI hero, có guard reduced-motion + tabular-nums.
4. **TOPBAR đổi sang navy gradient nền tối chữ trắng (S4)** [Loại hẳn] — Khung trái đã navy đặc (sidebar active dòng 53 + logo dòng 31 + nhiều nút navy). Phủ thêm navy lên topbar làm 'nặng đầu', mất khoảng thở, và phát sinh nợ contrast mới: chip-ai (.chip nền blue-l chữ navy dòng 35) + nút .btn-line (nền trắng dòng 44) đang thiết kế cho nền sáng sẽ FAIL trên navy, buộc làm lại toàn bộ control topbar — ngược tinh thần 'chỉ đánh bóng, giữ nhận diện'. Control tower B2B chuộng nền sáng để dữ liệu là nhân vật chính. Thay bằng viền dưới navy 2px mảnh nếu cần điểm nhấn.
5. **GIẢM đại trà border-radius 12px → 8px toàn cục (S3)** [Loại theo mặc định (cho phép tùy chọn)] — Hạ toàn cục về 8 khiến card mật-độ-cao trông cứng/mỏng và buộc sửa hàng loạt ~12 literal radius (đã xác minh: dòng 31/38/45/69/99/105/110/166/192...), dễ sót gây lệch. Vấn đề THẬT không phải 12 quá lớn mà là sự hỗn loạn ~12 giá trị. Giải đúng là chuẩn hóa thành thang token và GIỮ 12 cho card/kpi.
6. **Cắt M3 KPI xuống tối đa 4 chỉ số (S3) — bỏ 4 thẻ còn lại** [Loại theo mặc định (cho phép tùy chọn)] — Cắt cứng còn 4 giấu các số vận hành quan trọng dispatcher cần để ra quyết định ngay: km rỗng % (chỉ số tối ưu cốt lõi), xe standby (mục tiêu 3-5 xe), lợi nhuận/biên. Control tower là bài toán mật-độ-cao CÓ CHỦ ĐÍCH, khác dashboard tiêu dùng. Đúng hơn: GIỮ 8 thẻ nhưng phân tầng (nhãn cụm + 1 thẻ hero) để có điểm neo — đạt 'bớt ngợp' mà không mất dữ liệu.
7. **Thêm landing 'Tổng quan/Dashboard' làm màn vào đầu tiên (S4)** [Loại theo mặc định (cho phép tùy chọn)] — Khi mở app, _routes/_financial=None (app.py:272), /api/plan trả routes:[] tới khi optimize → Dashboard landing sẽ RỖNG, phản tác dụng 'next-best-action'. Thanh stepper phục vụ mục tiêu định hướng tốt hơn ở trạng thái trống với công sức thấp hơn nhiều, và không thêm module mới (ngược tinh thần 'giảm thứ tranh trung tâm'). Chỉ cân nhắc nếu chấp nhận auto-run optimize khi vào (đội thêm phức tạp).
8. **Refactor sidebar sâu thành 5 tab lớn có tab con (S4)** [Loại theo mặc định (cho phép tùy chọn)] — Cần đập cơ chế view hiện tại (nav() toggle theo id view-* dòng 600-614) + thêm lớp tab nội bộ = nhiều rủi ro hồi quy cho sản phẩm dự thi. Đạt cùng mục tiêu 'giảm 9 mục' bằng cách gộp NÔNG các mục trùng (map vào nút mở rộng, sự cố+nhật ký thành tab, ràng buộc xuống cài đặt) với rủi ro thấp hơn nhiều và giữ đánh số bước theo yêu cầu người dùng.
9. **Viết lại tool giá dầu vì 'đang cố định 30020'** [Loại hẳn] — Sai hiện trạng (đã xác minh code). fuel_price.py đã là pipeline real-time đầy đủ: fetch_fuel_price crawl (dòng 118), get_price live/cache/fallback TTL (dòng 129), /api/fuel/refresh ép cập nhật + tính lại P&L. 30020 chỉ là FALLBACK_PRICE (dòng 36) khi mất mạng/chưa cấu hình nguồn. Viết lại là lãng phí + rủi ro hồi quy. Việc đúng: cấu hình FUEL_PRICE_URL/API key trong .env (hiện KHÔNG có file .env) + hiển thị nguồn/trạng thái/thời điểm trên UI.
10. **Viết lại 'tool AI search real-time' vì cho rằng chưa có** [Loại hẳn] — Sai hiện trạng. gemini_ai._call_gemini đã thêm tools=[{google_search:{}}] khi web=True (dòng 117), ask_gemini gọi web=True (dòng 451). Khi có GEMINI_API_KEY, trợ lý ĐÃ tra cứu Internet real-time. Việc còn lại KHÔNG phải code mới mà là đặt API key (hiện chạy offline _offline_assistant vì không key — đã xác minh không có .env, shell không set key) + hiển thị nhãn 'Trực tuyến · Gemini (Internet)' để người dùng tin là real-time.
11. **Nhồi TOÀN BỘ dữ liệu mọi đơn (validated + working + routes) vào mỗi prompt AI để 'chắc chắn đủ field'** [Loại hẳn] — Phản tác dụng: tăng token, chậm, tốn chi phí, làm loãng context khiến mô hình dễ sai. Cách đúng: chỉ inject chi tiết đầy đủ của ĐƠN ĐANG ĐƯỢC HỎI qua hàm get_order_detail(store, order_id) nhận diện order_id từ câu hỏi (regex), giữ context tổng quan như hiện tại. Đủ field cho đơn cần tra cứu mà không phình prompt.
12. **Density toggle (Thoải mái/Gọn) class .compact (S2)** [Loại theo mặc định (cho phép tùy chọn)] — Với sản phẩm dự thi + đã làm drawer/thu cột, density toggle là tính năng phụ làm phình phạm vi và thêm 1 trạng thái phải test trên MỌI bảng. Không sai về best practice nhưng đầu tư/lợi ích thấp ở giai đoạn tinh chỉnh này. Để 'dài hạn', làm SAU khi token hóa spacing (--sp-*) hoàn tất thì mới rẻ.
13. **Đổi màu marker trong L.divIcon sang biến CSS var() (hệ quả token hóa màu chart)** [Loại hẳn] — Có hại kỹ thuật: template string trong L.divIcon (dòng 902-904) KHÔNG nội suy CSS var — đổi #0B3D91 sang var(--navy) sẽ làm marker MẤT MÀU. Phải giữ literal hex ở 3 hàm icon này như ngoại lệ có chủ đích của hệ token. (Lưu ý: màu chart truyền qua JS array tại drawCostChart dòng 1096 thì đổi tự do được — đó là việc nên làm.)
14. **Refactor badge 'tốt' từ inline-style về class .badge (đề xuất gốc S1 #44)** [Loại hẳn] — Đã đính chính/lỗi thời: badge trong code HIỆN TẠI đã dùng class .badge + modifier (.b-ok/.b-rev/.b-err/.b-blue/.b-gray dòng 99-104) nhất quán. Không còn inline-style cần gom. Coi như đã đạt — không nên tốn công làm lại. (Việc THẬT còn lại: sửa contrast .b-rev #B07A00/#FFF6E2 = 3.47:1 FAIL AA → dùng amber tối hơn ~#8A5E00.)
