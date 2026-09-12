#!/usr/bin/env python3
"""Download and clean University of Ljubljana study-programme data.

The generated JSON is used by the static GitHub Pages front-end. Only
"Univerzitetni" and "Enoviti magistrski" programmes are retained.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup, Tag
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

BASE_URL = "https://www.uni-lj.si"
CATALOG_URL = (
    "https://www.uni-lj.si/studij/dodiplomski-in-enoviti-magistrski-studij/"
    "programi-dodiplomskega-in-enovitega-magistrskega-studija"
)
ALLOWED_TYPES = {"Univerzitetni", "Enoviti magistrski"}
DEFAULT_OUTPUT = Path(__file__).resolve().parents[1] / "data" / "programs.json"
PROGRAM_PATH_RE = re.compile(r"^/programi/[^/?#]+/?$")

BASIC_LABELS = {
    "Vrsta študijskega programa",
    "Trajanje v letih",
    "Št. ECTS kreditnih točk",
    "Članica UL",
    "Opis programa",
}

DESCRIPTION_STOPS = (
    "Smeri",
    "Strokovni naslov",
    "Angleško poimenovanje strokovnega naslova",
    "Pogoji za vpis",
    "Merila za izbiro ob omejitvi vpisa",
)

SECTION_STOPS = (
    "Hitre povezave",
    "Kontakt",
    "Družbena omrežja",
)

IRRELEVANT_CRITERIA_STARTS = (
    "kandidati, ki se vpisujejo v višji letnik",
    "kandidati za vpis v višji letnik",
    "pri izbiri kandidatov za vpis v višji letnik",
    "kandidati za prehode",
    "merila za prehode",
)


def clean_text(value: str) -> str:
    value = value.replace("\xa0", " ").replace("\u200b", " ")
    return re.sub(r"\s+", " ", value).strip()


def clean_ui_prefix(value: str) -> str:
    value = clean_text(value)
    value = re.sub(r"^Odpri razdelek:\s*Zapri razdelek:\s*", "", value, flags=re.I)
    return value.strip()


def content_root(soup: BeautifulSoup) -> Tag:
    return soup.find("main") or soup.find(id="main-content") or soup.body or soup


def string_lines(root: Tag) -> list[str]:
    lines: list[str] = []
    for piece in root.stripped_strings:
        text = clean_ui_prefix(str(piece))
        if text:
            lines.append(text)
    return lines


def block_lines(root: Tag) -> list[str]:
    """Return readable block-level text while preserving list markers."""
    accepted = {"h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "dt", "dd", "button", "summary"}
    result: list[str] = []
    for tag in root.find_all(accepted):
        # Avoid duplicate text from a <p> nested inside a <li>, etc.
        if tag.find_parent(accepted):
            parent = tag.find_parent(accepted)
            if parent is not None and parent.name in {"li", "p", "dt", "dd"}:
                continue
        text = clean_ui_prefix(tag.get_text(" ", strip=True))
        if not text:
            continue
        if tag.name == "li":
            text = f"- {text}"
        result.append(text)
    return result


def value_after_label(lines: list[str], label: str, stop_labels: Iterable[str]) -> str:
    for index, line in enumerate(lines):
        if line == label:
            values: list[str] = []
            for candidate in lines[index + 1 :]:
                if candidate in stop_labels or any(candidate.startswith(stop) for stop in stop_labels):
                    break
                if candidate.startswith("Odpri razdelek"):
                    continue
                values.append(candidate)
            return ", ".join(values)
    return ""


def extract_section(
    blocks: list[str],
    heading_starts_with: str,
    stop_prefixes: Iterable[str],
) -> list[str]:
    start = None
    for i, line in enumerate(blocks):
        if clean_ui_prefix(line).startswith(heading_starts_with):
            start = i + 1
            break
    if start is None:
        return []

    result: list[str] = []
    for line in blocks[start:]:
        cleaned = clean_ui_prefix(line)
        if any(cleaned.startswith(prefix) for prefix in stop_prefixes):
            break
        if cleaned:
            result.append(cleaned)
    return result


def normalize_bullet(line: str) -> str:
    line = clean_text(line)
    line = re.sub(r"^[–−•]\s*", "- ", line)
    line = re.sub(r"^-\s*", "- ", line)
    return line


def candidate_group_letters(line: str) -> set[str]:
    lower = clean_text(line).lower()
    if "kandidat" not in lower:
        return set()
    if "točk" in lower or "točke" in lower or "točka" in lower:
        return set(re.findall(r"\b([a-z])\)", lower))
    if "splošn" in lower and "matur" in lower:
        return {"a"}
    return set()


def general_matura_criteria(section_lines: list[str]) -> list[str]:
    """Keep only selection criteria that apply to a general-matura candidate."""
    lines = [normalize_bullet(line) for line in section_lines if clean_text(line)]
    if not lines:
        return []

    # Stop when a programme switches to rules for transfers/higher-year entry.
    trimmed: list[str] = []
    for line in lines:
        lower = line.lower().lstrip("- ")
        if any(lower.startswith(prefix) for prefix in IRRELEVANT_CRITERIA_STARTS):
            break
        if lower.startswith("merila za izbiro ob omejitvi vpisa"):
            break
        if lower in {"več", "več..."}:
            break
        trimmed.append(line)
    lines = trimmed

    group_headers: list[tuple[int, set[str]]] = []
    for i, line in enumerate(lines):
        letters = candidate_group_letters(line)
        if letters:
            group_headers.append((i, letters))

    if group_headers:
        for header_pos, (start_index, letters) in enumerate(group_headers):
            if "a" not in letters:
                continue
            end_index = group_headers[header_pos + 1][0] if header_pos + 1 < len(group_headers) else len(lines)
            selected = lines[start_index + 1 : end_index]
            return cleanup_criteria(selected)
        return []

    # Shared criteria: remove generic introductory prose before the actual criteria.
    start = 0
    for i, line in enumerate(lines):
        stripped = line.lstrip("- ").lower()
        if line.startswith("- "):
            start = i
            break
        if "izbrani glede na" in stripped or "izbran glede na" in stripped:
            start = i + 1
            break
    return cleanup_criteria(lines[start:])


def cleanup_criteria(lines: list[str]) -> list[str]:
    result: list[str] = []
    for line in lines:
        text = normalize_bullet(line)
        lower = text.lower().lstrip("- ")
        if not text:
            continue
        if lower.startswith("če bo sprejet sklep o omejitvi vpisa"):
            continue
        if candidate_group_letters(text):
            continue
        if lower.startswith("kandidati iz točke b") or lower.startswith("kandidati iz točk b"):
            break
        if not text.startswith("- ") and "%" in text and not text.endswith(":"):
            text = f"- {text}"
        result.append(text)
    return result


def programme_title(soup: BeautifulSoup, url: str) -> str:
    root = content_root(soup)
    h1 = root.find("h1")
    if h1:
        title = clean_text(h1.get_text(" ", strip=True))
        if title:
            return title
    if soup.title and soup.title.string:
        return clean_text(soup.title.string.split("|")[0])
    return urlparse(url).path.rstrip("/").rsplit("/", 1)[-1].replace("-", " ").title()


def parse_programme_html(html: str, url: str) -> dict[str, object] | None:
    soup = BeautifulSoup(html, "html.parser")
    root = content_root(soup)
    strings = string_lines(root)
    blocks = block_lines(root)

    programme_type = value_after_label(
        strings,
        "Vrsta študijskega programa",
        {"Trajanje v letih"},
    )
    if programme_type not in ALLOWED_TYPES:
        return None

    duration_raw = value_after_label(
        strings,
        "Trajanje v letih",
        {"Št. ECTS kreditnih točk", "Članica UL"},
    )
    duration_match = re.search(r"\d+(?:[.,]\d+)?", duration_raw)
    duration: int | float | str
    if duration_match:
        number = duration_match.group(0).replace(",", ".")
        duration = int(float(number)) if float(number).is_integer() else float(number)
    else:
        duration = duration_raw

    faculty = value_after_label(
        strings,
        "Članica UL",
        {"Opis programa", "Smeri", "Strokovni naslov", "Pogoji za vpis"},
    )

    description = extract_section(blocks, "Opis programa", DESCRIPTION_STOPS)
    if not description:
        fallback_description = extract_section(strings, "Opis programa", DESCRIPTION_STOPS)
        if fallback_description:
            description = [clean_text(" ".join(fallback_description))]

    criteria_section = extract_section(
        blocks,
        "Merila za izbiro ob omejitvi vpisa",
        (*SECTION_STOPS, "Merila za izbiro ob omejitvi vpisa"),
    )
    if not criteria_section:
        criteria_section = extract_section(
            strings,
            "Merila za izbiro ob omejitvi vpisa",
            (*SECTION_STOPS, "Merila za izbiro ob omejitvi vpisa"),
        )
    criteria = general_matura_criteria(criteria_section)

    path = urlparse(url).path.rstrip("/")
    programme_id = path.rsplit("/", 1)[-1]
    return {
        "id": programme_id,
        "faculty": faculty,
        "name": programme_title(soup, url),
        "type": programme_type,
        "duration": duration,
        "description": description,
        "criteriaGeneralMatura": criteria,
        "sourceUrl": url,
    }


def programme_urls_from_catalogue(html: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    urls: set[str] = set()
    for anchor in soup.find_all("a", href=True):
        absolute = urljoin(BASE_URL, anchor["href"])
        parsed = urlparse(absolute)
        if parsed.netloc not in {"www.uni-lj.si", "uni-lj.si"}:
            continue
        if PROGRAM_PATH_RE.match(parsed.path):
            canonical = f"https://www.uni-lj.si{parsed.path.rstrip('/')}"
            urls.add(canonical)
    return sorted(urls)


def make_session() -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=4,
        connect=4,
        read=4,
        backoff_factor=0.6,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET",),
    )
    session.mount("https://", HTTPAdapter(max_retries=retry))
    session.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 (compatible; ULStudyProgrammeBrowser/1.0; "
                "+https://github.com/)"
            ),
            "Accept-Language": "sl,en;q=0.8",
        }
    )
    return session


def fetch(session: requests.Session, url: str, timeout: float) -> str:
    response = session.get(url, timeout=timeout)
    response.raise_for_status()
    response.encoding = response.apparent_encoding or response.encoding
    return response.text


def update_data(output: Path, delay: float, timeout: float, min_programs: int) -> dict[str, object]:
    session = make_session()
    print(f"Fetching catalogue: {CATALOG_URL}")
    catalogue_html = fetch(session, CATALOG_URL, timeout)
    urls = programme_urls_from_catalogue(catalogue_html)
    if not urls:
        raise RuntimeError("No programme links were found in the UL catalogue page.")
    print(f"Found {len(urls)} undergraduate/integrated programme links.")

    programmes: list[dict[str, object]] = []
    errors: list[dict[str, str]] = []
    for index, url in enumerate(urls, start=1):
        try:
            html = fetch(session, url, timeout)
            programme = parse_programme_html(html, url)
            if programme is not None:
                programmes.append(programme)
                criteria_count = len(programme["criteriaGeneralMatura"])
                if criteria_count == 0:
                    pass
                    # print(f"  warning: no general-matura criteria parsed for {programme['name']}", file=sys.stderr)
        except Exception as exc:  # Keep other pages usable and report failures.
            errors.append({"url": url, "error": str(exc)})
            print(f"  error: {url}: {exc}", file=sys.stderr)
        if index < len(urls) and delay:
            time.sleep(delay)

    programmes.sort(key=lambda item: (str(item["faculty"]).casefold(), str(item["name"]).casefold()))
    if len(programmes) < min_programs:
        raise RuntimeError(
            f"Only {len(programmes)} matching programmes were parsed; expected at least {min_programs}. "
            "The UL page structure may have changed."
        )

    payload: dict[str, object] = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "isSample": False,
        "source": {
            "catalogue": CATALOG_URL,
            "programmeCatalogue": f"{BASE_URL}/programi",
        },
        "programTypes": sorted(ALLOWED_TYPES),
        "programs": programmes,
        "scrapeErrors": errors,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(programmes)} programmes to {output}")
    if errors:
        print(f"Completed with {len(errors)} page errors.", file=sys.stderr)
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Output JSON path")
    parser.add_argument("--delay", type=float, default=0.10, help="Delay between programme requests in seconds")
    parser.add_argument("--timeout", type=float, default=30.0, help="HTTP timeout per request in seconds")
    parser.add_argument("--min-programs", type=int, default=40, help="Safety check for the minimum parsed programme count")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        update_data(args.output, args.delay, args.timeout, args.min_programs)
    except Exception as exc:
        print(f"update_data.py failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
