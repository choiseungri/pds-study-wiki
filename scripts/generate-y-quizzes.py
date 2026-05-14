from __future__ import annotations

import html
import json
import re
import struct
import zlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import fitz
import olefile


ROOT = Path(__file__).resolve().parents[1]
Y_DIR = ROOT / "Y"


CIRCLED = "①②③④⑤⑥⑦⑧⑨⓵⓶⓷⓸⓹⓺⓻⓼⓽"
LATIN = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


@dataclass
class ExamSpec:
    year: int
    kind: str
    title: str
    output: str
    source_selector: Callable[[list[Path]], Path]
    answer_selector: Callable[[list[Path]], Path] | None = None
    notes: str = ""


@dataclass
class Line:
    text: str
    marked: bool = False
    x0: float = 0.0
    y0: float = 0.0


@dataclass
class Option:
    text: str
    correct: bool = False
    lines: list[str] = field(default_factory=list)


@dataclass
class Question:
    source: str
    professor: str
    stem: str
    options: list[Option]
    answers: list[int]
    uncertain: bool = False
    note: str = ""


def main() -> None:
    pdfs = sorted(Y_DIR.glob("*.pdf"), key=lambda p: p.name)
    docs = sorted([*Y_DIR.glob("*.docx"), *Y_DIR.glob("*.hwp")], key=lambda p: p.name)
    files = sorted([*pdfs, *docs], key=lambda p: p.name)

    specs = build_specs()
    reports = []
    for spec in specs:
        source_path = spec.source_selector(files)
        answer_path = spec.answer_selector(files) if spec.answer_selector else source_path
        source_questions = parse_document(source_path, answer_path)
        questions = normalize_questions(source_questions)
        write_quiz(spec, source_path, answer_path, questions)
        reports.append({
            "file": spec.output,
            "source": source_path.name,
            "answer": answer_path.name if answer_path else "",
            "questions": len(questions),
            "answered": sum(1 for q in questions if q["answers"]),
            "unanswered": sum(1 for q in questions if not q["answers"]),
        })

    print(json.dumps(reports, ensure_ascii=False, indent=2))


def build_specs() -> list[ExamSpec]:
    return [
        ExamSpec(2025, "형성평가", "2025학년도 환자.의사.사회4 형성평가", "2025-pds4-formative-quiz.html", by("251226")),
        ExamSpec(2023, "총괄평가", "2023학년도 PDS4 총괄평가", "2023-pds4-summative-quiz.html", by("230317", "문제지"), by("230317", "답")),
        ExamSpec(2023, "형성평가", "2023학년도 PDS4 형성평가", "2023-pds4-formative-quiz.html", by("230309", "문제지"), by("230309", "답")),
        ExamSpec(2022, "총괄평가", "2022학년도 PDS4 총괄평가", "2022-pds4-summative-quiz.html", by("220318", "문제지"), by("220318", "답")),
        ExamSpec(2022, "형성평가", "2022학년도 PDS4 형성평가", "2022-pds4-formative-quiz.html", by("220311", "문제지"), by("220311", "답")),
        ExamSpec(2021, "총괄평가", "2021학년도 PDS4 총괄평가", "2021-pds4-summative-quiz.html", by("210319", "문제지"), by("210319", "답")),
        ExamSpec(2021, "형성평가", "2021학년도 PDS4 형성평가", "2021-pds4-formative-quiz.html", by("210312", "문제지"), by("210312", "답")),
        ExamSpec(2020, "총괄평가", "2020학년도 PDS4 총괄평가", "2020-pds4-summative-quiz.html", by("200710", "문제지"), by("200710", "답")),
        ExamSpec(2020, "형성평가", "2020학년도 PDS4 형성평가", "2020-pds4-formative-quiz.html", by("200703", "문제지"), by("200703", "답")),
        ExamSpec(2019, "2차시험", "2019학년도 PDS4 2차시험", "2019-pds4-2nd-quiz.html", by("190315", "문제지"), by("190315", "답")),
        ExamSpec(2019, "1차시험", "2019학년도 PDS4 1차시험", "2019-pds4-1st-quiz.html", by("190306", "문제지"), by("190306", "답")),
        ExamSpec(2018, "종합시험", "2018 PDS4 종합시험 복원", "2018-pds4-summative-quiz.html", by("2018 PDS4 종합시험", ext=".hwp"), notes="HWP 복원본이라 정답 표시가 없으면 검토 필요로 표시합니다."),
        ExamSpec(2018, "형성평가", "2018 PDS4 형성평가", "2018-pds4-formative-quiz.html", by_exact("2018 PDS4 형성평가.pdf"), by_exact("2018 PDS4 형성평가 답.pdf")),
        ExamSpec(2017, "복원", "2017 PDS4 복원", "2017-pds4-restored-quiz.html", by_exact("2017 PDS4 복원.pdf"), notes="복원본에 별도 정답 표시가 없으면 검토 필요로 표시합니다."),
        ExamSpec(2016, "복원", "2016 PDS4 복원", "2016-pds4-restored-quiz.html", by_exact("2016 PDS4 복원.docx"), notes="DOCX 복원본이라 정답 표시가 없으면 검토 필요로 표시합니다."),
        ExamSpec(2016, "형성평가", "2016 PDS4 형성평가", "2016-pds4-formative-quiz.html", by_exact("2016 PDS4 형성평가.docx"), notes="DOCX 복원본이라 정답 표시가 없으면 검토 필요로 표시합니다."),
        ExamSpec(2015, "복원", "2015 PDS4 복원", "2015-pds4-restored-quiz.html", by_exact("2015 PDS4 복원.pdf"), notes="2015 답지는 스캔 PDF라 자동 정답 추출을 하지 못했습니다."),
    ]


def by(*needles: str, ext: str | None = None) -> Callable[[list[Path]], Path]:
    def select(files: list[Path]) -> Path:
        matches = []
        for path in files:
            if ext and path.suffix.lower() != ext.lower():
                continue
            if ext is None and path.suffix.lower() != ".pdf":
                continue
            if all(needle in path.name for needle in needles):
                matches.append(path)
        if not matches:
            raise FileNotFoundError(f"No file matched {needles}")
        return sorted(matches, key=lambda p: p.name)[0]
    return select


