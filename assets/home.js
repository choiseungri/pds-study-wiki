const data = window.PDS_SITE_DATA || { config: {}, pages: [] };
const pages = Array.isArray(data.pages) ? data.pages : [];
const config = data.config || {};
const examArchive = [
  {
    year: "2025",
    items: [
      { label: "형성평가", href: "Y/2025-pds4-formative-quiz.html", questions: 197, note: "임시정답 2" },
      { label: "총괄평가", href: "Y/2025-pds4-summative-quiz.html", questions: 24 }
    ]
  },
  {
    year: "2023",
    items: [
      { label: "형성평가", href: "Y/2023-pds4-formative-quiz.html", questions: 65, note: "임시정답 2" },
      { label: "총괄평가", href: "Y/2023-pds4-summative-quiz.html", questions: 109, note: "검토표시 1" }
    ]
  },
  {
    year: "2022",
    items: [
      { label: "형성평가", href: "Y/2022-pds4-formative-quiz.html", questions: 49, note: "검토표시 1" },
      { label: "총괄평가", href: "Y/2022-pds4-summative-quiz.html", questions: 166, note: "임시정답 4 · 검토표시 2" }
    ]
  },
  {
    year: "2021",
    items: [
      { label: "형성평가", href: "Y/2021-pds4-formative-quiz.html", questions: 52 },
      { label: "총괄평가", href: "Y/2021-pds4-summative-quiz.html", questions: 137, note: "임시정답 2 · 검토표시 1" }
    ]
  },
  {
    year: "2020",
    items: [
      { label: "형성평가", href: "Y/2020-pds4-formative-quiz.html", questions: 50, note: "임시정답 1 · 검토표시 1" },
      { label: "총괄평가", href: "Y/2020-pds4-summative-quiz.html", questions: 124, note: "임시정답 1 · 검토표시 1" }
    ]
  },
  {
    year: "2019",
    items: [
      { label: "1차시험", href: "Y/2019-pds4-1st-quiz.html", questions: 60, note: "임시정답 10 · 검토표시 1" },
      { label: "2차시험", href: "Y/2019-pds4-2nd-quiz.html", questions: 115, note: "임시정답 8 · 검토표시 1" }
    ]
  },
  {
    year: "2018",
    items: [
      { label: "형성평가", href: "Y/2018-pds4-formative-quiz.html", questions: 88, note: "임시정답 88 · 검토표시 9" },
      { label: "총괄평가", href: "Y/2018-pds4-summative-quiz.html", questions: 50, note: "임시정답 50 · 검토표시 3" }
    ]
  },
  {
    year: "2017",
    items: [
      { label: "복원", href: "Y/2017-pds4-restored-quiz.html", questions: 135, note: "임시정답 125 · 검토표시 40" }
    ]
  },
  {
    year: "2016",
    items: [
      { label: "형성평가", href: "Y/2016-pds4-formative-quiz.html", questions: 27, note: "임시정답 27" },
      { label: "복원", href: "Y/2016-pds4-restored-quiz.html", questions: 112, note: "임시정답 96 · 검토표시 75" }
    ]
  },
  {
    year: "2015",
    items: [
      { label: "복원", href: "Y/2015-pds4-restored-quiz.html", questions: 210, note: "임시정답 208 · 검토표시 28" }
    ]
  }
];

const state = {
  query: "",
  tag: "전체"
};

const els = {
  totalCount: document.querySelector("#total-count"),
  generatedAt: document.querySelector("#generated-at"),
  visibleCount: document.querySelector("#visible-count"),
  searchInput: document.querySelector("#search-input"),
  tagFilters: document.querySelector("#tag-filters"),
  examArchive: document.querySelector("#exam-archive"),
  examArchiveCount: document.querySelector("#exam-archive-count"),
  scheduleView: document.querySelector("#schedule-view"),
  lectureList: document.querySelector("#lecture-list")
};

