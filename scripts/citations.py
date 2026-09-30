"""Publication citations built from DOI registry records.

Profiles list only DOIs. `update_citations.py` fetches the title, journal and
year of each DOI from Crossref and saves them in data/publications.json; the
site build reads only that file, so it never needs the network and every
citation has the same shape:

    Title. Journal. Year. DOI: 10.x/y

Titles keep italics, subscripts and superscripts (the only tags allowed); all
other markup is removed and everything else is escaped, so the saved title is
safe to put into a page as it is.
"""

from __future__ import annotations

import html
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent
CACHE_FILE = ROOT / "data" / "publications.json"
OVERRIDES_FILE = ROOT / "data" / "citation_overrides.yaml"
USER_AGENT = "aaugs-dp-biosciences-site/1.0 (https://github.com/AAUGS-DP-Biosciences-and-Drug-Research/Home)"
DOI_RE = re.compile(r"10\.[0-9]{4,9}/[\x21-\x7e]+")  # ASCII, no spaces
MAX_PUBLICATIONS = 5
MAX_TEXT_LENGTH = 2000  # longest title or journal name accepted from the registry

# Markup that Crossref titles use for the formatting we keep, mapped to HTML.
_KEPT_TAGS = {"i": "i", "italic": "i", "em": "i", "sub": "sub", "sup": "sup"}
# A tag: "<" directly followed by a name (so "a < b > c" is text); bounded, so hostile input stays fast.
_TAG_RE = re.compile(r"<(/?)(?:[A-Za-z]{1,10}:)?([A-Za-z][A-Za-z0-9]{0,19})(?:\s[^<>]{0,500})?/?>")
_SAFE_TITLE_RE = re.compile(r"</?(?:i|sub|sup)>")
_SPACE_BEFORE_SCRIPT_RE = re.compile(r"\s+(?=<(?:sub|sup)>)")


def check_doi(doi: object) -> str:
    """Return `doi` if it is a bare DOI such as '10.1000/xyz', else raise ValueError."""
    if not isinstance(doi, str) or not DOI_RE.fullmatch(doi) or doi != doi.strip():
        raise ValueError(f"not a bare DOI (expected e.g. 10.1000/xyz, without https://doi.org/ or spaces): {doi!r}")
    return doi


def clean_markup(raw: str) -> str:
    """Escape `raw` for HTML, keeping only italic, subscript and superscript tags.

    Crossref sends titles as text that may contain entities and JATS/HTML tags.
    Other tags (small caps, MathML, ...) are dropped and their text is kept.
    Typographic hyphens (U+2010, U+2011) become plain hyphens, so titles look
    and search the same whichever publisher wrote them, and a space in front of
    a subscript or superscript is removed ("H <sub>2</sub>O" -> "H<sub>2</sub>O").
    The kept tags are balanced: stray closing tags are dropped and open ones
    are closed, so a title can never leak formatting into the rest of the page.
    """
    text = html.unescape(raw).replace("\u2010", "-").replace("\u2011", "-")
    out: list[str] = []
    open_tags: list[str] = []
    pos = 0
    for tag in _TAG_RE.finditer(text):
        out.append(html.escape(text[pos:tag.start()], quote=False))
        pos = tag.end()
        kept = _KEPT_TAGS.get(tag.group(2).lower())
        if kept is None or tag.group(0).endswith("/>"):  # unknown or empty (<i/>) tags
            continue
        if not tag.group(1):
            open_tags.append(kept)
            out.append(f"<{kept}>")
        elif open_tags and open_tags[-1] == kept:
            open_tags.pop()
            out.append(f"</{kept}>")
    out.append(html.escape(text[pos:], quote=False))
    out.extend(f"</{kept}>" for kept in reversed(open_tags))
    return _SPACE_BEFORE_SCRIPT_RE.sub("", " ".join("".join(out).split()))


def plain(marked_up: str) -> str:
    """Text of a saved title or journal name, without tags or entities."""
    return html.unescape(_SAFE_TITLE_RE.sub("", marked_up))


def _year(date: object) -> int | None:
    """The year of a Crossref date object, or None when it has none."""
    parts = date.get("date-parts") if isinstance(date, dict) else None
    year = parts[0][0] if parts and parts[0] else None
    return year if isinstance(year, int) and not isinstance(year, bool) else None


def entry_from_record(doi: str, record: dict[str, Any]) -> dict[str, Any]:
    """The saved citation fields (title, journal, year) of one Crossref record.

    The year is that of the journal issue (as authors cite it); articles that
    are online only have no print date, so the first online year is used.
    Raises ValueError, naming the DOI, when the record lacks a title, journal or
    year, or has an implausibly long title or journal name.
    """
    titles = record.get("title") or []
    journals = record.get("container-title") or []
    if not journals and record.get("type") == "posted-content":  # preprints: the server
        journals = [inst.get("name", "") for inst in record.get("institution") or []]
    raw_title = titles[0] if titles else ""
    raw_journal = journals[0] if journals else ""
    if len(raw_title) > MAX_TEXT_LENGTH or len(raw_journal) > MAX_TEXT_LENGTH:
        raise ValueError(f"{doi}: the registry title or journal name is longer than {MAX_TEXT_LENGTH} characters")
    year = _year(record.get("published-print")) or _year(record.get("issued"))
    title, journal = clean_markup(raw_title), clean_markup(raw_journal)
    if not title or not journal or year is None:
        raise ValueError(f"{doi}: the registry record has no title, journal or year "
                         f"(title={title!r}, journal={journal!r}, year={year!r})")
    return {"title": title, "journal": journal, "year": year}


