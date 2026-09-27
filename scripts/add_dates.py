"""Add a "Last updated" line to every built page, from the git history.

Run after `zensical build` and before `build_pdf.py` (so the PDFs carry the
date too). The date is the last *real* change of the page's source:
  docs/<page>.md                    for the content pages
  data/supervisors/<file>.yaml      for a supervisor profile (and its photo)
  data/supervisors/ + data/photos/  for the supervisor overview
Commits up to the migration merge only moved or reformatted content, so they
are skipped; for files unchanged since then, the date of their last change in
the old repository is taken from data/dates_before_migration.yaml.
CI must check out the full history (fetch-depth: 0).
"""

import datetime
import subprocess
import sys
from pathlib import Path
from xml.sax.saxutils import escape

import yaml

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
MARK = '<p class="dp-updated">'
MIGRATION = "5ccbbb0456e2a767a57265e6c6128121aea30c99"  # merge of Home#1
BEFORE = yaml.safe_load((ROOT / "data" / "dates_before_migration.yaml").read_text(encoding="utf-8"))
SITE_URL = "https://aaugs-dp-biosciences-and-drug-research.github.io/Home/"


def last_commit_date(*paths):
    """Latest real change of any of the paths (files or directories)."""
    rel = [str(Path(p).relative_to(ROOT)) for p in paths]
    out = subprocess.run(
        ["git", "log", "-1", "--format=%cs", f"{MIGRATION}..HEAD", "--", *rel],
        cwd=ROOT, capture_output=True, text=True, check=True,
    ).stdout.strip()
    dates = [datetime.date.fromisoformat(out)] if out else []
    for r in rel:
        dates += [datetime.date.fromisoformat(str(v)) for k, v in BEFORE.items() if k == r or k.startswith(r.rstrip("/") + "/")]
    return max(dates) if dates else None


def fmt(d):
    return f"{d.day} {d.strftime('%B %Y')}"


def stamp(html_file, date):
    t = html_file.read_text(encoding="utf-8")
    if MARK in t or date is None:
        return False
    line = f'{MARK}Last updated: <time datetime="{date.isoformat()}">{fmt(date)}</time></p>'
    i = t.rfind("</article>")
    if i == -1:
        return False
    html_file.write_text(t[:i] + line + "\n" + t[i:], encoding="utf-8")
    return True


def pages():
    """(built html, source paths) for every page of the site."""
    for md in sorted((ROOT / "docs").glob("*.md")):
        out = SITE / ("index.html" if md.stem == "index" else f"{md.stem}/index.html")
        yield out, [md]
    sup = ROOT / "data" / "supervisors"
    photos = ROOT / "data" / "photos"
    yield SITE / "supervisors" / "index.html", [sup, photos]
    for f in sorted(sup.glob("*.y*ml")):
        for entry in yaml.safe_load(f.read_text(encoding="utf-8")) or []:
            slug = entry["slug"]
            yield SITE / "supervisors" / slug / "index.html", [f, *photos.glob(f"{slug}.*")]


def sitemap_url(html_file):
    """Canonical public URL for a built index.html file."""
    rel = html_file.relative_to(SITE)
    if rel.as_posix() == "index.html":
        return SITE_URL
    parent = rel.parent.as_posix().strip('/')
    return f"{SITE_URL}{parent}/"


def write_sitemap(entries):
    """Replace the generator sitemap with every real HTML page and accurate lastmod."""
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for html_file, date in sorted(entries, key=lambda item: sitemap_url(item[0])):
        lines.append('  <url>')
        lines.append(f"    <loc>{escape(sitemap_url(html_file))}</loc>")
        if date is not None:
            lines.append(f"    <lastmod>{date.isoformat()}</lastmod>")
        lines.append('  </url>')
    lines.append('</urlset>')
    (SITE / "sitemap.xml").write_text("\n".join(lines) + "\n", encoding="utf-8")

def main():
    if not SITE.is_dir():
        sys.exit("site/ not found – run `zensical build` first")
    n = 0
    sitemap_entries = []
    for html_file, sources in pages():
        if not html_file.is_file():
            continue
        date = last_commit_date(*sources)
        sitemap_entries.append((html_file, date))
        if stamp(html_file, date):
            n += 1
    write_sitemap(sitemap_entries)
    print(f"✅ Added 'Last updated' to {n} pages; sitemap contains {len(sitemap_entries)} pages")


if __name__ == "__main__":
    main()
