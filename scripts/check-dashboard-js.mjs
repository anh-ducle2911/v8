import fs from "node:fs";
import vm from "node:vm";

const html = fs.readFileSync(new URL("../templates/dashboard.html", import.meta.url), "utf8");
const blocks = [...html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/gi)]
  .map((match) => match[1])
  .filter((source) => source.trim());

blocks.forEach((source, index) => {
  new vm.Script(source, { filename: `dashboard-inline-${index + 1}.js` });
});

console.log("dashboard inline scripts syntax OK:", blocks.length);
