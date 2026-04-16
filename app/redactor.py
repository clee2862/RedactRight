from __future__ import annotations

import io
from collections import Counter
import re
from dataclasses import dataclass
from typing import Any

import fitz


PATTERNS = {
    "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    "phone": re.compile(r"\b(?:\+?1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)\d{3}[-.\s]?\d{4}\b"),
    "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "credit_card": re.compile(r"\b(?:\d[ -]*?){13,16}\b"),
    "ip_address": re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
}
DETECTOR_KEYS = tuple(PATTERNS.keys()) + ("person_name",)
PERSON_NAME_PATTERNS = (
    re.compile(r"\b[A-Z][a-z]+,\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2}\b"),
    re.compile(r"\b[A-Z][a-z]+(?:[-'][A-Z][a-z]+)?(?:\s+[A-Z][a-z]+(?:[-'][A-Z][a-z]+)?){1,3}\b"),
    re.compile(r"\b[A-Z]{2,}(?:\s+[A-Z]{2,}){1,3}\b"),
)
INLINE_NAME_CUE_PATTERNS = (
    re.compile(r"\bHello\s+([A-Z][A-Za-z'-]+(?:\s+[A-Z][A-Za-z'-]+){1,3}|[A-Z]{2,}(?:\s+[A-Z]{2,}){1,3})\b"),
    re.compile(r"\b(?:by|for|to|from|attn\.?|attention|payee|employee|person|name)\s+([A-Z][A-Za-z'-]+(?:\s+[A-Z][A-Za-z'-]+){1,3})\b"),
)
NAME_LABEL_CUES = {
    "person",
    "name",
    "employee",
    "customer",
    "payee",
    "bill to",
    "ship to",
    "submitted by",
    "approved by",
    "prepared by",
}
PERSON_NAME_STOPWORDS = {
    "account",
    "amount",
    "approved",
    "banking",
    "bill",
    "biller",
    "business",
    "class",
    "code",
    "confirmation",
    "credit",
    "date",
    "description",
    "expense",
    "funds",
    "fusion",
    "global",
    "internet",
    "invoice",
    "item",
    "items",
    "kuala",
    "limit",
    "lumpur",
    "missing",
    "oracle",
    "original",
    "other",
    "overview",
    "payable",
    "personal",
    "persekutuan",
    "policy",
    "receipt",
    "report",
    "required",
    "source",
    "submission",
    "tax",
    "technology",
    "template",
    "total",
    "travel",
    "type",
    "wilayah",
    "you",
    "your",
}
PERSON_NAME_EXCLUSIONS = {
    "Access Review",
    "Access Reviews",
    "Action Item",
    "Action Items",
    "Audit Date",
    "Billing Address",
    "Credit Card",
    "Customer Name",
    "Due Date",
    "Email Address",
    "Expense Report",
    "Findings Report",
    "Home Address",
    "Independent Assessment",
    "Invoice Number",
    "Ip Address",
    "Mobile Banking",
    "Original Receipt",
    "Other Important Instructions",
    "Phone Number",
    "Platform Team",
    "Receipt Required",
    "Receipt Submission Instructions",
    "Report Number",
    "Report Status",
    "Reporting Period",
    "Security Team",
    "Submission Date",
    "Total Amount",
    "Total Amount Payable",
}


@dataclass
class RedactionResult:
    source_text: str
    redacted_text: str
    counts: dict[str, int]
    findings: list[dict[str, Any]]
    redacted_file: bytes | None = None


def _replacement_label(key: str) -> str:
    return f"[{key.upper()}_REDACTED]"


def _normalize_custom_terms(custom_terms: list[str] | None) -> list[str]:
    if not custom_terms:
        return []

    seen: set[str] = set()
    normalized: list[str] = []
    for term in custom_terms:
        clean = term.strip()
        if not clean:
            continue
        lowered = clean.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        normalized.append(clean)
    return normalized


def _active_patterns(
    enabled: dict[str, bool],
    custom_terms: list[str] | None = None,
    person_name_terms: list[str] | None = None,
) -> list[tuple[str, re.Pattern[str], str | None]]:
    active: list[tuple[str, re.Pattern[str], str | None]] = []
    for key, pattern in PATTERNS.items():
        if enabled.get(key, True):
            active.append((key, pattern, None))

    for term in _normalize_custom_terms(custom_terms):
        active.append(("custom_term", re.compile(re.escape(term), re.IGNORECASE), term))

    for term in _normalize_custom_terms(person_name_terms):
        active.append(("person_name", re.compile(re.escape(term), re.IGNORECASE), term))

    return active


def _should_keep_name_candidate(value: str) -> bool:
    candidate = " ".join(value.strip().split())
    if not candidate:
        return False
    if any(char.isdigit() for char in candidate):
        return False
    if candidate in PERSON_NAME_EXCLUSIONS:
        return False

    words = candidate.replace(",", " ").split()
    if len(words) < 2 or len(words) > 4:
        return False
    if candidate.isupper() and any(len(word) == 1 for word in words):
        return False
    lowered_words = [word.strip(",").lower() for word in words]
    if any(word in PERSON_NAME_STOPWORDS for word in lowered_words):
        return False
    return True