function init() {
  document.title = config.siteTitle || "PDS 학습 위키";
  const h1 = document.querySelector("h1");
  const subtitle = document.querySelector(".subtitle");
  if (h1) h1.textContent = config.siteTitle || "PDS 학습 위키";
  if (subtitle) subtitle.textContent = config.subtitle || subtitle.textContent;

  els.totalCount.textContent = `${pages.length + getExamCount()}개`;
  els.generatedAt.textContent = data.generatedAt ? `갱신 ${formatGeneratedDate(data.generatedAt)}` : "자동 생성 목록";

  renderExamArchive();
  renderTagFilters();
  bindEvents();
  render();
}

function bindEvents() {
  els.searchInput.addEventListener("input", event => {
    state.query = event.target.value.trim();
    render();
  });
}

function renderTagFilters() {
  const tags = ["전체", ...Array.from(new Set(pages.map(page => page.tag).filter(Boolean))).sort((a, b) => a.localeCompare(b, "ko"))];
  els.tagFilters.replaceChildren(...tags.map(tag => {
    const button = document.createElement("button");
    button.className = "chip";
    button.type = "button";
    button.textContent = tag;
    button.setAttribute("aria-pressed", String(state.tag === tag));
    button.addEventListener("click", () => {
      state.tag = tag;
      renderTagFilters();
      render();
    });
    return button;
  }));
}

function renderExamArchive() {
  if (!els.examArchive) return;

  const totalExams = getExamCount();
  const totalQuestions = examArchive.reduce((sum, group) => {
    return sum + group.items.reduce((itemSum, item) => itemSum + item.questions, 0);
  }, 0);

  if (els.examArchiveCount) {
    els.examArchiveCount.textContent = `${totalExams}개 시험지 · ${totalQuestions.toLocaleString("ko-KR")}문항`;
  }

  els.examArchive.replaceChildren(...examArchive.map(createExamYearGroup));
}

function getExamCount() {
  return examArchive.reduce((sum, group) => sum + group.items.length, 0);
}

function createExamYearGroup(group) {
  const article = document.createElement("article");
  article.className = "exam-year";

  const heading = document.createElement("div");
  heading.className = "exam-year-heading";

  const year = document.createElement("h3");
  year.textContent = group.year;

  const count = document.createElement("span");
  const questions = group.items.reduce((sum, item) => sum + item.questions, 0);
  count.textContent = `${group.items.length}개 · ${questions.toLocaleString("ko-KR")}문항`;
  heading.append(year, count);

  const links = document.createElement("div");
  links.className = "exam-links";
  links.replaceChildren(...group.items.map(createExamLink));

  article.append(heading, links);
  return article;
}

function createExamLink(item) {
  const link = document.createElement("a");
  link.className = `exam-link ${getExamTypeClass(item.label)}`;
  link.href = encodeURI(item.href);
  link.innerHTML = `
    <span class="exam-link-top">
      <strong>${escapeHtml(item.label)}</strong>
      <span>${Number(item.questions).toLocaleString("ko-KR")}문항</span>
    </span>
    ${item.note ? `<span class="exam-note">${escapeHtml(item.note)}</span>` : `<span class="exam-note exam-note-ok">정답표시 확인</span>`}
  `;
  return link;
}

function getExamTypeClass(label) {
  if (label.includes("형성")) return "exam-link-formative";
  if (label.includes("총괄")) return "exam-link-summative";
  if (label.includes("복원")) return "exam-link-restored";
  return "exam-link-default";
}

function render() {
  const filtered = filterPages();
  els.visibleCount.textContent = state.query || state.tag !== "전체"
    ? `${filtered.length}개 표시`
    : "전체 자료";
  renderSchedule(filtered);
  renderList(filtered);
}

function filterPages() {
  const normalizedQuery = normalize(state.query);
  return pages.filter(page => {
    const tagOk = state.tag === "전체" || page.tag === state.tag;
    if (!tagOk) return false;
    if (!normalizedQuery) return true;
    const haystack = normalize([
      page.title,
      page.file,
      page.dateLabel,
      page.weekday,
      page.periodLabel,
      page.tag
    ].join(" "));
    return haystack.includes(normalizedQuery);
  });
}

