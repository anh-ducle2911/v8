import fs from "node:fs";

const vi = JSON.parse(fs.readFileSync(new URL("../src/i18n/vi.json", import.meta.url), "utf8"));
const en = JSON.parse(fs.readFileSync(new URL("../src/i18n/en.json", import.meta.url), "utf8"));

function flatten(value, prefix = "") {
  return Object.entries(value).flatMap(([key, child]) => {
    const path = `${prefix}${key}`;
    return child && typeof child === "object" ? flatten(child, `${path}.`) : [path];
  });
}

const viKeys = flatten(vi).sort();
const enKeys = flatten(en).sort();
const errors = [
  ...viKeys.filter((key) => !enKeys.includes(key)).map((key) => `EN missing ${key}`),
  ...enKeys.filter((key) => !viKeys.includes(key)).map((key) => `VI missing ${key}`),
];

if (errors.length) {
  console.error(errors.join("\n"));
  process.exit(1);
}

console.log("i18n keys OK:", viKeys.length);
