import { readFile } from "node:fs/promises";
import vm from "node:vm";

const code = await readFile("site-data.js", "utf8");
const context = { window: {} };
vm.runInNewContext(code, context);

const pages = context.window.PDS_SITE_DATA?.pages || [];
const byFile = new Map(pages.map(page => [page.file, page]));
const expectedWeek3Start = "2026-05-15";
const expectedWeek3Files = [
  "0515_1_head-injury.html",
  "0518_1_aromatherapy-theory-practice.html",
  "0519_1_clinical-preventive-medicine-health-screening.html",
  "0520_1_integrative-medicine-overview-status.html",
  "0521_1_comparative-healthcare-systems.html"
];

const failures = [];
for (const file of expectedWeek3Files) {
  const page = byFile.get(file);
  if (!page) {
    failures.push(`${file}: missing`);
  } else if (page.weekKey !== expectedWeek3Start) {
    failures.push(`${file}: expected ${expectedWeek3Start}, got ${page.weekKey}`);
  }
}

if (failures.length) {
  console.error("Week 3/4 merge check failed:");
  console.error(failures.join("\n"));
  process.exit(1);
}

console.log("Week 3/4 merge verified.");
