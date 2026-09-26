"""Generate the supervisor pages from data/supervisors/*.yaml.

Writes (all git-ignored, rebuilt on every build):
  docs/supervisors/index.md          card grid grouped by subject
  docs/supervisors/<slug>.md         one profile page per supervisor
  docs/assets/images/supervisors/    resized photos

Field labels and ordering follow the original supervisor-portfolio templates.
Slugs are kept unchanged so the old URLs can be redirected one-to-one.
"""

import html
import re
import shutil
from pathlib import Path

import yaml
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parent.parent
YAML_DIR = ROOT / "data" / "supervisors"
PHOTO_DIR = ROOT / "data" / "photos"
OUT_DIR = ROOT / "docs" / "supervisors"
IMG_OUT = ROOT / "docs" / "assets" / "images" / "supervisors"
LOGO = "AboAkademiUniversity.png"
PHOTO_WIDTH = 600

SECTIONS = [
    ("expertise", "Areas of Expertise"),
    ("projects", "Research Projects"),
    ("techniques", "Special Methodologies & Techniques"),
    ("funding", "Major Funding & International Networks"),
]


def normalize_url(url):
    url = str(url or "").strip()
    if not url:
        return ""
    if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", url):
        return url
    return f"https://{url}"


def normalize_web_pages(sup):
    pages = sup.get("web_pages") or []
    if not isinstance(pages, list):
        pages = [pages]
    out = []
    for item in pages:
        if isinstance(item, dict):
            label = str(item.get("label") or item.get("name") or "Web Page").strip()
            url = normalize_url(item.get("url") or item.get("link"))
        else:
            label, url = "Web Page", normalize_url(item)
        if url:
            out.append({"label": label, "url": url})
    return out


def last_name_key(name):
    parts = str(name or "").split()
    return parts[-1].casefold() if parts else ""


def text(value):
    """Escape a YAML string and turn '[https://…]' into links (as before)."""
    escaped = html.escape(str(value), quote=False)
    return re.sub(
        r"\[(https?://[^\]\s]+)\]",
        lambda m: f'<a href="{m.group(1)}" target="_blank" rel="noopener">{m.group(1)}</a>',
        escaped,
    )


def tone(slug):
    """Stable palette colour (0-3) for the initials tile of a supervisor."""
    return sum(map(ord, slug)) % 4


def initials(name):
    parts = str(name).split()
    return html.escape((parts[0][0] + parts[-1][0]).upper() if parts else "")


def split_doi(value):
    """Clean DOI for the link, plus any trailing punctuation to keep as text.

    Accepts '10.x/y', 'doi.org/10.x/y' and 'https://doi.org/10.x/y'; a trailing
    '.' or ',' (end of the citation) is not part of the DOI.
    """
    value = value.strip()
    doi = re.sub(r"^(https?://)?(dx\.)?doi\.org/", "", value, flags=re.I)
    m = re.match(r"^(.*?)([.,;]*)$", doi)
    return m.group(1), m.group(2)


def publication(pub):
    pub = str(pub)
    i = pub.find("DOI: ")
    if i == -1:
        return text(pub)
    doi, tail = split_doi(pub[i + 5:])
    return (
        f'{text(pub[:i])} DOI: <a href="https://doi.org/{html.escape(doi)}" '
        f'target="_blank" rel="noopener">{html.escape(doi)}</a>{html.escape(tail)}'
    )


def load():
    sups = []
    for f in sorted(YAML_DIR.glob("*.y*ml")):
        entry = yaml.safe_load(f.read_text(encoding="utf-8"))
        sups.extend(entry if isinstance(entry, list) else [entry])
    for s in sups:
        s["lab_website"] = normalize_url(s.get("lab_website"))
        s["cris_profile"] = normalize_url(s.get("cris_profile"))
        s["web_pages"] = normalize_web_pages(s)
    sups.sort(key=lambda s: (last_name_key(s.get("name")), str(s.get("name", "")).casefold()))
    return sups


def find_photo(slug):
    for ext in (".jpg", ".jpeg", ".png", ".webp", ".JPG", ".JPEG", ".PNG"):
        p = PHOTO_DIR / f"{slug}{ext}"
        if p.is_file():
            return p
    return None


def make_photo(slug):
    """Resize the photo to a web/print friendly JPEG. Returns file name or None."""
    src = find_photo(slug)
    if src is None:
        return None
    im = ImageOps.exif_transpose(Image.open(src))
    if im.mode in ("RGBA", "LA", "P"):
        im = im.convert("RGBA")
        bg = Image.new("RGB", im.size, "white")
        bg.paste(im, mask=im.split()[-1])
        im = bg
    else:
        im = im.convert("RGB")
    if im.width > PHOTO_WIDTH:
        im = im.resize((PHOTO_WIDTH, round(im.height * PHOTO_WIDTH / im.width)), Image.LANCZOS)
    name = f"{slug}.jpg"
    im.save(IMG_OUT / name, "JPEG", quality=85, optimize=True)
    return name