def by_exact(name: str) -> Callable[[list[Path]], Path]:
    def select(files: list[Path]) -> Path:
        for path in files:
            if path.name == name:
                return path
        raise FileNotFoundError(name)
    return select


def parse_document(source_path: Path, answer_path: Path) -> list[Question]:
    parse_path = answer_path if answer_path.exists() else source_path
    if parse_path.suffix.lower() == ".hwp":
        lines = [Line(text) for text in extract_hwp_text(parse_path).splitlines()]
    elif parse_path.suffix.lower() == ".docx":
        lines = extract_marked_lines(parse_path)
        return parse_loose_numbered_lines(lines)
    else:
        lines = extract_marked_lines(parse_path)
    parsed = parse_lines(lines)
    if parse_path.suffix.lower() == ".pdf" and len(parsed) < 50:
        loose = parse_loose_numbered_lines(lines)
        if len(loose) > max(5, len(parsed) * 2):
            return loose
    return parsed


def extract_marked_lines(path: Path) -> list[Line]:
    doc = fitz.open(str(path))
    out: list[Line] = []
    for page in doc:
        marks = get_page_marks(page)
        for block in page.get_text("dict").get("blocks", []):
            if block.get("type") != 0:
                continue
            for raw_line in block.get("lines", []):
                spans = [span for span in raw_line.get("spans", []) if span.get("text", "").strip()]
                if not spans:
                    continue
                text = normalize_text("".join(span.get("text", "") for span in spans))
                if not text:
                    continue
                rect = fitz.Rect(raw_line["bbox"])
                out.append(Line(text=text, marked=is_marked(rect, marks), x0=rect.x0, y0=rect.y0))
    return out


def get_page_marks(page: fitz.Page) -> list[tuple[str, fitz.Rect]]:
    marks: list[tuple[str, fitz.Rect]] = []
    for drawing in page.get_drawings():
        rect = drawing.get("rect")
        if rect is None:
            continue
        fill = drawing.get("fill")
        if fill and fill[0] > 0.8 and fill[1] > 0.8 and fill[2] < 0.2:
            marks.append(("highlight", fitz.Rect(rect)))
            continue
        width = rect.width
        height = rect.height
        if height <= 1.2 and width >= 8:
            marks.append(("underline", fitz.Rect(rect)))
    return marks


def is_marked(line_rect: fitz.Rect, marks: list[tuple[str, fitz.Rect]]) -> bool:
    for kind, mark in marks:
        overlap_x = min(line_rect.x1, mark.x1) - max(line_rect.x0, mark.x0)
        if overlap_x <= 2:
            continue
        if kind == "highlight":
            overlap_y = min(line_rect.y1, mark.y1) - max(line_rect.y0, mark.y0)
            if overlap_y > 1:
                return True
        else:
            if line_rect.y0 - 2 <= mark.y0 <= line_rect.y1 + 5:
                return True
    return False


def extract_hwp_text(path: Path) -> str:
    ole = olefile.OleFileIO(str(path))
    header = ole.openstream("FileHeader").read()
    compressed = bool(header[36] & 1)
    sections = sorted(
        [item for item in ole.listdir() if item[0] == "BodyText" and item[1].startswith("Section")],
        key=lambda item: item[1],
    )
    chunks: list[str] = []
    for section in sections:
        data = ole.openstream("/".join(section)).read()
        if compressed:
            data = zlib.decompress(data, -15)
        offset = 0
        while offset + 4 <= len(data):
            header_value = struct.unpack_from("<I", data, offset)[0]
            offset += 4
            tag = header_value & 0x3FF
            size = (header_value >> 20) & 0xFFF
            if size == 0xFFF:
                if offset + 4 > len(data):
                    break
                size = struct.unpack_from("<I", data, offset)[0]
                offset += 4
            payload = data[offset:offset + size]
            offset += size
            if tag == 67:
                chunks.append(payload.decode("utf-16le", errors="ignore"))
    return clean_hwp_text("\n".join(chunks))


def clean_hwp_text(text: str) -> str:
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)
    text = text.replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    return text


def parse_lines(raw_lines: list[Line]) -> list[Question]:
    questions: list[Question] = []
    source = "출처 미분류"
    professor = ""
    stem: list[str] = []
    options: list[Option] = []
    pending_marker = False
    pending_question = False

    def finalize() -> None:
        nonlocal stem, options, pending_question
        clean_stem = normalize_stem(stem)
        clean_options = [opt for opt in options if normalize_text(opt.text)]
        if clean_stem and (len(clean_options) >= 2 or any(opt.correct for opt in clean_options)):
            answers = [index + 1 for index, opt in enumerate(clean_options) if opt.correct]
            questions.append(Question(
                source=source,
                professor=professor,
                stem=clean_stem,
                options=clean_options,
                answers=answers,
                uncertain=not bool(answers),
                note="" if answers else "원본에서 정답 표시를 자동으로 확인하지 못했습니다.",
            ))
        stem = []
        options = []
        pending_question = False

    cleaned = [Line(normalize_text(line.text), line.marked, line.x0, line.y0) for line in raw_lines]
    cleaned = [line for line in cleaned if line.text]

    for index, line in enumerate(cleaned):
        text = line.text
        if pending_marker and not is_option_marker_only(text):
            opt_text = parse_option_start(text)
            add_option(options, opt_text if opt_text is not None else text, line.marked)
            pending_marker = False
            continue

        if is_noise(text):
            continue

        section = parse_section(text)
        if section:
            finalize()
            source, professor = section
            pending_marker = False
            pending_question = False
            continue

        qmatch = re.match(r"^\s*(\d{1,3})\s*[\.)]\s*(.+)$", text)
        if qmatch:
            finalize()
            stem = [cleanup_question_start(qmatch.group(2))]
            pending_marker = False
            pending_question = False
            continue

        if re.match(r"^\s*\d{1,3}\s*[\.)]\s*$", text):
            finalize()
            pending_marker = False
            pending_question = True
            continue

        if pending_question:
            stem = [cleanup_question_start(text)]
            pending_question = False
            continue

        opt_text = parse_option_start(text)

        if is_option_marker_only(text):
            pending_marker = True
            continue

        if opt_text is not None:
            if not stem and questions and len(options) == 0:
                stem = ["문항 본문 미복원"]
            add_option(options, opt_text, line.marked)
            continue

        if options:
            if looks_like_new_stem(cleaned, index):
                finalize()
                stem = [text]
            else:
                options[-1].text = normalize_text(f"{options[-1].text} {text}")
                options[-1].lines.append(text)
                options[-1].correct = options[-1].correct or line.marked
        else:
            stem.append(text)

    finalize()
    return questions


