"""Build the PDFs from the *built* site, so the PDF text is exactly the web text.

Run after `zensical build`. Writes into site/pdf/:
  <page>.pdf               one PDF per page
  supervisor-portfolio.pdf supervisor overview + every profile
  handbook.pdf             cover, contents and all sections in one document
and site/Document.pdf (the landing page, same address as the old Home PDF).
"""

import copy
import datetime
import sys
from pathlib import Path
from urllib.parse import unquote, urljoin, urlparse

import yaml
from bs4 import BeautifulSoup
from weasyprint import CSS, HTML

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
OUT = SITE / "pdf"
CONFIG = yaml.safe_load((ROOT / "mkdocs.yml").read_text(encoding="utf-8"))
SITE_URL = CONFIG["site_url"].rstrip("/") + "/"
TITLE = CONFIG["site_name"]

PAGES = [  # (built page, pdf name, section title in the handbook)
    ("learning-goals/", "learning-goals", "Learning Goals"),
    ("curriculum/", "curriculum", "Curriculum"),
    ("yearly-followup/", "yearly-followup", "PhD Follow-up Strategies"),
    ("graduation-requirements/", "graduation-requirements", "Graduation Requirements"),
]

PRINT_CSS = """
@page {
  size: A4; font-family: "Inter", "Noto Sans", "DejaVu Sans", sans-serif; margin: 20mm 18mm 20mm 18mm;
  @bottom-center { content: counter(page); font-family: "Noto Sans", "DejaVu Sans", sans-serif; font-size: 9pt; color: #666; }
  @top-right { content: string(section); font-family: "Noto Sans", "DejaVu Sans", sans-serif; font-size: 8pt; color: #888; }
}
@page cover { @bottom-center { content: none; } @top-right { content: none; } }
body { font-family: "Inter", "Noto Sans", "DejaVu Sans", sans-serif; font-size: 10.5pt; line-height: 1.45; color: #1d1d1f; }
h1 { font-size: 20pt; color: #1a3d7c; margin: 0 0 8pt; string-set: section content(); }
h2 { font-size: 14pt; color: #1a3d7c; margin: 16pt 0 5pt; border-bottom: 1px solid #d5dbe6; padding-bottom: 2pt; }
h3 { font-size: 12pt; margin: 12pt 0 4pt; }
h4 { font-size: 10.5pt; margin: 10pt 0 3pt; }
h2, h3, h4 { break-after: avoid; }
li { margin: 2pt 0; }
a { color: #1a3d7c; text-decoration: none; }
hr { border: 0; border-top: 1px solid #d5dbe6; margin: 12pt 0; }
table { border-collapse: collapse; } td, th { border: 1px solid #ccc; padding: 3pt 6pt; }
.headerlink, .md-content__button, .dp-filter, .dp-back, .dp-pdf-link { display: none !important; }
.section { break-before: page; }
.task-list-item { list-style: none; }
.task-list-item input { margin-right: 4pt; }
.task-list-control .task-list-indicator::before { content: "☐ "; }
.task-list-control input { display: none; }
/* landing page cards */
.dp-cards { display: grid; grid-template-columns: 1fr 1fr; gap: 8pt; }
.dp-card { border: 1px solid #d5dbe6; border-radius: 6pt; padding: 0 8pt 4pt; break-inside: avoid; }
.dp-card ul { list-style: none; padding-left: 0; }
.dp-card--soon { color: #888; }
/* supervisor overview */
.dp-subject h2 { break-after: avoid; }
.dp-people { display: flex; flex-wrap: wrap; gap: 6pt; }
.dp-person { width: 72pt; color: #1d1d1f; font-size: 7.5pt; line-height: 1.2; break-inside: avoid; }
.dp-person img, .dp-person .dp-person__initials { display: block; width: 72pt; height: 72pt; object-fit: cover; object-position: top; border-radius: 4pt; }
.dp-person__name { display: block; font-weight: 700; margin-top: 2pt; }
.dp-person__group { display: block; color: #666; }
.dp-person__initials { background: #1a3d7c; color: #fff; font-size: 20pt; font-weight: 700; text-align: center; line-height: 72pt; }
/* profiles */
.profile { break-before: page; }
.dp-profile { display: flex; gap: 12pt; align-items: flex-start; margin-bottom: 6pt; }
.dp-profile__photo { width: 90pt; height: 112pt; object-fit: cover; object-position: top; border-radius: 4pt; flex: none; }
span.dp-profile__photo { display: block; background: #1a3d7c; color: #fff; font-size: 28pt; font-weight: 700; text-align: center; line-height: 112pt; }
.dp-profile__info h1 { font-size: 16pt; }
.dp-profile__info p { margin: 1pt 0; }
/* cover + contents */
.cover { page: cover; text-align: center; padding-top: 55mm; }
.cover img { width: 32mm; }
.cover h1 { font-size: 26pt; string-set: none; margin-top: 12mm; }
.cover p { color: #555; }
.toc { break-before: page; }
.toc h1 { string-set: none; }
.toc ol { list-style: none; padding: 0; font-size: 12pt; }
.toc li { margin: 6pt 0; }
.toc li.sub { margin-left: 14pt; font-size: 10pt; }
.toc a::after { content: leader(".") target-counter(attr(href), page); }
"""


