# HPL i18n EN/VI — hướng dẫn tích hợp (dành cho Codex)

## Files
```
src/i18n/vi.json                    # nguồn tiếng Việt (verbatim từ bản live)
src/i18n/en.json                    # bản dịch EN chuẩn ngành logistics
src/i18n/index.js                   # setup react-i18next (stack React)
src/i18n/i18n-vanilla.js            # fallback zero-dependency (bản standalone HTML)
src/components/LanguageSwitcher.jsx # segmented control VI | EN
src/components/LanguageSwitcher.css
public/logo-hpl.svg                 # logo HPL (navy + viền đỏ, dùng cả làm favicon)
```

## A. Stack React
1. `npm i i18next react-i18next`
2. `import "./i18n";` trong `main.jsx` / `index.js` (trước khi render App).
3. Trong header component:
```jsx
import LanguageSwitcher from "./components/LanguageSwitcher";
// ...
<div className="topbar__right">
  <AiAssistantChip />      {/* "Trợ lý AI · Trực tuyến" */}
  <LanguageSwitcher />     {/* NGAY BÊN PHẢI chip trên */}
</div>
```
4. Thay mọi chuỗi cứng bằng `t("key")` theo bảng khóa trong vi.json.

## B. Stack standalone HTML/JS
1. Thêm `<script src="src/i18n/i18n-vanilla.js"></script>` + link CSS.
2. Gắn `data-i18n="nav.step3"` (hoặc `data-i18n-placeholder` / `-title` / `-aria-label`) vào mọi node có chữ.
3. Khởi tạo:
```html
<script type="module">
  const [vi, en] = await Promise.all([
    fetch("src/i18n/vi.json").then(r => r.json()),
    fetch("src/i18n/en.json").then(r => r.json()),
  ]);
  HPLI18N.init({ vi, en });
  HPLI18N.mountSwitcher("#topbar-right");   // container chứa chip "Trợ lý AI"
</script>
```
4. Text render bằng JS: gọi `HPLI18N.t("...")` và re-render trong listener
   `document.addEventListener("hpl:languagechange", rerender)`.

## C. Logo
- Header: `<img src="/logo-hpl.svg" alt="HPL" width="32" height="32" class="topbar__logo">`
- Favicon: `<link rel="icon" type="image/svg+xml" href="/logo-hpl.svg">`

## D. Vị trí thanh ngôn ngữ (bắt buộc)
Cùng hàng với header, **bên phải** chỉ báo `Trợ lý AI · Trực tuyến`, canh giữa theo chiều dọc,
không xuống dòng. Dưới 640px chỉ hiện icon quả cầu + mã ngôn ngữ đang chọn.

## E. Quy ước khóa
`app.* nav.* assistant.* language.* actions.* order.* status.* hints.*`
Khóa mới phải thêm đồng thời vào **cả hai** file; CI fail nếu lệch khóa:
```bash
node -e "const a=require('./src/i18n/vi.json'),b=require('./src/i18n/en.json');const f=(o,p='')=>Object.entries(o).flatMap(([k,v])=>typeof v==='object'?f(v,p+k+'.'):[p+k]);const A=f(a).sort(),B=f(b).sort();const d=[...A.filter(k=>!B.includes(k)).map(k=>'EN missing '+k),...B.filter(k=>!A.includes(k)).map(k=>'VI missing '+k)];if(d.length){console.error(d.join('\n'));process.exit(1)}console.log('i18n keys OK:',A.length)"
```