def parse_loose_numbered_lines(raw_lines: list[Line]) -> list[Question]:
    lines = [normalize_text(line.text) for line in raw_lines]
    lines = [line for line in lines if line and not is_noise(line)]
    questions: list[Question] = []
    source = "출처 미분류"
    current: list[str] = []

    def flush() -> None:
        nonlocal current
        if not current:
            return
        question = build_loose_question(current, source)
        if question:
            questions.append(question)
        current = []

    for line in lines:
        section = parse_section(line)
        if section and not current:
            source = section[0]
            continue
        qmatch = re.match(r"^\s*(\d{1,3})\s*[\.)]?\s*(.+)$", line)
        if qmatch and ("?" in qmatch.group(2) or len(qmatch.group(2)) > 8):
            flush()
            current = [qmatch.group(2)]
            continue
        if current:
            current.append(line)
        elif looks_like_loose_heading(line):
            source = normalize_source(line)
    flush()
    return questions


def build_loose_question(lines: list[str], source: str) -> Question | None:
    cleaned = [normalize_text(line) for line in lines if normalize_text(line)]
    if not cleaned:
        return None
    answer = ""
    body: list[str] = []
    for line in cleaned:
        match = re.match(r"^답\s*[:：]?\s*(.+)$", line)
        if match:
            answer = normalize_text(match.group(1))
        else:
            body.append(line)
    if not body:
        return None
    stem = cleanup_question_start(body[0])
    tail = body[1:]
    options: list[str] = []
    for line in tail:
        if len(line) > 140 or looks_like_loose_heading(line):
            continue
        parts = [part.strip() for part in re.split(r"\s{2,}", line) if part.strip()]
        options.extend(parts if len(parts) >= 2 else [line])
    correct_index = 0
    if answer:
        for index, option in enumerate(options):
            if normalize(answer) in normalize(option) or normalize(option) in normalize(answer):
                correct_index = index + 1
                break
        if not correct_index:
            options.append(answer)
            correct_index = len(options)
    for index, option in enumerate(options):
        if re.search(r"\(?\s*답\s*\)?", option):
            correct_index = index + 1
            options[index] = re.sub(r"\(?\s*답\s*\)?", "", option).strip()
    if not options:
        return None
    if not answer and len(options) < 2:
        return None
    option_objs = [Option(text=option, correct=(index + 1 == correct_index)) for index, option in enumerate(options)]
    return Question(
        source=source,
        professor="",
        stem=stem,
        options=option_objs,
        answers=[correct_index] if correct_index else [],
        uncertain=not bool(correct_index),
        note="" if correct_index else "DOCX 복원본에서 정답 표시를 자동으로 확인하지 못했습니다.",
    )


def looks_like_loose_heading(text: str) -> bool:
    if len(text) > 80:
        return False
    return bool(re.search(r"교수|의료관리학|의료법규|병원경영|의료윤리|통합의학|보건관리|법의학|의사소통", text))


def cleanup_question_start(text: str) -> str:
    text = normalize_text(text)
    text = re.sub(r"^문(?=보건복지부령|보건복지부|의료법|국민건강|감염병|검역|다음|상급|중앙회)", "", text)
    return text


def normalize(value: str) -> str:
    return re.sub(r"\s+", "", value.lower())


def add_option(options: list[Option], text: str, marked: bool) -> None:
    correct = marked or bool(re.search(r"\(?\s*답\s*\)?", text))
    text = re.sub(r"\(?\s*답\s*\)?", "", text)
    text = re.sub(r"^\s*답\s*[:：]\s*", "", text)
    options.append(Option(text=normalize_text(text), correct=correct, lines=[text]))


def parse_option_start(text: str) -> str | None:
    text = text.strip()
    if not text:
        return None
    if text[0] in CIRCLED:
        return text[1:].strip()
    match = re.match(r"^([A-E])\s*[\.)]\s*(.+)$", text)
    if match:
        return match.group(2).strip()
    match = re.match(r"^[●⚫•]\s*(.+)$", text)
    if match:
        return match.group(1).strip()
    match = re.match(r"^[-–]\s*(.+)$", text)
    if match and not re.search(r"\d+\s*문", text):
        return match.group(1).strip()
    match = re.match(r"^답\s*[:：]\s*(.+)$", text)
    if match:
        return f"답: {match.group(1).strip()}"
    return None


def is_option_marker_only(text: str) -> bool:
    value = text.strip()
    if value in {"●", "⚫", "•"}:
        return True
    if value in CIRCLED:
        return True
    return bool(re.fullmatch(r"[A-E]\s*[\.)]", value))


def parse_section(text: str) -> tuple[str, str] | None:
    if len(text) > 180:
        return None
    if text.startswith("[") and "]" in text:
        body, rest = text[1:].split("]", 1)
        if is_sectionish(body, rest):
            return normalize_source(body), parse_professor(rest)
    if text.startswith("<") and ">" in text:
        body, rest = text[1:].split(">", 1)
        if is_sectionish(body, rest):
            return normalize_source(body), parse_professor(rest)
    if text.startswith("■"):
        body = text.lstrip("■ ").strip()
        if body and len(body) < 80:
            return normalize_source(body), ""
    return None


