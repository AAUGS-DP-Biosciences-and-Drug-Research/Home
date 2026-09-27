"""Generate the supervisor pages from data/supervisors/*.yaml.

Writes (all git-ignored, rebuilt on every build):
  docs/supervisors/index.md          card grid grouped by subject
  docs/supervisors/<slug>.md         one profile page per supervisor
  docs/assets/images/supervisors/    resized photos

Field labels and ordering follow the original supervisor-portfolio templates.
Slugs are kept unchanged so the old URLs can be redirected one-to-one.
"""

import html
import json
import re
import shutil
import urllib.parse
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
REPO = "https://github.com/AAUGS-DP-Biosciences-and-Drug-Research/Home"
SITE_URL = "https://aaugs-dp-biosciences-and-drug-research.github.io/Home/"

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
        entry = entry if isinstance(entry, list) else [entry]
        for s in entry:
            s["_file"] = f.name
        sups.extend(entry)
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


def issue_body(s):
    """Plain-text profile the supervisor edits in the new issue."""
    s = s or {}
    lines = [
        "<!-- Edit what should change, then click Create. Leave everything that is"
        " correct as it is. One item per line in the lists. To send a new photo,"
        " drag it into this box. -->",
        "",
    ]
    fields = [("Name", s.get("name")), ("Group name", s.get("group")), ("Subject", s.get("unit")),
              ("University", s.get("university", "Åbo Akademi University")),
              ("Lab website", s.get("lab_website")), ("AboCRIS profile", s.get("cris_profile"))]
    lines += [f"**{label}:** {value or ''}  " for label, value in fields]
    lists = SECTIONS + [("publications", "Selected Publications (up to 5, each ending with DOI: 10.xxxx/…)")]
    for key, title in lists:
        lines += ["", f"### {title}"]
        items = [" ".join(str(i).split()) for i in s.get(key) or []]
        lines += [f"- {i}" for i in items] or ["- "]
    lines += ["", "### Keywords", str(s.get("keywords") or ""), "", "### Anything else?", ""]
    return "\n".join(lines)


def suggest_url(s=None):
    """New-issue link, prefilled with the current profile (blank for a new one).

    Uses the plain `title`/`body` parameters: GitHub does not reliably prefill
    issue-form fields from the URL. The label is added by
    .github/workflows/label-profile-issues.yml (a link can only set labels for
    people with triage rights).
    """
    title = f"Profile update: {s['name']}" if s else "New supervisor profile: "
    q = {"title": title, "body": issue_body(s)}
    return f"{REPO}/issues/new?{urllib.parse.urlencode(q, quote_via=urllib.parse.quote)}"