def article(page):
    """Return a deep copy of the <article> of a built page, links made absolute."""
    path = SITE / page / "index.html"
    soup = BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")
    art = copy.copy(soup.select_one("article.md-content__inner"))
    for el in art.select(".headerlink, .md-content__button"):
        el.decompose()
    page_url = urljoin(SITE_URL, page)
    for a in art.select("a[href]"):
        href = a["href"]
        if not href.startswith(("#", "mailto:")):
            a["href"] = urljoin(page_url, href)
    for img in art.select("img[src]"):
        src = img["src"]
        if not urlparse(src).scheme:
            local = (path.parent / unquote(src)).resolve()
            img["src"] = local.as_uri()
    return art


def render(body_html, out):
    doc = f'<!doctype html><html lang="en"><head><meta charset="utf-8"><title>{TITLE}</title></head><body>{body_html}</body></html>'
    HTML(string=doc, base_url=str(SITE)).write_pdf(out, stylesheets=[CSS(string=PRINT_CSS)])
    print(f"✅ {out.relative_to(ROOT)} ({out.stat().st_size // 1024} kB)")


def prefix_ids(art, prefix):
    """Make ids unique inside the handbook and point internal anchors at them."""
    for el in art.select("[id]"):
        el["id"] = f"{prefix}-{el['id']}"
    for a in art.select('a[href^="#"]'):
        a["href"] = f"#{prefix}-{a['href'][1:]}"


def supervisor_articles():
    index = article("supervisors/")
    profiles = []
    for a in index.select("a.dp-person"):
        slug = urlparse(a["href"]).path.rstrip("/").split("/")[-1]
        profiles.append((slug, article(f"supervisors/{slug}/")))
        a["href"] = f"#sup-{slug}"  # inside the PDF, the overview jumps to the profile
    return index, profiles


def supervisor_html(index, profiles, prefix="sup"):
    parts = [str(index)]
    for slug, art in profiles:
        art = copy.copy(art)
        for el in art.select("[id]"):
            el["id"] = f"{prefix}-{slug}-{el['id']}"
        parts.append(f'<section class="profile" id="{prefix}-{slug}">{art}</section>')
    return "".join(parts)


def main():
    if not SITE.is_dir():
        sys.exit("site/ not found – run `zensical build` first")
    OUT.mkdir(exist_ok=True)

    render(str(article("")), SITE / "Document.pdf")

    for page, name, _ in PAGES:
        render(str(article(page)), OUT / f"{name}.pdf")

    index, profiles = supervisor_articles()
    render(supervisor_html(index, profiles), OUT / "supervisor-portfolio.pdf")

    # Handbook: cover, contents, all sections, supervisor portfolio
    logo = (SITE / "assets" / "images" / "AboAkademiUniversity.png").as_uri()
    today = datetime.date.today().strftime("%d %B %Y")
    cover = (
        f'<div class="cover"><img src="{logo}" alt=""><h1>{TITLE}</h1>'
        f"<p>Åbo Akademi University</p><p>{SITE_URL}</p><p>{today}</p></div>"
    )
    toc, body = [], []
    for i, (page, name, title) in enumerate(PAGES, 1):
        art = article(page)
        prefix_ids(art, name)
        toc.append(f'<li><a href="#s-{name}">{title}</a></li>')
        body.append(f'<section class="section" id="s-{name}">{art}</section>')
    toc.append('<li><a href="#s-supervisors">Supervisor Portfolio</a></li>')
    for slug, art in profiles:
        name = art.select_one("h1").get_text(strip=True)
        toc.append(f'<li class="sub"><a href="#sup-{slug}">{name}</a></li>')
    body.append(f'<section class="section" id="s-supervisors">{supervisor_html(index, profiles)}</section>')
    toc_html = f'<div class="toc"><h1>Contents</h1><ol>{"".join(toc)}</ol></div>'
    render(cover + toc_html + "".join(body), OUT / "handbook.pdf")


if __name__ == "__main__":
    main()