def is_sectionish(body: str, rest: str) -> bool:
    combined = f"{body} {rest}"
    return bool(re.search(r"문제|문항|P\b|교수|박훈기|신영전|김원규|한승훈|김미정|정규원|유상호|한동운|황환식|김민주|장성호", combined))


def parse_professor(rest: str) -> str:
    rest = rest.replace("P", " ").replace("교수", " ")
    names = re.findall(r"[가-힣]{2,4}", rest)
    for name in reversed(names):
        if name not in {"문제", "문항", "복원"}:
            return name
    return ""


def normalize_source(value: str) -> str:
    value = value.replace("–", "-").replace("—", "-")
    value = re.sub(r"\s+", " ", value).strip(" -")
    return value or "출처 미분류"


def looks_like_new_stem(lines: list[Line], index: int) -> bool:
    text = lines[index].text
    if len(text) < 5:
        return False
    if not ("?" in text or "것은" in text or "고르" in text or "옳" in text or "아닌" in text):
        return False
    lookahead = lines[index + 1:index + 5]
    return any(parse_option_start(item.text) is not None or item.text in {"●", "⚫", "•"} for item in lookahead)


def normalize_stem(lines: list[str]) -> str:
    return normalize_text(" ".join(line for line in lines if line))


def normalize_text(value: str) -> str:
    value = value.replace("\u00a0", " ")
    value = re.sub(r"[ \t]+", " ", value)
    value = re.sub(r"\n{3,}", "\n\n", value)
    return value.strip()


def is_noise(text: str) -> bool:
    if not text:
        return True
    if re.fullmatch(r"\d+", text):
        return True
    if text.startswith("총 ") and "복원" in text:
        return True
    if text.startswith("202") and ("학년도" in text or "PDS" in text):
        return True
    if text.startswith("201") and ("학년도" in text or "PDS" in text):
        return True
    if text.startswith("* "):
        return True
    return False


def normalize_questions(questions: list[Question]) -> list[dict]:
    normalized = []
    for index, question in enumerate(questions, 1):
        answers = list(question.answers)
        provisional = False
        note = question.note
        if not answers and question.options:
            answers = pick_provisional_answers(question)
            provisional = True
            note = build_provisional_note(question, answers)
        normalized.append({
            "id": index,
            "source": question.source,
            "professor": question.professor,
            "stem": question.stem,
            "options": [option.text for option in question.options],
            "answers": answers,
            "uncertain": question.uncertain or provisional,
            "provisional": provisional,
            "note": note,
        })
    return normalized


def pick_provisional_answers(question: Question) -> list[int]:
    stem = normalize(question.stem)
    options = [option.text for option in question.options]
    normalized_options = [normalize(option) for option in options]

    if "bathe" in stem:
        if "가장힘든점" in stem or "힘든점" in stem:
            hit = find_option(normalized_options, ["t", "trouble"])
            if hit:
                return [hit]
        if "기분" in stem or "어때" in stem:
            hit = find_option(normalized_options, ["a", "affect"])
            if hit:
                return [hit]
        if "어떻게하" in stem or "조치" in stem:
            hit = find_option(normalized_options, ["h", "handling"])
            if hit:
                return [hit]

    if "보수교육" in stem and ("매년" in stem or "이수" in stem):
        hit = find_option(normalized_options, ["8", "8시간"])
        if hit:
            return [hit]

    if "결혼" in stem and "srrs" in stem:
        hit = find_option(normalized_options, ["50"])
        if hit:
            return [hit]

    if "larrydossey" in stem or "distanthealing" in stem:
        hit = find_option(normalized_options, ["답없음", "없음"])
        if hit:
            return [hit]

    if "상급종합병원" in stem and "진료과목수" in stem:
        hit = find_option(normalized_options, ["20"])
        if hit:
            return [hit]

    return [1]


def find_option(options: list[str], needles: list[str]) -> int:
    for index, option in enumerate(options, 1):
        if any(needle in option for needle in needles):
            return index
    return 0


def build_provisional_note(question: Question, answers: list[int]) -> str:
    selected = ", ".join(str(answer) for answer in answers)
    base = "원본에서 정답 표시를 자동으로 확인하지 못해 임시 정답 후보를 넣었습니다."
    if selected:
        base += f" 임시 후보: {selected}번."
    return base + " 반드시 원본/강의자료로 검토하세요."


def looks_like_new_stem(lines: list[Line], index: int) -> bool:
    text = lines[index].text
    if len(text) < 12 or text.startswith("※"):
        return False
    if is_indented_pdf_continuation(lines[index]):
        return False
    if is_inside_pdf_note(lines, index):
        return False
    if index + 1 < len(lines) and lines[index].y0 and lines[index + 1].y0 and lines[index + 1].y0 + 100 < lines[index].y0:
        return False
    preview = [text]
    found_options = False
    for item in lines[index + 1:index + 14]:
        item_text = item.text
        if parse_section(item_text):
            break
        if parse_option_start(item_text) is not None or is_option_marker_only(item_text):
            found_options = True
            break
        if len(preview) < 8:
            preview.append(item_text)
    return found_options and has_question_cue(" ".join(preview))


def is_indented_pdf_continuation(line: Line) -> bool:
    if not line.x0:
        return False
    column_base = 308.0 if line.x0 >= 300 else 28.0
    return line.x0 - column_base > 10


def is_inside_pdf_note(lines: list[Line], index: int) -> bool:
    current = lines[index]
    for previous in reversed(lines[max(0, index - 12):index]):
        if parse_option_start(previous.text) is not None or parse_section(previous.text):
            return False
        if previous.text.startswith("※"):
            if current.y0 - previous.y0 > 22:
                return False
            return not (current.y0 < 150 and previous.y0 > 600)
    return False


def has_question_cue(text: str) -> bool:
    return bool(re.search(
        r"\?|것은|것을|고르|옳|틀린|아닌|해당|무엇|누구|몇|순서|알맞|적절|설명|말하는|해당하지|해당하는|시오",
        text,
    ))


