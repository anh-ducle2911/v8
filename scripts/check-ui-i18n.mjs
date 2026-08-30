import fs from "node:fs";

const html = fs.readFileSync(new URL("../templates/dashboard.html", import.meta.url), "utf8");
const vi = JSON.parse(fs.readFileSync(new URL("../src/i18n/vi.json", import.meta.url), "utf8"));

function flattenValues(value, prefix = "", out = new Map()) {
  for (const [key, child] of Object.entries(value)) {
    const path = prefix ? `${prefix}.${key}` : key;
    if (child && typeof child === "object") flattenValues(child, path, out);
    else if (typeof child === "string" && !out.has(child)) out.set(child, path);
  }
  return out;
}

function get(path) {
  return path.split(".").reduce((value, key) => value?.[key], vi);
}

const declared = [...html.matchAll(/data-i18n(?:-placeholder|-title|-aria-label|-document-title)?="([^"]+)"/g)]
  .map((match) => match[1]);
const missing = [...new Set(declared.filter((key) => get(key) === undefined))];
if (missing.length) {
  console.error(missing.map((key) => `Missing declared key ${key}`).join("\n"));
  process.exit(1);
}

const chip = html.indexOf('id="chip-ai"');
const switcher = html.indexOf('id="i18n-switcher-anchor"');
if (chip < 0 || switcher < chip) throw new Error("Language switcher must be immediately after the AI status chip");
if (!html.includes('src="/logo-hpl.svg"') || !html.includes('href="/logo-hpl.svg"')) {
  throw new Error("HPL header logo and favicon are required");
}
if (!html.includes("/api/export?lang=")) throw new Error("Excel export must pass the active language");

const valueKeys = flattenValues(vi);
const hardcoded = [...html.matchAll(/<([a-z][\w-]*)([^>]*)>([^<>]+)<\/\1>/gi)]
  .filter(([, tag, attrs, text]) => !/^(script|style|textarea)$/i.test(tag)
    && !/\bdata-i18n(?:=|\s)/.test(attrs)
    && valueKeys.has(text.trim()))
  .map(([, tag, , text]) => `<${tag}> ${JSON.stringify(text.trim())} (${valueKeys.get(text.trim())})`);
if (hardcoded.length) {
  console.error(hardcoded.map((item) => `Hardcoded declared-value text: ${item}`).join("\n"));
  process.exit(1);
}

console.log("UI i18n declarations OK:", declared.length);
