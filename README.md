# Doctoral Programme in Biosciences and Drug Research – website

Source of the (unofficial) programme website:

**https://aaugs-dp-biosciences-and-drug-research.github.io/Home/**

The site is built with [Zensical](https://zensical.org) from the Markdown
files in `docs/`. Every push to `main` rebuilds the website and all PDFs and
publishes them automatically (GitHub Actions → `gh-pages` branch).

## Editing a page

| Page | File |
|---|---|
| Home (landing page) | `docs/index.md` |
| Learning Goals | `docs/learning-goals.md` |
| Curriculum | `docs/curriculum.md` |
| Yearly Follow-up | `docs/yearly-followup.md` |
| Graduation Requirements | `docs/graduation-requirements.md` |

Open the file on GitHub, click the pencil icon, edit, and commit. Each page on
the website also has an "Edit this page" button that opens the right file.
Lists need a blank line before them, and nested items are indented by
**4 spaces**.

Downloadable files (DOCX, …) go in `docs/files/`.

## Supervisors

- One YAML file per supervisor in `data/supervisors/` (template: copy an
  existing file). The `slug` is also the page address, so do not change it
  for existing supervisors.
- Photo: `data/photos/<slug>.jpg` (or `.png`). Photos are resized
  automatically. Without a photo, the initials are shown.
- Optional `photo_position: center` crops the thumbnail from the centre
  instead of the top.
- Supervisors can request changes themselves: each profile page has a
  **Suggest changes to this profile** button. It opens a new GitHub issue whose
  text is the current profile, so they only edit what should change. The
  supervisor overview page links to a blank version for new supervisors.
  These issues get the label `supervisor profile` automatically
  (`.github/workflows/label-profile-issues.yml`); apply the change to the YAML
  file and close the issue. The pencil icon on a profile opens its YAML file.
- To convert a Microsoft Forms Excel export into YAML, use the notebook
  `tools/Convert_Excel_Supervisor_Data_to_YAML.ipynb`:
  [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/AAUGS-DP-Biosciences-and-Drug-Research/Home/blob/main/tools/Convert_Excel_Supervisor_Data_to_YAML.ipynb)

## Look and feel

The style follows www.abo.fi (colours of the abo2025 theme, square colour tiles,
bold type). Everything is in `docs/assets/stylesheets/extra.css`. The
university's own fonts are licensed through Adobe Fonts, so the open-source
Figtree font is used instead; it is self-hosted in `docs/assets/fonts/`, so the
site makes no requests to Google or Adobe. To show a black-and-white campus
photo behind the title on the landing page, add `docs/assets/images/hero.jpg`
and uncomment the `background-image` line under "Landing page hero" in
`extra.css`.

## Credits and licences

| What | Source | Licence |
|---|---|---|
| Custom website code | This repository | MIT (`LICENSE`) |
| Site generator and theme | [Zensical](https://zensical.org) | MIT (bundled third-party scripts: see `assets/javascripts/LICENSE` in the built site) |
| QR codes | [segno](https://github.com/heuer/segno) | BSD |
| Font | [Figtree](https://github.com/erikdkennedy/figtree), via Fontsource, self-hosted in `docs/assets/fonts/` | SIL Open Font License 1.1 (`docs/assets/fonts/OFL.txt`) |
| Emoji in PDFs | Noto Color Emoji (system font on the build machine) | SIL Open Font License 1.1 |
| Åbo Akademi University logo | [abo.fi logo page](https://www.abo.fi/en/about-abo-akademi-university/for-media/the-abo-akademi-university-logo/) | © Åbo Akademi University. Used unmodified, on white, as required by the university's graphic guide ("Felanvändning": no busy/low-contrast backgrounds, no recolouring or distortion) |
| Colours | Åbo Akademi graphic guide (2019) and www.abo.fi | Colour values only; no code, images or icons are copied from www.abo.fi |
| Supervisor photos and texts | Submitted by the supervisors for the portfolio | © the supervisors; photographs are not licensed for reuse |

The university's own typefaces (Gibson, Soleil) are licensed through Adobe
Fonts and are **not** used. The only requests a visitor's browser makes outside
the site are to the GitHub API (repository name/version next to the "Edit these
pages on GitHub" link); no Google, Adobe or font CDN requests.

See `LICENSE-CONTENT.md` and the public **Licensing and image rights** page for the separation between code and visual-content rights.

## PDFs

Built automatically from the website pages (so PDF and web text are always
the same):

- `/Home/pdf/handbook.pdf` – everything in one document, with contents
- `/Home/pdf/<page>.pdf` – one PDF per page, and `supervisor-portfolio.pdf`
- `/Home/Document.pdf` – the landing page (same address as before)

Each section fits on one page where possible, all links are clickable, and every
page carries a QR code to its live web page, so printed copies lead to the
current version.

## Publication check

`scripts/check_dois.py` checks every supervisor publication against its DOI
registry: the DOI resolves, the title matches, the supervisor is an author and
the article is not retracted. The *Check publication DOIs* workflow runs it on
the 1st of every month and opens (or updates) an issue when something needs
attention. Run it by hand from the Actions tab, or locally with
`python scripts/check_dois.py`.

## Building locally

```bash
pip install -r requirements.txt
python scripts/gen_supervisors.py   # supervisor pages from YAML
zensical serve                      # live preview (address printed in the terminal)
zensical build && python scripts/add_dates.py && python scripts/build_pdf.py   # full build incl. dates and PDFs
```

WeasyPrint needs Pango (`apt install libpango-1.0-0 libpangoft2-1.0-0`).

## History

Until 2026 each page lived in its own repository (LearningGoals, Curriculum,
Yearly_followup, Graduation_Requirements, supervisor-portfolio, Master_PDF).
See [MIGRATION.md](MIGRATION.md) for how they were merged here and how text
accuracy was verified. Retired files are kept in [`deprecated/`](deprecated/).