def profile_page(s):
    photo = s["_photo"]
    pos = ' style="object-position: center;"' if s.get("photo_position") == "center" else ""
    if photo:
        media = f'<img class="dp-profile__photo" src="../assets/images/supervisors/{photo}" alt="Photo of {html.escape(str(s["name"]))}"{pos}>'
    else:
        media = f'<span class="dp-profile__photo dp-person__initials dp-tone-{tone(s["slug"])}" aria-hidden="true">{initials(s["name"])}</span>'
    info = [f"<h1>{text(s['name'])}</h1>"]
    if s.get("group"):
        info.append(f"<p><strong>Group Name:</strong> {text(s['group'])}</p>")
    if s.get("unit"):
        info.append(f"<p><strong>Subject:</strong> {text(s['unit'])}</p>")
    info.append(f"<p><strong>University:</strong> {text(s.get('university', ''))}</p>")
    if s["lab_website"]:
        info.append(f'<p><strong>Lab Website:</strong> <a href="{html.escape(s["lab_website"])}" target="_blank" rel="noopener">link</a></p>')
    if s["cris_profile"]:
        info.append(f'<p><strong>AboCRIS Profile:</strong> <a href="{html.escape(s["cris_profile"])}" target="_blank" rel="noopener">link</a></p>')
    if s["web_pages"]:
        links = " · ".join(
            f'<a href="{html.escape(p["url"])}" target="_blank" rel="noopener">{text(p["label"])}</a>'
            for p in s["web_pages"]
        )
        info.append(f"<p><strong>Web Pages:</strong> {links}</p>")

    body = []
    for key, title in SECTIONS:
        if s.get(key):
            items = "".join(f"<li>{text(i)}</li>" for i in s[key])
            body.append(f"<h2>{title}</h2>\n<ul>{items}</ul>")
    if s.get("publications"):
        items = "".join(f"<li>{publication(p)}</li>" for p in s["publications"])
        body.append(f"<h2>Selected Publications</h2>\n<ul>{items}</ul>")
    if s.get("keywords"):
        body.append(f"<h2>Keywords</h2>\n<p>{text(s['keywords'])}</p>")

    title = str(s["name"]).replace('"', '\\"')
    return (
        f'---\ntitle: "{title}"\n---\n\n'
        f'<div class="dp-profile">\n'
        f"{media}\n"
        f'<div class="dp-profile__info">\n' + "\n".join(info) + "\n</div>\n</div>\n\n"
        + "\n\n".join(body)
        + '\n\n<p class="dp-back"><a href="index.md">← Back to Portfolio</a></p>\n'
    )


def index_page(sups):
    by_subject = {}
    for s in sups:
        by_subject.setdefault(s.get("unit"), []).append(s)
    subjects = sorted(by_subject, key=lambda u: str(u))

    options = "".join(f'<option value="{html.escape(str(u))}">{text(u)}</option>' for u in subjects)
    parts = [
        '---\ntitle: Supervisors\nhide:\n  - toc\n---\n',
        "# Supervisor Portfolio for the Doctoral Programme in Biosciences and Drug Research\n",
        '<p class="dp-pdf-link"><a class="md-button md-button--primary" href="../pdf/supervisor-portfolio.pdf" target="_blank">📄 Download Full Portfolio PDF</a></p>\n',
        '<div class="dp-filter" data-dp-filter>'
        '<label class="dp-filter__group"><span>Search</span>'
        '<input type="search" data-dp-search placeholder="Name, group, expertise, technique…"></label>'
        '<label class="dp-filter__group"><span>Subject</span>'
        f'<select data-dp-subject><option value="">All subjects</option>{options}</select></label>'
        '<span class="dp-filter__count" data-dp-count></span>'
        "</div>\n",
    ]
    for u in subjects:
        cards = []
        for s in by_subject[u]:
            photo = s["_photo"]
            pos = ' style="object-position: center;"' if s.get("photo_position") == "center" else ""
            if photo:
                media = f'<img src="../assets/images/supervisors/{photo}" alt="{html.escape(str(s["name"]))}"{pos}>'
            else:
                media = f'<span class="dp-person__initials" aria-hidden="true">{initials(s["name"])}</span>'
            haystack = " ".join(
                str(x) for x in [s.get("name"), s.get("group"), s.get("unit"), s.get("keywords")]
                + list(s.get("expertise") or []) + list(s.get("techniques") or [])
            ).casefold()
            cards.append(
                f'<a class="dp-person dp-tone-{tone(s["slug"])}" href="{s["slug"]}.md" data-subject="{html.escape(str(u))}" '
                f'data-search="{html.escape(haystack)}">'
                f"{media}"
                f'<span class="dp-person__name">{text(s["name"])}</span>'
                f'<span class="dp-person__group">{text(s.get("group") or "")}</span>'
                "</a>"
            )
        parts.append(
            f'<section class="dp-subject" data-subject="{html.escape(str(u))}">\n'
            f"<h2>{text(u)}</h2>\n"
            f'<div class="dp-people">{"".join(cards)}</div>\n</section>\n'
        )
    parts.append('<p class="dp-back"><a href="../index.md">← Back to Home</a></p>\n')
    return "\n".join(parts)


def main():
    for d in (OUT_DIR, IMG_OUT):
        shutil.rmtree(d, ignore_errors=True)
        d.mkdir(parents=True)
    sups = load()
    for s in sups:
        s["_photo"] = make_photo(s["slug"])
        if not s["_photo"]:
            print(f"⚠️  No photo for {s['name']} → using logo")
        (OUT_DIR / f"{s['slug']}.md").write_text(profile_page(s), encoding="utf-8")
    (OUT_DIR / "index.md").write_text(index_page(sups), encoding="utf-8")
    print(f"✅ Generated {len(sups)} supervisor pages")


if __name__ == "__main__":
    main()
