import { readFile, readdir, writeFile } from "node:fs/promises";
import path from "node:path";

const root = process.cwd();
const configPath = path.join(root, "site.config.json");
const outPath = path.join(root, "site-data.js");
const weekdayLabels = ["일", "월", "화", "수", "목", "금", "토"];

const config = JSON.parse(await readFile(configPath, "utf8"));
const year = Number(config.academicYear) || new Date().getFullYear();
const entries = await readdir(root, { withFileTypes: true });
const htmlFiles = entries
  .filter(entry => entry.isFile() && entry.name.toLowerCase().endsWith(".html"))
  .map(entry => entry.name)
  .filter(file => !["index.html", "404.html"].includes(file.toLowerCase()));

const invalidFiles = htmlFiles.filter(file => !isValidPageFileName(file));
if (invalidFiles.length) {
  throw new Error([
    "Invalid HTML page filenames:",
    ...invalidFiles.map(file => `- ${file}`),
    "",
    "Use: MMDD_period_english-slug.html",
    "Example: 0511_2_public-health-policy.html"
  ].join("\n"));
}

const pages = [];
for (const file of htmlFiles) {
  const parsed = parseFileName(file);
  if (!parsed) continue;

  const html = await readFile(path.join(root, file), "utf8");
  const title = extractTitle(html) || parsed.fallbackTitle;
  const professor = getProfessor(file, html, title, config);
  const dateInfo = getDateInfo(year, parsed.month, parsed.day);
  const periods = config.periods || [];
  const span = getPageSpan(file, config);

  pages.push({
    file,
    title,
    professor,
    tag: professor,
    dateKey: dateInfo.dateKey,
    dateLabel: dateInfo.dateLabel,
    weekday: dateInfo.weekday,
    weekKey: dateInfo.weekKey,
    period: parsed.period,
    endPeriod: parsed.period + span - 1,
    span,
    periodLabel: getPeriodLabel(parsed.period, span, periods)
  });
}

pages.sort((a, b) => a.dateKey.localeCompare(b.dateKey) || Number(a.period) - Number(b.period) || a.title.localeCompare(b.title, "ko"));

const payload = {
  generatedAt: new Date().toISOString(),
  config,
  pages
};

await writeFile(outPath, `window.PDS_SITE_DATA = ${JSON.stringify(payload, null, 2)};\n`, "utf8");
console.log(`Generated site-data.js with ${pages.length} pages.`);

function parseFileName(file) {
  const match = file.match(/^(\d{2})(\d{2})_(\d+)_([a-z0-9]+(?:-[a-z0-9]+)*)\.html$/u);
  if (!match) return null;
  const [, month, day, period, rawTitle] = match;
  return {
    month: Number(month),
    day: Number(day),
    period: Number(period),
    fallbackTitle: cleanupText(rawTitle.replace(/[_-]+/g, " "))
  };
}

function isValidPageFileName(file) {
  return /^\d{4}_[1-9]\d*_[a-z0-9]+(?:-[a-z0-9]+)*\.html$/.test(file);
}

function extractTitle(html) {
  const h1 = html.match(/<h1\b[^>]*>([\s\S]*?)<\/h1>/i)?.[1];
  const title = html.match(/<title\b[^>]*>([\s\S]*?)<\/title>/i)?.[1];
  return cleanupText(h1 || title || "");
}

function cleanupText(value) {
  return decodeEntities(String(value || "")
    .replace(/<br\s*\/?>/gi, " ")
    .replace(/<[^>]+>/g, " ")
    .replace(/\s+/g, " ")
    .trim());
}

function decodeEntities(value) {
  const named = {
    amp: "&",
    lt: "<",
    gt: ">",
    quot: "\"",
    apos: "'",
    nbsp: " "
  };
  return value.replace(/&(#x?[0-9a-f]+|[a-z]+);/gi, (entity, body) => {
    if (body[0] === "#") {
      const isHex = body[1]?.toLowerCase() === "x";
      const codePoint = Number.parseInt(body.slice(isHex ? 2 : 1), isHex ? 16 : 10);
      return Number.isFinite(codePoint) ? String.fromCodePoint(codePoint) : entity;
    }
    return named[body.toLowerCase()] || entity;
  });
}

function getProfessor(file, html, title, siteConfig) {
  const explicit = siteConfig.pageProfessors?.[file];
  if (explicit) return explicit;

  const text = `${title} ${file} ${cleanupText(html.slice(0, 5000))}`;
  for (const rule of siteConfig.professorRules || []) {
    if ((rule.keywords || []).some(keyword => text.includes(keyword))) return rule.professor;
  }
  return "담당 미확인";
}

function getPageSpan(file, siteConfig) {
  const value = Number(siteConfig.pageSpans?.[file]);
  return Number.isInteger(value) && value > 1 ? value : 1;
}

function getPeriodLabel(period, span, periods) {
  const start = periods.find(item => Number(item.period) === Number(period));
  if (span <= 1) {
    return start?.time ? `${start.label} ${start.time}` : start?.label || `${period}교시`;
  }

  const endPeriod = Number(period) + Number(span) - 1;
  const end = periods.find(item => Number(item.period) === endPeriod);
  const timeRange = getTimeRange(start?.time, end?.time);
  const label = `${period}-${endPeriod}교시`;
  return timeRange ? `${label} ${timeRange}` : label;
}

function getTimeRange(startTime, endTime) {
  const start = String(startTime || "").split("-")[0]?.trim();
  const end = String(endTime || "").split("-").at(-1)?.trim();
  return start && end ? `${start}-${end}` : "";
}

function getDateInfo(yearValue, month, day) {
  const date = new Date(Date.UTC(yearValue, month - 1, day));
  const weekdayIndex = date.getUTCDay();
  const monday = new Date(date);
  const offset = weekdayIndex === 0 ? -6 : 1 - weekdayIndex;
  monday.setUTCDate(date.getUTCDate() + offset);

  return {
    dateKey: formatDate(date),
    dateLabel: `${pad(month)}/${pad(day)}`,
    weekday: `${weekdayLabels[weekdayIndex]}요일`,
    weekKey: formatDate(monday)
  };
}

function formatDate(date) {
  return `${date.getUTCFullYear()}-${pad(date.getUTCMonth() + 1)}-${pad(date.getUTCDate())}`;
}

function pad(value) {
  return String(value).padStart(2, "0");
}
