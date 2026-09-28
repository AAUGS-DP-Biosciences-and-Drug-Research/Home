"""Check every supervisor publication against its DOI registry record.

For each publication in data/supervisors/*.yaml:
  - the DOI resolves (Crossref, or doi.org content negotiation as fallback)
  - the registered title matches the title in our citation
  - the supervisor is among the authors
  - the article has not been retracted

Usage:  python scripts/check_dois.py [--report report.md]
Exit code 1 if anything needs attention (used by .github/workflows/check-dois.yml).
"""

import argparse
import concurrent.futures as cf
import difflib
import json
import re
import sys
import time
import unicodedata
import urllib.parse
import urllib.request
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parent))
from gen_supervisors import load_entries, split_doi  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
UA = {"User-Agent": "aaugs-dp-biosciences-site/1.0 (https://github.com/AAUGS-DP-Biosciences-and-Drug-Research/Home)"}
TITLE_MIN = 0.8   # similarity below this is reported as a title mismatch
AUTHOR_MIN = 0.85  # fuzzy match for surnames (publishers misspell names)


def norm(s):
    s = unicodedata.normalize("NFKD", str(s))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return " ".join(re.sub(r"[^a-z0-9 ]", " ", s.lower()).split())


def fetch(url, headers):
    req = urllib.request.Request(url, headers={**UA, **headers})
    return json.load(urllib.request.urlopen(req, timeout=40))


def registry(doi):
    """Title, authors and retraction status of a DOI, with retries."""
    q = urllib.parse.quote(doi, safe="/")
    last = None
    for attempt in range(4):
        try:
            try:
                m = fetch(f"https://api.crossref.org/works/{q}", {})["message"]
                source = "crossref"
            except urllib.error.HTTPError as e:
                if e.code != 404:
                    raise
                m = fetch(f"https://doi.org/{q}", {"Accept": "application/vnd.citationstyles.csl+json"})
                source = "doi.org"
            title = m.get("title")
            title = " ".join(title) if isinstance(title, list) else (title or "")
            title = re.sub(r"<[^>]+>|&lt;[^&]*&gt;", "", title)
            authors = [{"family": a.get("family") or a.get("name") or "", "given": a.get("given") or ""}
                       for a in m.get("author", [])]
            notices = {u.get("type") for u in m.get("updated-by", [])}  # includes Retraction Watch
            if source == "crossref":
                notes = fetch(f"https://api.crossref.org/works?filter=updates:{q}&rows=5", {})["message"]["items"]
                notices |= {u.get("type") for n in notes for u in n.get("update-to", [])}
            retracted = title.upper().startswith("RETRACTED") or bool(notices & {"retraction", "withdrawal"})
            concern = "expression_of_concern" in notices
            return {"title": title, "authors": authors, "retracted": retracted, "concern": concern}
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, KeyError) as e:
            # network hiccup, rate limit or truncated response: retry
            last = e
            time.sleep(3 * (attempt + 1))
    return {"error": str(last)}


def title_score(registered, citation):
    t, c = norm(registered), norm(citation)
    if len(t.split()) >= 4 and t in c:  # short titles could match a journal name
        return 1.0
    return difflib.SequenceMatcher(None, t, c[: len(t) + 10]).ratio()


def similar(a, b):
    return difflib.SequenceMatcher(None, a, b).ratio() >= AUTHOR_MIN


def is_author(name, authors):
    """True when one author's family name and given-name initial match the supervisor.

    Name order is not assumed ("Zhang Hongbo" and "Hongbo Zhang" both work):
    one part of the supervisor's name must match the author's family name, and
    when the registry gives a first name, another part must share its initial.
    """
    parts = [p for p in norm(name).split() if len(p) >= 2]
    for a in authors:
        family, given = norm(a["family"]).split(), norm(a["given"]).split()
        for i, p in enumerate(parts):
            if any(similar(p, f) for f in family):
                rest = parts[:i] + parts[i + 1:]
                initials = {g[0] for g in given}
                if not initials or any(r[0] in initials for r in rest):
                    return True
    return False


def publications():
    for f in sorted((ROOT / "data" / "supervisors").glob("*.y*ml")):
        for e in load_entries(f):
            for p in e.get("publications") or []:
                p = " ".join(str(p).split())
                i = p.find("DOI: ")
                doi = split_doi(p[i + 5:])[0] if i >= 0 else None
                yield e["name"], f.name, (p[:i] if i >= 0 else p).strip(), doi


def check(pub):
    name, file, citation, doi = pub
    if not doi:
        return pub, ["no DOI"]
    r = registry(doi)
    if "error" in r:
        return pub, [f"DOI does not resolve ({r['error'][:60]})"]
    problems = []
    if r["retracted"]:
        problems.append("**retracted**")
    if r["concern"]:
        problems.append("expression of concern")
    score = title_score(r["title"], citation)
    if score < TITLE_MIN:
        problems.append(f"title mismatch ({score:.2f}): registered as “{r['title'][:120]}”")
    if not is_author(name, r["authors"]):
        problems.append("supervisor not among the authors: "
                        + ", ".join(f"{a['given']} {a['family']}".strip() for a in r["authors"][:8]))
    return pub, problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", help="write a Markdown report here")
    args = ap.parse_args()
    pubs = list(publications())
    with cf.ThreadPoolExecutor(2) as ex:  # gentle on the Crossref API
        results = list(ex.map(check, pubs))
    bad = [(p, probs) for p, probs in results if probs]
    lines = [f"Checked {len(pubs)} publications of {len({p[0] for p in pubs})} supervisors: "
             f"{len(pubs) - len(bad)} OK, {len(bad)} need attention.", ""]
    for (name, file, citation, doi), probs in bad:
        lines.append(f"- **{name}** (`data/supervisors/{file}`), DOI `{doi}`: {'; '.join(probs)}")
        lines.append(f"  - citation: {citation[:160]}")
    report = "\n".join(lines)
    print(report)
    if args.report:
        Path(args.report).write_text(report + "\n", encoding="utf-8")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