function renderSchedule(items) {
  if (!items.length) {
    els.scheduleView.innerHTML = `<div class="no-results">검색 조건에 맞는 자료가 없습니다.</div>`;
    return;
  }

  const weeks = groupBy(items, page => page.weekKey);
  const weekBlocks = Array.from(weeks.entries())
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([, weekPages], index) => createWeekBlock(weekPages, index));
  els.scheduleView.replaceChildren(...weekBlocks);
}

function createWeekBlock(weekPages, index) {
  const sorted = [...weekPages].sort(comparePages);
  const dates = Array.from(new Map(sorted.map(page => [page.dateKey, page])).values())
    .sort((a, b) => a.dateKey.localeCompare(b.dateKey));
  const periods = getPeriods(sorted);

  const block = document.createElement("article");
  block.className = "week-block";

  const title = document.createElement("div");
  title.className = "week-title";
  title.innerHTML = `
    <div>
      <span class="week-kicker">WEEK ${String(index + 1).padStart(2, "0")}</span>
      <strong>${escapeHtml(dates[0].dateLabel)} - ${escapeHtml(dates[dates.length - 1].dateLabel)}</strong>
    </div>
    <span class="week-count">${sorted.length}개 자료</span>
  `;

  const scroller = document.createElement("div");
  scroller.className = "grid-scroller";

  const grid = document.createElement("div");
  grid.className = "schedule-grid";
  grid.style.gridTemplateColumns = `128px repeat(${dates.length}, minmax(172px, 1fr))`;
  grid.style.gridTemplateRows = `74px repeat(${periods.length}, minmax(126px, auto))`;

  const corner = cell("schedule-cell schedule-head period-corner", "교시");
  corner.style.gridColumn = "1";
  corner.style.gridRow = "1";
  grid.appendChild(corner);

  dates.forEach((datePage, dateIndex) => {
    const head = document.createElement("div");
    head.className = "schedule-cell schedule-head date-head";
    head.style.gridColumn = String(dateIndex + 2);
    head.style.gridRow = "1";
    head.innerHTML = `
      <span>${escapeHtml(datePage.weekday)}</span>
      <strong>${escapeHtml(datePage.dateLabel)}</strong>
    `;
    grid.appendChild(head);
  });

  const coveredSlots = new Set();

  periods.forEach((period, periodIndex) => {
    const row = periodIndex + 2;
    const periodHead = cell("schedule-cell period-head", period.label);
    periodHead.dataset.period = String(period.period);
    periodHead.style.gridColumn = "1";
    periodHead.style.gridRow = String(row);
    grid.appendChild(periodHead);

    dates.forEach((datePage, dateIndex) => {
      const key = slotKey(datePage.dateKey, period.period);
      if (coveredSlots.has(key)) return;

      const slot = document.createElement("div");
      slot.className = "schedule-cell lesson-slot";
      slot.style.gridColumn = String(dateIndex + 2);
      slot.style.gridRow = String(row);
      const matches = sorted.filter(page => page.dateKey === datePage.dateKey && Number(page.period) === Number(period.period));

      if (!matches.length) {
        slot.classList.add("empty-cell");
        slot.innerHTML = `<span class="empty-line"></span>`;
      } else {
        const span = Math.max(...matches.map(page => Number(page.span) || 1));
        if (span > 1) {
          slot.classList.add("span-slot");
          slot.style.gridRow = `${row} / span ${span}`;
          markCoveredSlots(coveredSlots, datePage.dateKey, period.period, span);
        }
        slot.replaceChildren(...matches.map(createLessonLink));
      }
      grid.appendChild(slot);
    });
  });

  scroller.appendChild(grid);
  block.append(title, scroller);
  return block;
}

function renderList(items) {
  if (!items.length) {
    els.lectureList.innerHTML = `<div class="no-results">검색 조건에 맞는 자료가 없습니다.</div>`;
    return;
  }
  els.lectureList.replaceChildren(...[...items].sort(comparePages).map(createLectureCard));
}

