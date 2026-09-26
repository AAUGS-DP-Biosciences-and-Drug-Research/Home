"""Check that no text was lost or changed in the migration.

Compares, word by word, the text of the pages that were published by the old
per-repo sites (pinned to their last gh-pages commit, so this stays
reproducible after those sites become redirects) with the newly built site,
and checks that every PDF contains all of its page's words.

Usage:  python scripts/verify_content.py      (after zensical build + build_pdf.py)
Exit code 1 if any difference is found.
"""

import difflib
import re
import sys
import unicodedata
import urllib.request
from pathlib import Path

import pypdfium2 as pdfium
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
RAW = "https://raw.githubusercontent.com/AAUGS-DP-Biosciences-and-Drug-Research/{repo}/{sha}/{path}"

# Last gh-pages commit of each old site before the migration.
OLD = {
    "Home": "4bcb81979e072e225568bba4f47a06d0b2449e70",
    "LearningGoals": "a53110092ba4a5bba09e7044bb007fae8e176077",
    "Curriculum": "16d39cccc7ef0999ad0ee26203eba85a9f78e933",
    "Yearly_followup": "3b2675e07a3b498472ffbe9cf00a2bb648b007d6",
    "Graduation_Requirements": "875fc3a8ed1d1f636d9da9cb9773704231dbfe29",
    "supervisor-portfolio": "44bfbe03e7d0c7dc251857aa7041617438828373",
}

PAGES = [  # (old repo, old path, new page, pdf)
    ("Home", "index.html", "", "Document.pdf"),
    ("LearningGoals", "index.html", "learning-goals/", "pdf/learning-goals.pdf"),
    ("Curriculum", "index.html", "curriculum/", "pdf/curriculum.pdf"),
    ("Yearly_followup", "index.html", "yearly-followup/", "pdf/yearly-followup.pdf"),
    ("Graduation_Requirements", "index.html", "graduation-requirements/", "pdf/graduation-requirements.pdf"),
    ("supervisor-portfolio", "index.html", "supervisors/", None),
]

# Elements that are new on the new site (not content that could be lost).
NEW_ONLY = ".dp-updated, .dp-suggest, .dp-filter, .dp-person__group, .dp-person__initials, .headerlink, .md-content__button"
# Web-only elements that the PDFs hide on purpose (buttons, back links).
WEB_ONLY = ".dp-back, .dp-pdf-link"

# Known, intended differences between the old and new *web* text:
#  - the old page template ended every page with a "← Back to Home" link;
#    the new site has navigation tabs instead.
#  - where the old Markdown lists were not recognised, the old site showed the
#    list dashes as literal "-" characters; they are now real bullets.
OLD_TEMPLATE_TAIL = ["←", "Back", "to", "Home"]


def fetch(repo, path):
    url = RAW.format(repo=repo, sha=OLD[repo], path=path)
    with urllib.request.urlopen(url, timeout=60) as r:
        return r.read().decode("utf-8")


def words(text):
    text = unicodedata.normalize("NFC", text)
    text = text.replace("[ ]", " ")  # checklist boxes are now real checkboxes
    text = text.replace("\u00ad", "").replace("\u200b", "")  # soft hyphens, zero-width spaces
    return re.findall(r"\S+", text)


def old_words(html, template_tail=False, literal_dashes=False):
    soup = BeautifulSoup(html, "html.parser")
    for el in soup(["script", "style", "title", "head"]):
        el.decompose()
    w = words(soup.get_text(" "))
    if literal_dashes:
        w = [x for x in w if x != "-"]
    if template_tail and w[-len(OLD_TEMPLATE_TAIL):] == OLD_TEMPLATE_TAIL:
        w = w[: -len(OLD_TEMPLATE_TAIL)]
    return w


def new_words(page, pdf=False):
    soup = BeautifulSoup((SITE / page / "index.html").read_text(encoding="utf-8"), "html.parser")
    art = soup.select_one("article.md-content__inner")
    for el in art.select(NEW_ONLY + (", " + WEB_ONLY if pdf else "")):
        el.decompose()
    return words(art.get_text(" "))


def is_emoji(w):
    # Colour emoji are drawn as images in the PDF, so text extraction cannot see
    # them (they are visible when the PDF is viewed).
    return all(unicodedata.category(c) in ("So", "Sk", "Mn", "Cf") for c in w)


def pdf_words(path):
    pdf = pdfium.PdfDocument(str(path))
    text = " ".join(pdf[i].get_textpage().get_text_range() for i in range(len(pdf)))
    text = text.replace("\ufffe", "-")  # hyphen of a word split across lines
    return words(text.replace("\r", " "))


def compare(label, old, new):
    if old == new:
        print(f"  ✅ {label}: {len(old)} words identical")
        return True
    print(f"  ❌ {label}: text differs")
    sm = difflib.SequenceMatcher(a=old, b=new, autojunk=False)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag != "equal":
            print(f"     {tag}: old «{' '.join(old[i1:i2])}»  →  new «{' '.join(new[j1:j2])}»")
    return False


def pdf_contains(label, web, pdf):
    """Every web word must appear in the PDF (line breaks may split hyphenated words)."""
    joined = "".join(pdf)
    pdfset = set(pdf)
    missing = [w for w in web if not is_emoji(w) and w not in pdfset and w not in joined]
    if missing:
        print(f"  ❌ {label}: {len(missing)} words missing from PDF: {missing[:20]}")
        return False
    print(f"  ✅ {label}: all {len(web)} words present")
    return True


def supervisor_slugs():
    return sorted(p.stem for p in (ROOT / "docs" / "supervisors").glob("*.md") if p.stem != "index")


def main():
    ok = True
    print("Web pages (old published text vs new site):")
    for repo, old_path, new_page, _ in PAGES:
        ok &= compare(
            f"{repo}/{old_path} → /{new_page}",
            old_words(
                fetch(repo, old_path),
                template_tail=repo not in ("Home", "supervisor-portfolio"),
                literal_dashes=repo in ("Yearly_followup", "Graduation_Requirements"),
            ),
            new_words(new_page),
        )

    print("Supervisor profiles:")
    slugs = supervisor_slugs()
    for slug in slugs:
        old = old_words(fetch("supervisor-portfolio", f"supervisors/{slug}.html"))
        ok &= compare(f"supervisors/{slug}", old, new_words(f"supervisors/{slug}/"))

    print("PDFs (every word of the web page is in the PDF):")
    for repo, _, new_page, pdf in PAGES:
        if pdf:
            ok &= pdf_contains(pdf, new_words(new_page, pdf=True), pdf_words(SITE / pdf))
    portfolio = pdf_words(SITE / "pdf" / "supervisor-portfolio.pdf")
    handbook = pdf_words(SITE / "pdf" / "handbook.pdf")
    sup_words = new_words("supervisors/", pdf=True) + [
        w for s in slugs for w in new_words(f"supervisors/{s}/", pdf=True)
    ]
    ok &= pdf_contains("pdf/supervisor-portfolio.pdf", sup_words, portfolio)
    hb_words = [w for _, _, p, _ in PAGES[1:5] for w in new_words(p, pdf=True)] + sup_words
    ok &= pdf_contains("pdf/handbook.pdf", hb_words, handbook)

    print("\nRESULT:", "all content transferred ✅" if ok else "DIFFERENCES FOUND ❌")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