def load_overrides(path: Path = OVERRIDES_FILE) -> dict[str, dict[str, Any]]:
    """Hand-written fixes for registry records, keyed by lower-case DOI.

    Each entry may set `title`, `journal` and/or `year`. Raises ValueError for
    anything else, so a typo cannot silently do nothing.
    """
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) if path.is_file() else None
    overrides: dict[str, dict[str, Any]] = {}
    for doi, fields in (raw or {}).items():
        check_doi(doi)
        if not isinstance(fields, dict) or not fields or not set(fields) <= {"title", "journal", "year"}:
            raise ValueError(f"{path.name}: {doi} needs one or more of title, journal, year")
        for field, value in fields.items():
            if field == "year":
                valid = isinstance(value, int) and not isinstance(value, bool)
            else:
                valid = isinstance(value, str) and 0 < len(value.strip()) <= MAX_TEXT_LENGTH
            if not valid:
                raise ValueError(f"{path.name}: {doi}: {field} must be {'a whole number' if field == 'year' else 'non-empty text'}")
        overrides[doi.lower()] = fields
    return overrides


def entry_for(doi: str, record: dict[str, Any], overrides: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """The saved citation fields of `doi`: the registry's, then any override on top."""
    entry = entry_from_record(doi, record)
    for field, value in overrides.get(doi.lower(), {}).items():
        entry[field] = value if field == "year" else clean_markup(str(value))
    return entry


def get_json(url: str, attempts: int = 4) -> dict[str, Any]:
    """Parsed JSON from the Crossref API, retrying network errors and rate limits.

    Only rate limits (429), server errors (5xx) and network failures are retried.
    Raises LookupError for HTTP 404 and RuntimeError for other HTTP errors or
    when the registry stays unreachable.
    """
    last: Exception | None = None
    for attempt in range(attempts):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(request, timeout=40) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            if error.code == 404:
                raise LookupError(f"{url}: not found") from error
            if error.code != 429 and error.code < 500:
                raise RuntimeError(f"Crossref refused the request (HTTP {error.code}): {url}") from error
            last = error
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
            last = error
        time.sleep(3 * (attempt + 1))
    raise RuntimeError(f"Crossref unreachable after {attempts} attempts ({url}): {last}")


def fetch_record(doi: str) -> dict[str, Any]:
    """The Crossref record of `doi`.

    Raises LookupError when Crossref does not know the DOI (other registries,
    such as DataCite, are not supported) and RuntimeError when it is unreachable.
    """
    try:
        return get_json("https://api.crossref.org/works/" + urllib.parse.quote(doi, safe="/"))["message"]
    except LookupError as error:
        raise LookupError(f"{doi}: not registered with Crossref") from error


def load_cache(path: Path = CACHE_FILE, validate: bool = True) -> dict[str, dict[str, Any]]:
    """The saved citations, keyed by lower-case DOI.

    With `validate` (the default) every entry must be complete and its title and
    journal must be exactly what `clean_markup` would produce: saved text is put
    into pages as it is, so a hand-edited or damaged file is refused, not shown.
    """
    if not path.is_file():
        raise FileNotFoundError(f"{path} is missing: run python scripts/update_citations.py")
    cache = json.loads(path.read_text(encoding="utf-8"))
    if not validate:
        return cache
    for doi, entry in cache.items():
        title, journal, year = entry.get("title"), entry.get("journal"), entry.get("year")
        if not (isinstance(title, str) and isinstance(journal, str) and title and journal
                and isinstance(year, int) and not isinstance(year, bool)):
            raise ValueError(f"{path.name}: incomplete entry for {doi}")
        for field in (title, journal):
            if clean_markup(field) != field:
                raise ValueError(f"{path.name}: unexpected markup in the entry for {doi}")
    return cache


def save_cache(cache: dict[str, dict[str, Any]], path: Path = CACHE_FILE) -> None:
    """Write the saved citations, sorted by DOI so that diffs stay small."""
    text = json.dumps(dict(sorted(cache.items())), ensure_ascii=False, indent=1) + "\n"
    path.write_text(text, encoding="utf-8")


def citation_html(doi: str, cache: dict[str, dict[str, Any]]) -> str:
    """The citation of `doi` as HTML: 'Title. Journal. Year. DOI: <link>'.

    Raises KeyError, naming the fix, when the DOI is not in the saved citations.
    """
    entry = cache.get(doi.lower())
    if entry is None:
        raise KeyError(f"{doi} is not in data/publications.json: run python scripts/update_citations.py")
    title = entry["title"]
    stop = "" if plain(title).rstrip().endswith((".", "?", "!", ":", ";", ",", "…")) else "."
    safe_doi = html.escape(doi)
    return (f'{title}{stop} {entry["journal"]}. {entry["year"]}. DOI: '
            f'<a href="https://doi.org/{safe_doi}" target="_blank" rel="noopener">{safe_doi}</a>')