def detect_person_name_candidates(text: str) -> list[str]:
    counts: Counter[str] = Counter()
    canonical: dict[str, str] = {}

    def add_candidate(value: str) -> None:
        candidate = " ".join(value.strip().split())
        if not _should_keep_name_candidate(candidate):
            return
        key = candidate.lower()
        counts[key] += 1
        canonical.setdefault(key, candidate)

    lines = [line.strip() for line in text.splitlines()]
    previous_nonempty = ""

    for line in lines:
        if not line:
            continue

        for match in PERSON_NAME_PATTERNS[0].finditer(line):
            add_candidate(match.group(0))

        for pattern in INLINE_NAME_CUE_PATTERNS:
            for match in pattern.finditer(line):
                add_candidate(match.group(1))

        normalized_previous = previous_nonempty.lower().rstrip(":")
        if normalized_previous in NAME_LABEL_CUES:
            candidate_line = re.sub(r"\s*\(\d+\)\s*$", "", line).strip()
            if candidate_line:
                add_candidate(candidate_line)

        previous_nonempty = line

    ranked = list(canonical.values())
    ranked.sort(key=lambda item: (-counts[item.lower()], item))
    return ranked[:25]


def redact_text(
    text: str,
    enabled: dict[str, bool],
    custom_terms: list[str] | None = None,
    person_name_terms: list[str] | None = None,
) -> RedactionResult:
    output = text
    counts: dict[str, int] = {key: 0 for key in PATTERNS}
    findings: list[dict[str, Any]] = []

    if custom_terms:
        counts["custom_term"] = 0
    if person_name_terms:
        counts["person_name"] = 0

    for key, pattern, source_term in _active_patterns(enabled, custom_terms, person_name_terms):
        matches = list(pattern.finditer(output))
        counts[key] = counts.get(key, 0) + len(matches)
        for m in matches:
            item = {
                "type": key,
                "start": m.start(),
                "end": m.end(),
                "value": m.group(0),
            }
            if source_term is not None:
                item["source_term"] = source_term
            findings.append(item)

        replacement = _replacement_label(key)
        output = pattern.sub(replacement, output)

    findings.sort(key=lambda item: item["start"])
    return RedactionResult(source_text=text, redacted_text=output, counts=counts, findings=findings)


def _group_words_by_line(words: list[tuple[Any, ...]]) -> list[list[tuple[Any, ...]]]:
    lines: dict[tuple[int, int], list[tuple[Any, ...]]] = {}
    line_order: list[tuple[int, int]] = []

    for word in words:
        key = (int(word[5]), int(word[6]))
        if key not in lines:
            lines[key] = []
            line_order.append(key)
        lines[key].append(word)

    return [sorted(lines[key], key=lambda item: (float(item[0]), float(item[1]))) for key in line_order]


def _line_segments(words: list[tuple[Any, ...]]) -> tuple[str, list[dict[str, Any]]]:
    text_parts: list[str] = []
    segments: list[dict[str, Any]] = []
    cursor = 0

    for index, word in enumerate(words):
        token = str(word[4])
        if index:
            text_parts.append(" ")
            cursor += 1

        start = cursor
        text_parts.append(token)
        cursor += len(token)
        segments.append(
            {
                "start": start,
                "end": cursor,
                "rect": fitz.Rect(float(word[0]), float(word[1]), float(word[2]), float(word[3])),
            }
        )

    return "".join(text_parts), segments


def _rect_for_match(segments: list[dict[str, Any]], start: int, end: int) -> fitz.Rect | None:
    matching = [segment["rect"] for segment in segments if segment["start"] < end and segment["end"] > start]
    if not matching:
        return None

    rect = fitz.Rect(matching[0])
    for item in matching[1:]:
        rect |= item
    return rect


def redact_pdf(
    pdf_bytes: bytes,
    enabled: dict[str, bool],
    custom_terms: list[str] | None = None,
    person_name_terms: list[str] | None = None,
) -> RedactionResult:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    findings: list[dict[str, Any]] = []
    counts = {key: 0 for key in PATTERNS}
    if custom_terms:
        counts["custom_term"] = 0
    if person_name_terms:
        counts["person_name"] = 0
    page_texts: list[str] = []

    try:
        for page_index, page in enumerate(doc):
            page_texts.append(page.get_text("text"))

        combined_text = "\n".join(page_texts)
        active_patterns = _active_patterns(enabled, custom_terms, person_name_terms)

        for page_index, page in enumerate(doc):
            line_groups = _group_words_by_line(page.get_text("words", sort=True))

            for words in line_groups:
                line_text, segments = _line_segments(words)
                if not line_text:
                    continue

                for key, pattern, source_term in active_patterns:
                    for match in pattern.finditer(line_text):
                        rect = _rect_for_match(segments, match.start(), match.end())
                        if rect is None:
                            continue

                        counts[key] += 1
                        findings.append(
                            {
                                "type": key,
                                "page_number": page_index + 1,
                                "value": match.group(0),
                                "bbox": [
                                    round(rect.x0, 2),
                                    round(rect.y0, 2),
                                    round(rect.x1, 2),
                                    round(rect.y1, 2),
                                ],
                            }
                        )
                        if source_term is not None:
                            findings[-1]["source_term"] = source_term
                        page.add_redact_annot(
                            rect,
                            text=_replacement_label(key),
                            fill=(0, 0, 0),
                            text_color=(1, 1, 1),
                        )

            if page.first_annot is not None:
                page.apply_redactions()

        redacted_stream = io.BytesIO()
        doc.save(redacted_stream, garbage=4, deflate=True)
    finally:
        doc.close()

    preview = redact_text(combined_text, enabled, custom_terms, person_name_terms)
    findings.sort(key=lambda item: (item["page_number"], item["bbox"][1], item["bbox"][0]))
    return RedactionResult(
        source_text=combined_text,
        redacted_text=preview.redacted_text,
        counts=counts,
        findings=findings,
        redacted_file=redacted_stream.getvalue(),
    )
