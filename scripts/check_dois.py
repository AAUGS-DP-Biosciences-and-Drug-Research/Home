"""Check every supervisor publication against its DOI registry record.

For each DOI listed in data/supervisors/*.yaml:
  - the DOI is registered with Crossref
  - the supervisor is among the authors
  - the article is not retracted, withdrawn or flagged with an expression of concern
  - the citation saved in data/publications.json still matches the registry

Usage:  python scripts/check_dois.py [--report report.md]
Exit code 1 if anything needs attention (used by .github/workflows/check-dois.yml).
"""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import difflib
import re
import sys
import unicodedata
import urllib.parse
from collections.abc import Iterator
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from citations import entry_for, get_json, fetch_record, load_cache, load_overrides, plain  # noqa: E402
from gen_supervisors import YAML_DIR, load_entries  # noqa: E402

AUTHOR_MIN = 0.85  # fuzzy match for surnames (publishers misspell names)
BAD_NOTICES = {"retraction": "retracted", "withdrawal": "withdrawn", "expression_of_concern": "expression of concern"}


def norm(text: str) -> str:
    """Lower-case ASCII words of `text`, without accents or punctuation."""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    return " ".join(re.sub(r"[^a-z0-9 ]", " ", text.lower()).split())


def similar(a: str, b: str) -> bool:
    """True when two name parts are the same up to a typo."""
    return difflib.SequenceMatcher(None, a, b).ratio() >= AUTHOR_MIN


def given_names_match(rest: list[str], given: list[str]) -> bool:
    """True when the supervisor's remaining name parts fit the author's given names.

    A registry given name that is only an initial ("K.") must match the initial
    of a part; otherwise a part, or all parts joined, must be similar to a given
    name ("Hongbo" and "Hong-bo" match, "Hui" and "Hongbo" do not). An author
    without a given name (organisations, single names) matches.
    """
    if not given:
        return True
    joined_rest, joined_given = "".join(rest), "".join(given)
    return (any(similar(r, g) for r in rest for g in given)
            or similar(joined_rest, joined_given)
            or all(len(g) == 1 for g in given) and any(r[0] == g for r in rest for g in given))


def is_author(name: str, authors: list[dict[str, str]]) -> bool:
    """True when one author's family name and given names match the supervisor.

    Name order is not assumed ("Zhang Hongbo" and "Hongbo Zhang" both work):
    one part of the supervisor's name must match the author's family name and
    the others must fit the author's given names (see `given_names_match`).
    """
    parts = [p for p in norm(name).split() if len(p) >= 2]
    for author in authors:
        family, given = norm(author["family"]).split(), norm(author["given"]).split()
        for i, part in enumerate(parts):
            if any(similar(part, f) for f in family) and given_names_match(parts[:i] + parts[i + 1:], given):
                return True
    return False


def authors_of(record: dict[str, Any]) -> list[dict[str, str]]:
    """Family and given names of the record's authors (organisations use their name as family name)."""
    return [{"family": a.get("family") or a.get("name") or "", "given": a.get("given") or ""}
            for a in record.get("author", [])]


def notices_of(doi: str, record: dict[str, Any]) -> set[str]:
    """Kinds of correction notices (retraction, withdrawal, ...) that apply to the article."""
    kinds = {u.get("type") for u in record.get("updated-by", [])}  # includes Retraction Watch
    url = f"https://api.crossref.org/works?filter=updates:{urllib.parse.quote(doi, safe='/')}&rows=5"
    for notice in get_json(url)["message"]["items"]:
        kinds |= {u.get("type") for u in notice.get("update-to", [])}
    if " ".join(record.get("title") or []).upper().startswith("RETRACTED"):
        kinds.add("retraction")
    return kinds


def publications() -> Iterator[tuple[str, str, str]]:
    """(supervisor name, file name, DOI) for every listed publication."""
    for path in sorted(YAML_DIR.glob("*.y*ml")):
        for entry in load_entries(path):
            for doi in entry.get("publications") or []:
                yield entry["name"], path.name, doi


def check(pub: tuple[str, str, str], cache: dict[str, Any], overrides: dict[str, Any]) -> tuple[tuple[str, str, str], list[str]]:
    """The problems found for one publication (an empty list means it is fine)."""
    name, _, doi = pub
    try:
        record = fetch_record(doi)
        notices = notices_of(doi, record)
        expected = entry_for(doi, record, overrides)
    except (LookupError, ValueError) as error:  # a RuntimeError (registry down) stops the whole run
        return pub, [str(error)[:200]]
    problems = [f"**{label}**" for kind, label in BAD_NOTICES.items() if kind in notices]
    if not is_author(name, authors_of(record)):
        names = ", ".join(f"{a['given']} {a['family']}".strip() for a in authors_of(record)[:8])
        problems.append(f"supervisor not among the authors: {names}")
    saved = cache.get(doi.lower())
    if saved is None:
        problems.append("citation not saved yet: run `python scripts/update_citations.py`")
    elif saved != expected:
        changed = ", ".join(f"{k}: “{plain(str(saved[k]))}” → “{plain(str(expected[k]))}”"
                            for k in expected if saved.get(k) != expected[k])
        problems.append(f"registry data changed ({changed[:200]}); run `python scripts/update_citations.py --refresh`")
    return pub, problems


def main() -> None:
    """Check all publications (two at a time, to be gentle on Crossref) and print a report."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", help="write a Markdown report here")
    args = parser.parse_args()
    cache, overrides = load_cache(), load_overrides()
    pubs = list(publications())
    with cf.ThreadPoolExecutor(2) as pool:
        results = list(pool.map(lambda pub: check(pub, cache, overrides), pubs))
    bad = [(pub, problems) for pub, problems in results if problems]
    used = {doi.lower() for _, _, doi in pubs}
    stale = sorted(set(cache) - used)
    lines = [f"Checked {len(pubs)} publications of {len({p[0] for p in pubs})} supervisors: "
             f"{len(pubs) - len(bad)} OK, {len(bad)} need attention.", ""]
    for (name, file, doi), problems in bad:
        entry = cache.get(doi.lower())
        lines.append(f"- **{name}** (`data/supervisors/{file}`), DOI `{doi}`: {'; '.join(problems)}")
        if entry:
            lines.append(f"  - saved citation: {plain(entry['title'])[:140]}")
    if stale:
        lines += ["", f"Saved citations that no profile uses any more ({', '.join(stale[:10])}): "
                      "run `python scripts/update_citations.py`."]
    report = "\n".join(lines)
    print(report)
    if args.report:
        Path(args.report).write_text(report + "\n", encoding="utf-8")
    sys.exit(1 if bad or stale else 0)


if __name__ == "__main__":
    main()