function createLessonLink(page) {
  const link = document.createElement("a");
  link.className = `lesson-link ${getTagClass(page.tag)}`;
  if (Number(page.span) > 1) link.classList.add("lesson-link-wide");
  link.href = encodeURI(page.file);
  link.innerHTML = `
    <span class="lesson-kicker">
      <span class="period-pill">${escapeHtml(page.periodLabel)}</span>
      ${page.professor ? `<span class="tag">${escapeHtml(page.professor)}</span>` : ""}
    </span>
    <span class="lesson-title">${escapeHtml(page.title)}</span>
    <span class="lesson-open" aria-hidden="true">열기 &rarr;</span>
  `;
  return link;
}

function createLectureCard(page) {
  const link = document.createElement("a");
  link.className = `lecture-card ${getTagClass(page.professor || page.tag)}`;
  link.href = encodeURI(page.file);
  link.innerHTML = `
    <div class="card-top">
      <span class="tag">${escapeHtml(page.professor || page.tag || "담당 미확인")}</span>
      <span>${escapeHtml(page.dateLabel)} · ${escapeHtml(page.periodLabel)}</span>
    </div>
    <h3>${escapeHtml(page.title)}</h3>
    <div class="card-foot">
      <span>${escapeHtml(page.weekday)}</span>
      <span aria-hidden="true">열기 &rarr;</span>
    </div>
  `;
  return link;
}

function getPeriods(items) {
  const configured = Array.isArray(config.periods) ? config.periods : [];
  const used = new Set();
  items.forEach(page => {
    const start = Number(page.period);
    const span = Number(page.span) || 1;
    for (let offset = 0; offset < span; offset += 1) {
      used.add(start + offset);
    }
  });
  const base = configured
    .filter(period => used.has(Number(period.period)))
    .map(period => ({
      period: Number(period.period),
      label: period.time ? `${period.label}\n${period.time}` : period.label
    }));

  const missing = Array.from(used)
    .filter(period => !base.some(item => item.period === period))
    .sort((a, b) => a - b)
    .map(period => ({ period, label: `${period}교시` }));

  return [...base, ...missing].sort((a, b) => a.period - b.period);
}

function markCoveredSlots(set, dateKey, startPeriod, span) {
  for (let offset = 1; offset < span; offset += 1) {
    set.add(slotKey(dateKey, Number(startPeriod) + offset));
  }
}

function slotKey(dateKey, period) {
  return `${dateKey}:${period}`;
}

function cell(className, text) {
  const div = document.createElement("div");
  div.className = className;
  div.textContent = text;
  return div;
}

function groupBy(items, getKey) {
  const map = new Map();
  items.forEach(item => {
    const key = getKey(item);
    if (!map.has(key)) map.set(key, []);
    map.get(key).push(item);
  });
  return map;
}

function comparePages(a, b) {
  return a.dateKey.localeCompare(b.dateKey) || Number(a.period) - Number(b.period) || a.title.localeCompare(b.title, "ko");
}

function getTagClass(tag = "") {
  if (tag.includes("박훈기")) return "tag-prof-park";
  if (tag.includes("김대호")) return "tag-prof-kim-dh";
  if (tag.includes("한승훈")) return "tag-prof-han";
  if (tag.includes("신영전")) return "tag-prof-shin";
  if (tag.includes("김민주")) return "tag-prof-kim-mj";
  if (tag.includes("김원규")) return "tag-prof-kim-wk";
  if (tag.includes("이어진")) return "tag-prof-lee";
  if (tag.includes("손정식")) return "tag-prof-son";
  if (tag.includes("송은섭")) return "tag-prof-song";
  return "tag-default";
}

function normalize(value) {
  return String(value || "").toLocaleLowerCase("ko").replace(/\s+/g, "");
}

function formatGeneratedDate(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "자동 생성";
  return date.toLocaleString("ko-KR", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit"
  });
}

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

init();
