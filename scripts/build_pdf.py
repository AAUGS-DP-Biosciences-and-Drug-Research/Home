"""Build the PDFs from the *built* site, so the PDF text is exactly the web text.

Run after `zensical build`. Writes into site/pdf/:
  <page>.pdf               one PDF per page
  supervisor-portfolio.pdf supervisor overview + every profile
  handbook.pdf             cover, contents and all sections in one document
and site/Document.pdf (the landing page, same address as the old Home PDF).
"""

import copy
import datetime
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote, urljoin, urlparse

import yaml
from bs4 import BeautifulSoup
from weasyprint import CSS, HTML
from weasyprint.text.fonts import FontConfiguration

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

FONT_DIR = (ROOT / "docs" / "assets" / "fonts").as_uri()
PRINT_CSS = "".join(
    f'@font-face {{ font-family: "Figtree"; font-weight: {w}; font-style: {s}; '
    f'src: url("{FONT_DIR}/figtree-latin-{w}-{s}.woff2"); }}\n'
    for w, s in [(400, "normal"), (400, "italic"), (600, "normal"), (700, "normal"), (800, "normal")]
) + """
@page {
  size: A4; font-family: "Figtree", "Noto Sans", "DejaVu Sans", sans-serif; margin: 16mm 16mm 16mm 16mm;
  @bottom-center { content: counter(page); font-family: "Figtree", "Noto Sans", sans-serif; font-size: 8pt; color: #666; }
  @top-right { content: string(section); font-family: "Figtree", "Noto Sans", sans-serif; font-size: 7.5pt; color: #888; }
}
@page cover { @bottom-center { content: none; } @top-right { content: none; } }
body { font-family: "Figtree", "Noto Sans", "DejaVu Sans", sans-serif; font-size: 10pt; line-height: 1.4; color: #20201f; margin: 0; }
/* Every size below is relative (em) to the section's font size, which
   fit() lowers step by step until the section fits on one page. */
h1 { font-size: 1.9em; line-height: 1.15; color: #b8161d; margin: 0 0 0.5em; string-set: section content(); }
h2 { font-size: 1.3em; color: #b8161d; margin: 1.1em 0 0.35em; border-bottom: 1px solid #dddddd; padding-bottom: 0.15em; }
h3 { font-size: 1.1em; margin: 0.9em 0 0.3em; }
h4 { font-size: 1em; margin: 0.8em 0 0.2em; }
h2, h3, h4 { break-after: avoid; }
p { margin: 0.35em 0; }
ul, ol { margin: 0.3em 0; padding-left: 1.3em; }
li { margin: 0.12em 0; }
li > ul, li > ol { margin: 0.1em 0; }
a { color: #b8161d; text-decoration: none; }
hr { border: 0; border-top: 1px solid #dddddd; margin: 0.8em 0; }
table { border-collapse: collapse; } td, th { border: 1px solid #ccc; padding: 3pt 6pt; }
.dp-updated { margin-top: 1.2em; font-size: 0.75em; color: #777; }
.headerlink, .md-content__button, .dp-filter, .dp-back, .dp-pdf-link { display: none !important; }
.section, .profile { break-before: page; }
.joined { break-before: auto; margin-top: 1.4em; padding-top: 1em; border-top: 2px solid #eeeeee; }
.profile { break-inside: avoid; }
.cols2 article { column-count: 2; column-gap: 7mm; }
.cols2 article > h1, .cols2 .dp-profile, .cols2 .dp-hero, .cols2 .dp-updated { column-span: all; }
.cols2 h2, .cols2 h3, .cols2 li { break-inside: avoid; }
.task-list-item { list-style: none; }
.task-list-item input { margin-right: 4pt; }
.task-list-control .task-list-indicator::before { content: "☐ "; }
.task-list-control input { display: none; }
/* landing page */
.dp-hero { background: #20201f; color: #fff; padding: 1em 1.2em 0.8em; margin-bottom: 0.8em; }
.dp-hero h1 { color: #fff; }
.dp-hero strong { color: #fff; }
.dp-chips ul { list-style: none; padding: 0; }
.dp-chips li { display: inline-block; background: #f1f1f1; border-left: 2pt solid #e4032e; padding: 0.15em 0.6em; margin: 0 0.3em 0.3em 0; font-weight: 700; }
.dp-cards { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 6pt; }
.dp-card { background: #f1f1f1; padding: 0 0.7em 0.4em; break-inside: avoid; }
.dp-card h3 { margin-top: 0.5em; }
.dp-card ul { list-style: none; padding-left: 0; }
/* supervisor overview */
.dp-subject h2 { break-after: avoid; }
.dp-people { display: flex; flex-wrap: wrap; gap: 5pt; }
.dp-person { width: 64pt; color: #20201f; font-size: 0.72em; line-height: 1.2; break-inside: avoid; }
.dp-person img, .dp-person .dp-person__initials { display: block; width: 64pt; height: 64pt; object-fit: cover; object-position: top; }
.dp-person__name { display: block; font-weight: 700; margin-top: 2pt; }
.dp-person__group { display: block; color: #666; }
.dp-person__initials { background: #b8161d; color: #fff; font-size: 18pt; font-weight: 700; text-align: center; line-height: 64pt; }
/* profiles */
.dp-profile { display: flex; gap: 10pt; align-items: flex-start; margin-bottom: 0.4em; }
.dp-profile__photo { width: 76pt; height: 95pt; object-fit: cover; object-position: top; flex: none; }
span.dp-profile__photo { display: block; background: #b8161d; color: #fff; font-size: 26pt; font-weight: 700; text-align: center; line-height: 95pt; }
.dp-profile__info h1 { font-size: 1.6em; }
.dp-profile__info p { margin: 0.05em 0; }
/* cover + contents */
.cover { page: cover; text-align: center; padding-top: 55mm; }
.cover img { width: 32mm; }
.cover h1 { font-size: 26pt; string-set: none; margin-top: 12mm; }
.cover p { color: #555; }
.toc { break-before: page; }
.toc h1 { string-set: none; }
.toc ol { list-style: none; padding: 0; font-size: 11pt; }
.toc li { margin: 4pt 0; }
.toc li.sub { margin-left: 14pt; font-size: 9pt; margin: 1.5pt 0 1.5pt 14pt; }
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


def content_date():
    """Latest real change of any page or supervisor data (see add_dates.py)."""
    sys.path.insert(0, str(ROOT / "scripts"))
    from add_dates import last_commit_date
    return last_commit_date(ROOT / "docs", ROOT / "data" / "supervisors", ROOT / "data" / "photos") or datetime.date.today()


FONTS = FontConfiguration()  # needed for the @font-face rules (Figtree)
STYLES = [CSS(string=PRINT_CSS, font_config=FONTS)]

# Layouts tried, in order, to fit a section on one page: text size in pt,
# then the same sizes in two columns. Below 8 pt it becomes hard to read, so a
# section that still does not fit keeps the normal size and spans pages.
LAYOUTS = [(s, 1) for s in (10, 9.5, 9, 8.5, 8)] + [(s, 2) for s in (10, 9.5, 9, 8.5, 8)]


def _doc(body_html):
    return f'<!doctype html><html lang="en"><head><meta charset="utf-8"><title>{TITLE}</title></head><body>{body_html}</body></html>'


def pages(body_html):
    return len(HTML(string=_doc(body_html), base_url=str(SITE)).render(stylesheets=STYLES, font_config=FONTS).pages)


def fit(inner, cls="section", attrs=""):
    """Wrap one section so that it fits on a single page if at all possible."""
    for size, cols in LAYOUTS:
        wrapped = f'<section class="{cls}{" cols2" if cols == 2 else ""}" style="font-size: {size}pt"{attrs}>{inner}</section>'
        if pages(wrapped) == 1:
            return wrapped
    return f'<section class="{cls}" style="font-size: 10pt"{attrs}>{inner}</section>'


def height(body_html):
    """Height and usable page height (CSS px) of a one-page section."""
    page = HTML(string=_doc(body_html), base_url=str(SITE)).render(stylesheets=STYLES, font_config=FONTS).pages[0]
    box = page._page_box
    usable = box.height  # content area of the page (without margins)

    def find(b):
        if getattr(b, "element_tag", None) == "section":
            return b
        for child in getattr(b, "children", []):
            found = find(child)
            if found:
                return found

    return find(box).margin_height(), usable


def pack(items):
    """Lay out (inner_html, cls, attrs) sections, one per page, but let a short
    section share its page with the next one: as they are if both fit, or
    fitted together at a smaller size, so no page is left mostly empty."""
    gap = 60  # separator between joined sections (margin, padding, rule), CSS px
    fitted = [fit(*it) for it in items]
    out, used, i = [], None, 0
    while i < len(fitted):
        html = fitted[i]
        h, usable = height(html) if pages(html) == 1 else (None, None)
        if used is not None and h is not None and used + gap + h <= usable * 0.97:
            out.append(html.replace('<section class="', '<section class="joined ', 1))
            used += gap + h
        elif h is not None and h < usable * 0.35 and i + 1 < len(fitted):
            # short section followed by one that does not fit next to it:
            # try both together on one page, at the largest size that fits
            (a, ca, aa), (b, cb, ab) = items[i], items[i + 1]
            for size, cols in LAYOUTS:
                c2 = " cols2" if cols == 2 else ""
                pair = (f'<section class="{ca}{c2}" style="font-size: {size}pt"{aa}>{a}</section>'
                        f'<section class="joined {cb}{c2}" style="font-size: {size}pt"{ab}>{b}</section>')
                if pages(pair) == 1:
                    out.append(pair)
                    i += 2
                    used = None
                    break
            else:
                out.append(html)
                used = h
                i += 1
            continue
        else:
            out.append(html)
            used = h
        i += 1
    return out


def render(body_html, out):
    HTML(string=_doc(body_html), base_url=str(SITE)).write_pdf(out, stylesheets=STYLES, font_config=FONTS)
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
    parts = []
    for slug, art in profiles:
        art = copy.copy(art)
        for el in art.select("[id]"):
            el["id"] = f"{prefix}-{slug}-{el['id']}"
        parts.append((str(art), "profile", f' id="{prefix}-{slug}"'))
    return fit(str(index)) + "".join(pack(parts))


def main():
    if not SITE.is_dir():
        sys.exit("site/ not found – run `zensical build` first")
    OUT.mkdir(exist_ok=True)

    render(fit(str(article(""))), SITE / "Document.pdf")

    for page, name, _ in PAGES:
        render(fit(str(article(page))), OUT / f"{name}.pdf")

    index, profiles = supervisor_articles()
    render(supervisor_html(index, profiles), OUT / "supervisor-portfolio.pdf")

    # Handbook: cover, contents, all sections, supervisor portfolio
    logo = (SITE / "assets" / "images" / "AboAkademiUniversity.png").as_uri()
    updated = content_date()
    cover = (
        f'<div class="cover"><img src="{logo}" alt=""><h1>{TITLE}</h1>'
        f"<p>Åbo Akademi University</p><p>{SITE_URL}</p>"
        f"<p>Last updated: {updated.day} {updated.strftime('%B %Y')}</p></div>"
    )
    toc, body = [], []
    for i, (page, name, title) in enumerate(PAGES, 1):
        art = article(page)
        prefix_ids(art, name)
        toc.append(f'<li><a href="#s-{name}">{title}</a></li>')
        body.append(fit(str(art), "section", f' id="s-{name}"'))
    toc.append('<li><a href="#s-supervisors">Supervisor Portfolio</a></li>')
    for slug, art in profiles:
        name = art.select_one("h1").get_text(strip=True)
        toc.append(f'<li class="sub"><a href="#sup-{slug}">{name}</a></li>')
    body.append(f'<div id="s-supervisors">{supervisor_html(index, profiles)}</div>')
    toc_html = f'<div class="toc"><h1>Contents</h1><ol>{"".join(toc)}</ol></div>'
    render(cover + toc_html + "".join(body), OUT / "handbook.pdf")


if __name__ == "__main__":
    main()