def normalize_questions(questions: list[Question]) -> list[dict]:
    normalized = []
    for index, question in enumerate(questions, 1):
        raw_options = [option.text for option in question.options]
        raw_text = " ".join([question.stem, *raw_options])
        cleaned_options, option_index_map = clean_options(raw_options)
        answers = [option_index_map[answer] for answer in question.answers if answer in option_index_map]
        provisional = False
        disputed = False
        deleted = has_deleted_answer_note(raw_text)
        note = question.note

        explicit_answers, explicit_note = extract_explicit_answers(raw_text, len(cleaned_options))
        if explicit_answers:
            answers = explicit_answers
            disputed = True
            note = merge_notes(note, explicit_note)

        cleaned_question = Question(
            source=question.source,
            professor=question.professor,
            stem=clean_question_text(question.stem),
            options=[Option(text=option) for option in cleaned_options],
            answers=answers,
            uncertain=question.uncertain,
            note=note,
        )

        if not answers and cleaned_options:
            answers = pick_provisional_answers(cleaned_question)
            provisional = True
            note = merge_notes(note, build_deleted_note(answers) if deleted else build_provisional_note(cleaned_question, answers))

        normalized.append({
            "id": index,
            "source": question.source,
            "professor": question.professor,
            "stem": cleaned_question.stem,
            "options": cleaned_options,
            "answers": answers,
            "uncertain": question.uncertain or provisional or disputed or deleted,
            "provisional": provisional,
            "disputed": disputed,
            "deleted": deleted,
            "note": note,
        })
    return normalized


def clean_options(options: list[str]) -> tuple[list[str], dict[int, int]]:
    cleaned: list[str] = []
    index_map: dict[int, int] = {}
    for original_index, option in enumerate(options, 1):
        value = clean_question_text(option)
        if not value:
            continue
        index_map[original_index] = len(cleaned) + 1
        cleaned.append(value)
    return cleaned, index_map


def clean_question_text(value: str) -> str:
    value = normalize_text(value)
    value = re.sub(r"\s*※.*$", "", value)
    value = re.sub(r"\s*[<\[][^\]>]{0,160}(?:문제|문항)[^\]>]*[\]>]?.*$", "", value)
    return normalize_text(value)


def extract_explicit_answers(value: str, option_count: int) -> tuple[list[int], str]:
    answers: list[int] = []
    notes: list[str] = []
    for pattern in (
        r"답\s*(?:논란|확인|후보|은|:)?\s*([①②③④⑤⑥⑦⑧⑨0-9,\s/]+)",
        r"정답\s*(?:논란|확인|후보|은|:)?\s*([①②③④⑤⑥⑦⑧⑨0-9,\s/]+)",
    ):
        for match in re.finditer(pattern, value):
            parsed = parse_answer_numbers(match.group(1), option_count)
            if parsed:
                answers.extend(parsed)
                notes.append(match.group(0).strip())
    unique = sorted(set(answers))
    if not unique:
        return [], ""
    return unique, "원문 메모에서 정답 관련 표기를 발견했습니다: " + " / ".join(dict.fromkeys(notes))


def parse_answer_numbers(value: str, option_count: int) -> list[int]:
    circled = {char: index for index, char in enumerate("①②③④⑤⑥⑦⑧⑨", 1)}
    numbers = [circled[char] for char in value if char in circled]
    numbers.extend(int(match) for match in re.findall(r"\d+", value))
    return [number for number in numbers if 1 <= number <= option_count]


def has_deleted_answer_note(value: str) -> bool:
    return bool(re.search(r"정답\s*없음|문항\s*삭제|삭제\s*처리", value))


def merge_notes(*notes: str) -> str:
    parts = []
    for note in notes:
        cleaned = normalize_text(note)
        if cleaned and cleaned not in parts:
            parts.append(cleaned)
    return " ".join(parts)


def build_deleted_note(answers: list[int]) -> str:
    selected = ", ".join(str(answer) for answer in answers)
    base = "원문에 정답 없음 또는 문항 삭제 표시가 있어 채점 제외/검토 필요 문항으로 표시했습니다."
    if selected:
        base += f" 화면 표시를 위한 임시 후보: {selected}번."
    return base + " 원본 기준으로 최종 처리하세요."


def parse_section(text: str) -> tuple[str, str] | None:
    if len(text) > 180:
        return None
    if text.startswith("[") and "]" in text:
        body, rest = text[1:].split("]", 1)
        if is_sectionish(body, rest) or ":" in body:
            return normalize_source(body), parse_professor(rest)
    if text.startswith("<") and ">" in text:
        body, rest = text[1:].split(">", 1)
        if is_sectionish(body, rest) or ":" in body:
            return normalize_source(body), parse_professor(rest)
    if text.startswith("■"):
        body = text.lstrip("■ ").strip()
        if body and len(body) < 80:
            return normalize_source(body), ""
    return None


def is_noise(text: str) -> bool:
    if not text:
        return True
    if re.fullmatch(r"\d+", text):
        return True
    if re.fullmatch(r"[가-힣]{2,4}\s*\d+(?:\+\d+)?\s*문항", text):
        return True
    if text.startswith("총 ") and "복기" in text:
        return True
    if text.startswith("202") and ("학년도" in text or "PDS" in text):
        return True
    if text.startswith("201") and ("학년도" in text or "PDS" in text):
        return True
    if text.startswith("* "):
        return True
    return False


def write_quiz(spec: ExamSpec, source_path: Path, answer_path: Path, questions: list[dict]) -> None:
    payload = {
        "title": spec.title,
        "kind": spec.kind,
        "sourceFile": source_path.name,
        "answerFile": answer_path.name if answer_path else "",
        "notes": spec.notes,
        "questions": questions,
    }
    out = Y_DIR / spec.output
    out.write_text(render_template(payload), encoding="utf-8")


