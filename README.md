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

## PDFs

Built automatically from the website pages (so PDF and web text are always
the same):

- `/Home/pdf/handbook.pdf` – everything in one document, with contents
- `/Home/pdf/<page>.pdf` – one PDF per page, and `supervisor-portfolio.pdf`
- `/Home/Document.pdf` – the landing page (same address as before)

## Building locally

```bash
pip install -r requirements.txt
python scripts/gen_supervisors.py   # supervisor pages from YAML
zensical serve                      # live preview (address printed in the terminal)
zensical build && python scripts/build_pdf.py   # full build incl. PDFs into site/
```

WeasyPrint needs Pango (`apt install libpango-1.0-0 libpangoft2-1.0-0`).

## History

Until 2026 each page lived in its own repository (LearningGoals, Curriculum,
Yearly_followup, Graduation_Requirements, supervisor-portfolio, Master_PDF).
See [MIGRATION.md](MIGRATION.md) for how they were merged here and how text
accuracy was verified. Retired files are kept in [`deprecated/`](deprecated/).
