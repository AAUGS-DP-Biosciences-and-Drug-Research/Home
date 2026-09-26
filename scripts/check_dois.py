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

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gen_supervisors import split_doi  # noqa: E402

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
            authors = [" ".join(filter(None, [a.get("family"), a.get("given"), a.get("name")])) for a in m.get("author", [])]
            retracted = title.upper().startswith("RETRACTED")
            if source == "crossref" and not retracted:
                notes = fetch(f"https://api.crossref.org/works?filter=updates:{q}&rows=5", {})["message"]["items"]
                retracted = any(u.get("type") == "retraction" for n in notes for u in n.get("update-to", []))
            return {"title": title, "authors": authors, "retracted": retracted}
        except Exception as e:  # network hiccup or rate limit: retry
            last = e
            time.sleep(3 * (attempt + 1))
    return {"error": str(last)}


def title_score(registered, citation):
    t, c = norm(registered), norm(citation)
    if t and t in c:
        return 1.0
    return difflib.SequenceMatcher(None, t, c[: len(t) + 10]).ratio()


def is_author(name, authors):
    parts = [p for p in norm(name).split() if len(p) >= 3]
    for a in map(norm, authors):
        for w in a.split():
            if any(difflib.SequenceMatcher(None, p, w).ratio() >= AUTHOR_MIN for p in parts):
                return True
    return False


def publications():
    for f in sorted((ROOT / "data" / "supervisors").glob("*.y*ml")):
        for e in yaml.safe_load(f.read_text(encoding="utf-8")) or []:
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
    score = title_score(r["title"], citation)
    if score < TITLE_MIN:
        problems.append(f"title mismatch ({score:.2f}): registered as “{r['title'][:120]}”")
    if not is_author(name, r["authors"]):
        problems.append("supervisor not among the authors: " + ", ".join(r["authors"][:8]))
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