def render_template(payload: dict) -> str:
    data = json.dumps(payload, ensure_ascii=False)
    title = html.escape(payload["title"])
    source_file = html.escape(payload.get("sourceFile", ""))
    answer_file = html.escape(payload.get("answerFile", ""))
    notes = html.escape(payload.get("notes", ""))
    return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{title} 퀴즈</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f3f5f8;
      --panel: #ffffff;
      --ink: #182230;
      --muted: #667085;
      --line: #d6dce6;
      --blue: #2563eb;
      --blue-soft: #eaf1ff;
      --green: #07875f;
      --green-soft: #e8f7f0;
      --red: #c23b3b;
      --red-soft: #fff0f0;
      --amber: #9a6700;
      --amber-soft: #fff7dd;
      --navy: #111827;
      --shadow: 0 18px 45px rgba(17, 24, 39, 0.08);
      --soft-shadow: 0 8px 22px rgba(17, 24, 39, 0.06);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: radial-gradient(circle at 20% -10%, rgba(37, 99, 235, 0.12), transparent 34%), linear-gradient(180deg, #f8fafc 0%, var(--bg) 260px);
      color: var(--ink);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans KR", sans-serif;
      line-height: 1.55;
    }}
    button, select, input {{ font: inherit; }}
    .shell {{ width: min(1160px, calc(100% - 32px)); margin: 0 auto; }}
    header {{ padding: 38px 0 24px; background: rgba(255,255,255,.78); border-bottom: 1px solid var(--line); backdrop-filter: blur(14px); }}
    .eyebrow {{ margin: 0 0 6px; color: var(--blue); font-weight: 800; font-size: .86rem; }}
    h1 {{ margin: 0; color: var(--navy); font-size: clamp(1.7rem, 4vw, 2.6rem); line-height: 1.15; letter-spacing: 0; }}
    .summary {{ max-width: 780px; margin: 12px 0 0; color: var(--muted); }}
    .status {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; margin-top: 24px; }}
    .metric {{ min-height: 92px; padding: 16px; border: 1px solid var(--line); border-radius: 8px; background: rgba(255,255,255,.88); box-shadow: var(--soft-shadow); }}
    .metric span {{ display: block; color: var(--muted); font-size: .84rem; }}
    .metric strong {{ display: block; margin-top: 6px; color: var(--navy); font-size: 1.65rem; line-height: 1.1; }}
    .toolbar-band {{ position: sticky; top: 0; z-index: 10; padding: 10px 0; background: rgba(243,245,248,.92); border-bottom: 1px solid var(--line); backdrop-filter: blur(12px); }}
    .toolbar {{ display: grid; grid-template-columns: minmax(220px, 1.3fr) minmax(180px, .8fr) auto auto auto; gap: 8px; align-items: center; padding: 8px; border: 1px solid rgba(214,220,230,.9); border-radius: 8px; background: rgba(255,255,255,.86); box-shadow: var(--soft-shadow); }}
    .control {{ display: grid; gap: 5px; }}
    .control span {{ color: var(--muted); font-size: .78rem; font-weight: 800; }}
    input[type="search"], select {{ width: 100%; min-height: 42px; border: 1px solid var(--line); border-radius: 7px; background: #fff; color: var(--ink); padding: 0 12px; outline: none; }}
    input[type="search"]:focus, select:focus {{ border-color: var(--blue); box-shadow: 0 0 0 3px rgba(37,99,235,.14); }}
    .tool-button {{ min-height: 42px; border: 1px solid var(--line); border-radius: 7px; background: #fff; color: var(--ink); padding: 0 14px; cursor: pointer; white-space: nowrap; }}
    .tool-button.primary {{ border-color: var(--blue); background: var(--blue); color: #fff; font-weight: 800; }}
    main.shell {{ display: grid; grid-template-columns: 280px minmax(0, 1fr); gap: 18px; align-items: start; padding: 24px 0 48px; }}
    .source-board {{ position: sticky; top: 92px; display: grid; gap: 8px; max-height: calc(100vh - 112px); overflow: auto; border: 1px solid var(--line); border-radius: 8px; background: rgba(255,255,255,.9); padding: 10px; box-shadow: var(--soft-shadow); }}
    .source-chip {{ border: 1px solid var(--line); border-radius: 8px; background: #fff; padding: 12px; cursor: pointer; text-align: left; transition: border-color .15s ease, background .15s ease, transform .15s ease; }}
    .source-chip:hover {{ border-color: rgba(37,99,235,.55); transform: translateY(-1px); }}
    .source-chip[aria-pressed="true"] {{ border-color: var(--blue); background: var(--blue-soft); box-shadow: inset 3px 0 0 var(--blue); }}
    .source-chip strong {{ display: block; font-size: .92rem; line-height: 1.35; }}
    .source-chip span {{ display: block; margin-top: 5px; color: var(--muted); font-size: .8rem; }}
    .quiz-list {{ display: grid; gap: 14px; }}
    .question-card {{ border: 1px solid var(--line); border-radius: 8px; background: var(--panel); box-shadow: var(--shadow); overflow: hidden; }}
    .question-card.correct {{ border-color: rgba(7,135,95,.55); }}
    .question-card.incorrect {{ border-color: rgba(194,59,59,.55); }}
    .question-head {{ display: flex; flex-wrap: wrap; gap: 8px; align-items: center; justify-content: space-between; padding: 13px 16px; background: linear-gradient(180deg, #fff, #f8fafc); border-bottom: 1px solid var(--line); }}
    .q-number {{ display: inline-grid; place-items: center; min-width: 42px; height: 30px; border-radius: 999px; background: var(--navy); color: #fff; font-weight: 800; }}
    .badges {{ display: flex; flex-wrap: wrap; gap: 6px; align-items: center; }}
    .badge {{ display: inline-flex; align-items: center; min-height: 26px; border-radius: 999px; padding: 0 9px; background: #eef2f7; color: #34435a; font-size: .78rem; font-weight: 800; }}
    .badge.source {{ background: var(--blue-soft); color: #174ea6; }}
    .badge.warning {{ background: var(--amber-soft); color: var(--amber); }}
    .question-body {{ padding: 18px; }}
    .stem {{ margin: 0 0 16px; white-space: pre-line; font-weight: 650; color: #202b3c; }}
    .options {{ display: grid; gap: 9px; }}
    .option {{ display: grid; grid-template-columns: 30px 1fr; gap: 11px; align-items: start; width: 100%; min-height: 50px; border: 1px solid var(--line); border-radius: 8px; background: #fff; padding: 11px 13px; color: var(--ink); text-align: left; cursor: pointer; transition: border-color .15s ease, background .15s ease, transform .15s ease; }}
    .option:hover {{ border-color: var(--blue); background: #fbfdff; transform: translateY(-1px); }}
    .option.selected {{ border-color: var(--blue); background: var(--blue-soft); }}
    .option.answer {{ border-color: var(--green); background: var(--green-soft); }}
    .option.wrong {{ border-color: var(--red); background: var(--red-soft); }}
    .mark {{ display: inline-grid; place-items: center; width: 28px; height: 28px; border-radius: 999px; background: #eef2f7; font-weight: 800; color: #364152; }}
    .feedback {{ display: none; margin-top: 14px; border-radius: 8px; padding: 12px; font-size: .92rem; }}
    .feedback.visible {{ display: block; }}
    .feedback.correct {{ background: var(--green-soft); color: var(--green); }}
    .feedback.incorrect {{ background: var(--red-soft); color: var(--red); }}
    .feedback.pending {{ background: var(--amber-soft); color: var(--amber); }}
    .empty {{ padding: 28px; border: 1px dashed var(--line); border-radius: 8px; background: #fff; color: var(--muted); text-align: center; }}
    footer {{ padding: 24px 0 36px; color: var(--muted); border-top: 1px solid var(--line); background: #fff; font-size: .9rem; }}
    @media (max-width: 980px) {{ main.shell {{ grid-template-columns: 1fr; }} .source-board {{ position: static; max-height: none; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); }} }}
    @media (max-width: 900px) {{ .status {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }} .toolbar {{ grid-template-columns: 1fr 1fr; }} .toolbar .tool-button {{ width: 100%; }} }}
    @media (max-width: 620px) {{ .shell {{ width: min(100% - 20px, 1160px); }} .status, .toolbar {{ grid-template-columns: 1fr; }} .question-head {{ align-items: flex-start; }} }}
  </style>
</head>
<body>
  <header>
    <div class="shell">
      <p class="eyebrow">PDS4 CBT 복기</p>
      <h1>{title}</h1>
      <p class="summary">문항마다 추출된 출처 강의를 붙였습니다. 강의 필터를 고르면 해당 범위 문제만 풀 수 있고, 선택 즉시 정답 여부가 표시됩니다.</p>
      <div class="status" aria-live="polite">
        <div class="metric"><span>전체 문항</span><strong id="total-count">0</strong></div>
        <div class="metric"><span>현재 범위</span><strong id="visible-count">0</strong></div>
        <div class="metric"><span>푼 문항</span><strong id="answered-count">0</strong></div>
        <div class="metric"><span>정답률</span><strong id="score-rate">0%</strong></div>
      </div>
    </div>
  </header>
  <section class="toolbar-band">
    <div class="shell toolbar">
      <label class="control"><span>검색</span><input id="search-input" type="search" placeholder="문항, 보기, 강의명 검색" autocomplete="off" /></label>
      <label class="control"><span>출처 강의</span><select id="source-select"></select></label>
      <button id="toggle-unanswered" class="tool-button" type="button" aria-pressed="false">미풀이만</button>
      <button id="show-answers" class="tool-button" type="button">정답 표시</button>
      <button id="reset" class="tool-button primary" type="button">초기화</button>
    </div>
  </section>
  <main class="shell">
    <section class="source-board" id="source-board" aria-label="출처 강의별 필터"></section>
    <section class="quiz-list" id="quiz-list" aria-label="퀴즈 문항"></section>
  </main>
  <footer>
    <div class="shell">원본: {source_file}{(" / 정답 표시 파일: " + answer_file) if answer_file and answer_file != source_file else ""}{(" / " + notes) if notes else ""}</div>
  </footer>
  <script>
    const examData = {data};
    const questions = examData.questions || [];
    questions.forEach(question => {{
      question.shuffledOptions = shuffleOptions(question.options.map((text, index) => ({{
        text,
        originalNumber: index + 1,
        correct: question.answers.includes(index + 1)
      }})));
    }});
    const state = {{ source: "전체", query: "", onlyUnanswered: false, selections: new Map(), showAnswers: false }};
    const els = {{
      totalCount: document.querySelector("#total-count"),
      visibleCount: document.querySelector("#visible-count"),
      answeredCount: document.querySelector("#answered-count"),
      scoreRate: document.querySelector("#score-rate"),
      searchInput: document.querySelector("#search-input"),
      sourceSelect: document.querySelector("#source-select"),
      sourceBoard: document.querySelector("#source-board"),
      quizList: document.querySelector("#quiz-list"),
      toggleUnanswered: document.querySelector("#toggle-unanswered"),
      showAnswers: document.querySelector("#show-answers"),
      reset: document.querySelector("#reset")
    }};
    const numberMarks = ["①", "②", "③", "④", "⑤", "⑥", "⑦", "⑧", "⑨"];
    function init() {{ els.totalCount.textContent = String(questions.length); renderSourceControls(); bindEvents(); render(); }}
    function bindEvents() {{
      els.searchInput.addEventListener("input", event => {{ state.query = event.target.value.trim(); render(); }});
      els.sourceSelect.addEventListener("change", event => {{ state.source = event.target.value; render(); }});
      els.toggleUnanswered.addEventListener("click", () => {{ state.onlyUnanswered = !state.onlyUnanswered; els.toggleUnanswered.setAttribute("aria-pressed", String(state.onlyUnanswered)); els.toggleUnanswered.textContent = state.onlyUnanswered ? "전체 보기" : "미풀이만"; render(); }});
      els.showAnswers.addEventListener("click", () => {{ state.showAnswers = !state.showAnswers; els.showAnswers.textContent = state.showAnswers ? "정답 숨김" : "정답 표시"; render(); }});
      els.reset.addEventListener("click", () => {{ state.selections.clear(); state.showAnswers = false; els.showAnswers.textContent = "정답 표시"; render(); }});
    }}
    function renderSourceControls() {{
      const sources = ["전체", ...Array.from(new Set(questions.map(item => item.source || "출처 미분류")))];
      els.sourceSelect.replaceChildren(...sources.map(source => {{ const option = document.createElement("option"); option.value = source; option.textContent = source === "전체" ? "전체 강의" : source; return option; }}));
    }}
    function render() {{ const visible = getVisibleQuestions(); els.visibleCount.textContent = String(visible.length); renderStats(); renderSourceBoard(); renderQuestions(visible); }}
    function renderStats() {{ const answered = questions.filter(question => state.selections.has(question.id)); const scored = answered.filter(question => !question.uncertain); const correct = scored.filter(question => isCorrect(question, state.selections.get(question.id))).length; els.answeredCount.textContent = String(answered.length); els.scoreRate.textContent = scored.length ? `${{Math.round((correct / scored.length) * 100)}}%` : "0%"; }}
    function getVisibleQuestions() {{
      const normalizedQuery = normalize(state.query);
      return questions.filter(question => {{
        const source = question.source || "출처 미분류";
        const sourceOk = state.source === "전체" || source === state.source;
        const unansweredOk = !state.onlyUnanswered || !state.selections.has(question.id);
        const queryOk = !normalizedQuery || normalize([question.stem, source, question.professor, question.options.join(" ")].join(" ")).includes(normalizedQuery);
        return sourceOk && unansweredOk && queryOk;
      }});
    }}
    function renderSourceBoard() {{
      const grouped = questions.reduce((map, question) => {{ const source = question.source || "출처 미분류"; map.set(source, (map.get(source) || 0) + 1); return map; }}, new Map());
      els.sourceBoard.replaceChildren(createSourceButton("전체", questions.length), ...Array.from(grouped, ([source, count]) => createSourceButton(source, count)));
    }}
    function createSourceButton(source, count) {{
      const button = document.createElement("button"); button.type = "button"; button.className = "source-chip"; button.setAttribute("aria-pressed", String(state.source === source));
      button.innerHTML = `<strong>${{escapeHtml(source === "전체" ? "전체 강의" : source)}}</strong><span>${{count}}문항</span>`;
      button.addEventListener("click", () => {{ state.source = source; els.sourceSelect.value = source; render(); }});
      return button;
    }}
    function renderQuestions(items) {{
      if (!items.length) {{ els.quizList.innerHTML = `<div class="empty">현재 조건에 맞는 문항이 없습니다.</div>`; return; }}
      els.quizList.replaceChildren(...items.map(createQuestionCard));
    }}
    function createQuestionCard(question) {{
      const selected = state.selections.get(question.id); const answered = Number.isInteger(selected); const correct = answered && isCorrect(question, selected); const reveal = state.showAnswers || answered;
      const card = document.createElement("article"); card.className = "question-card"; if (answered) card.classList.add(correct ? "correct" : "incorrect");
      const badges = [`<span class="badge source">${{escapeHtml(question.source || "출처 미분류")}}</span>`]; if (question.professor) badges.push(`<span class="badge">${{escapeHtml(question.professor)}}</span>`); if (question.provisional) badges.push(`<span class="badge warning">임시 정답</span>`); if (question.uncertain) badges.push(`<span class="badge warning">검토 필요</span>`);
      card.innerHTML = `<div class="question-head"><span class="q-number">Q${{question.id}}</span><div class="badges">${{badges.join("")}}</div></div><div class="question-body"><p class="stem">${{escapeHtml(question.stem)}}</p><div class="options"></div><div class="feedback"></div></div>`;
      const optionWrap = card.querySelector(".options");
      optionWrap.replaceChildren(...question.shuffledOptions.map((option, index) => {{
        const isSelected = selected === option.originalNumber; const isAnswer = option.correct; const button = document.createElement("button"); button.type = "button"; button.className = "option";
        if (isSelected) button.classList.add("selected"); if (reveal && isAnswer) button.classList.add("answer"); if (answered && isSelected && !isAnswer) button.classList.add("wrong");
        button.innerHTML = `<span class="mark">${{numberMarks[index] || String(index + 1)}}</span><span>${{escapeHtml(option.text)}}</span>`;
        button.addEventListener("click", () => {{ state.selections.set(question.id, option.originalNumber); render(); document.querySelector(`[data-question-id="${{question.id}}"]`)?.scrollIntoView({{ block: "nearest" }}); }});
        return button;
      }}));
      card.dataset.questionId = String(question.id);
      const feedback = card.querySelector(".feedback");
      if (reveal) {{
        const answerText = question.shuffledOptions.map((option, index) => ({{ option, index }})).filter(item => item.option.correct).map(item => `${{numberMarks[item.index] || String(item.index + 1)}} ${{item.option.text}}`).join(" / ");
        const stateLabel = question.uncertain ? (answered ? (correct ? "임시 후보와 일치" : "임시 후보와 다름") : "임시 정답 후보") : (answered ? (correct ? "정답" : "오답") : "정답");
        const feedbackClass = question.uncertain ? "pending" : (answered ? (correct ? "correct" : "incorrect") : "pending");
        feedback.className = `feedback visible ${{feedbackClass}}`;
        feedback.innerHTML = `<strong>${{stateLabel}}</strong><div>${{answerText ? `정답 후보: ${{escapeHtml(answerText)}}` : "정답 표시를 자동으로 확인하지 못했습니다."}}</div>${{question.note ? `<div>${{escapeHtml(question.note)}}</div>` : ""}}`;
      }}
      return card;
    }}
    function isCorrect(question, selected) {{ return question.answers.includes(selected); }}
    function shuffleOptions(options) {{ const items = [...options]; for (let index = items.length - 1; index > 0; index -= 1) {{ const swapIndex = Math.floor(Math.random() * (index + 1)); [items[index], items[swapIndex]] = [items[swapIndex], items[index]]; }} return items; }}
    function normalize(value) {{ return String(value || "").toLowerCase().replace(/\\s+/g, " ").trim(); }}
    function escapeHtml(value) {{ return String(value || "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;"); }}
    init();
  </script>
</body>
</html>
"""


if __name__ == "__main__":
    main()