def profile_page(s):
    photo = s["_photo"]
    pos = ' style="object-position: center;"' if s.get("photo_position") == "center" else ""
    if photo:
        copyright_notice = f"© {s['name']}"
        media = (f'<div class="dp-profile__media"><img class="dp-profile__photo" src="../assets/images/supervisors/{photo}" '
                 f'alt="{html.escape(str(s["name"]))}" decoding="async"{pos}><small class="dp-photo-credit">{html.escape(copyright_notice)}</small></div>')
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
    edit = f"{REPO}/edit/main/data/supervisors/{s['_file']}"
    description_parts = [str(s.get("group") or "").strip(), str(s.get("unit") or "").strip()]
    affiliation_summary = ", ".join(part for part in description_parts if part)
    description = (
        f"{s['name']} — {affiliation_summary}. Supervisor profile for the "
        "Doctoral Programme in Biosciences and Drug Research."
        if affiliation_summary
        else f"{s['name']} — supervisor profile for the Doctoral Programme in Biosciences and Drug Research."
    )
    page_url = f"{SITE_URL}supervisors/{s['slug']}/"
    person = {
        "@type": "Person",
        "@id": f"{page_url}#person",
        "name": str(s["name"]),
        "url": page_url,
        "description": description,
        "affiliation": {
            "@type": "CollegeOrUniversity",
            "name": str(s.get("university") or "Åbo Akademi University"),
        },
    }
    same_as = []
    if s["cris_profile"]:
        same_as.append(s["cris_profile"])
    if s["lab_website"]:
        same_as.append(s["lab_website"])
    same_as.extend(page["url"] for page in s["web_pages"])
    if same_as:
        person["sameAs"] = list(dict.fromkeys(same_as))
    knows_about = [
        str(value).strip()
        for value in [*(s.get("expertise") or []), *(s.get("techniques") or [])]
        if str(value).strip()
    ]
    if knows_about:
        person["knowsAbout"] = list(dict.fromkeys(knows_about))
    if photo:
        person["image"] = {
            "@type": "ImageObject",
            "contentUrl": f"{SITE_URL}assets/images/supervisors/{photo}",
            "copyrightNotice": f"© {s['name']}",
            "creditText": f"© {s['name']}",
        }
    profile_jsonld = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "ProfilePage",
                "@id": f"{page_url}#profile",
                "url": page_url,
                "name": str(s["name"]),
                "mainEntity": {"@id": f"{page_url}#person"},
                "breadcrumb": {"@id": f"{page_url}#breadcrumb"},
            },
            person,
            {
                "@type": "BreadcrumbList",
                "@id": f"{page_url}#breadcrumb",
                "itemListElement": [
                    {
                        "@type": "ListItem",
                        "position": 1,
                        "name": "Home",
                        "item": SITE_URL,
                    },
                    {
                        "@type": "ListItem",
                        "position": 2,
                        "name": "Supervisors",
                        "item": f"{SITE_URL}supervisors/",
                    },
                    {
                        "@type": "ListItem",
                        "position": 3,
                        "name": str(s["name"]),
                        "item": page_url,
                    },
                ],
            },
        ],
    }
    structured_data = (json.dumps(profile_jsonld, ensure_ascii=False).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026"))
    return (
        f'---\ntitle: "{title}"\ndescription: "{description.replace(chr(34), chr(39))}"\n'
        + (f'image: "{SITE_URL}assets/images/supervisors/{photo}"\nimage_alt: "{title}"\n' if photo else "")
        + f'edit_url: "{edit}"\n---\n\n'
        f'<script type="application/ld+json">{structured_data}</script>\n\n'
        f'<div class="dp-profile">\n'
        f"{media}\n"
        f'<div class="dp-profile__info">\n' + "\n".join(info) + "\n</div>\n</div>\n\n"
        + "\n\n".join(body)
        + f'\n\n<p class="dp-suggest"><a class="md-button" href="{html.escape(suggest_url(s))}" target="_blank" rel="noopener">'
        "✏️ Suggest changes to this profile</a></p>\n"
        '\n<p class="dp-back"><a href="index.md">← Back to Portfolio</a></p>\n'
    )


def index_page(sups):
    by_subject = {}
    for s in sups:
        by_subject.setdefault(s.get("unit"), []).append(s)
    subjects = sorted(by_subject, key=lambda u: str(u))

    options = "".join(f'<option value="{html.escape(str(u))}">{text(u)}</option>' for u in subjects)
    parts = [
        '---\ntitle: Supervisors\ndescription: Search the supervisor portfolio for the Doctoral Programme in Biosciences and Drug Research by name, group, subject, expertise, and technique.\nhide:\n  - toc\n---\n',
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
                media = f'<img src="../assets/images/supervisors/{photo}" alt="" loading="lazy" decoding="async"{pos}>'
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
    parts.append(
        f'<p class="dp-suggest">Supervisor in the programme without a profile? '
        f'<a href="{html.escape(suggest_url())}" target="_blank" rel="noopener">Send us your profile</a> '
        "(needs a free GitHub account).</p>\n"
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
    rights = {
        "schema_version": 1,
        "policy": {
            "rights_status": "copyrighted",
            "reuse": "permission_required",
            "notice": "Supervisor photographs are © the named supervisor and are not licensed for reuse.",
        },
        "images": [
            {
                "path": f"assets/images/supervisors/{s['_photo']}",
                "copyright_holder": str(s["name"]),
                "copyright_notice": f"© {s['name']}",
                "rights_status": "copyrighted",
                "reuse": "permission_required",
                "profile_url": f"{SITE_URL}supervisors/{s['slug']}/",
            }
            for s in sups if s.get("_photo")
        ],
    }
    rights_path = ROOT / "docs" / "assets" / "image_rights.json"
    rights_path.parent.mkdir(parents=True, exist_ok=True)
    rights_path.write_text(json.dumps(rights, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"✅ Generated {len(sups)} supervisor pages")


if __name__ == "__main__":
    main()
