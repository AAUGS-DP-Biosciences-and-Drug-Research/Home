# Migration plan: one repository, one site

Goal: merge the separate one-page-per-repo sites into this **Home** repository,
rebuilt with [Zensical](https://zensical.org) (the successor of Material for
MkDocs), with PDFs generated from the same Markdown, **keeping the landing
address**:

> https://aaugs-dp-biosciences-and-drug-research.github.io/Home/

## Principles

1. **Text is transferred verbatim.** Page text is copied from each repo's
   `README.md` unchanged. The only edits are link *targets* that pointed at the
   old sites (they now point inside this site). Typos in the originals are
   deliberately kept and listed at the end of this file, to be fixed in a
   separate, reviewable commit.
2. **Accuracy is checked by a script, not by eye.** `scripts/verify_content.py`
   compares the text of the currently published pages (from each repo's
   `gh-pages` branch) with the newly built pages, word by word, and fails on any
   difference.
3. **Nothing goes live until `main` is merged.** Deployment keeps the existing
   mechanism (build → `gh-pages` branch of Home), so no GitHub Pages settings
   change and a failed build leaves the old site online.
4. **Old addresses keep working.** Old repos get redirect pages; nothing is
   deleted.

## Repository layout

```
mkdocs.yml                 site configuration (read by Zensical)
docs/                      pages (Markdown), copied verbatim from the old READMEs
  index.md                 landing page  (was Home)
  learning-goals.md        (was LearningGoals)
  curriculum.md            (was Curriculum)
  yearly-followup.md       (was Yearly_followup)
  graduation-requirements.md (was Graduation_Requirements)
  files/                   downloadable DOCX/XLSX
  assets/                  logo, stylesheet, supervisor photos
data/supervisors/*.yaml    supervisor profiles (moved unchanged from supervisor-portfolio)
scripts/
  gen_supervisors.py       YAML → docs/supervisors/*.md (runs before the build)
  build_pdf.py             built HTML → per-page PDFs + full handbook PDF
  verify_content.py        old published text vs new text
.github/workflows/publish.yml
```

## New addresses

| Old | New |
|---|---|
| `/Home/` | `/Home/` (unchanged) |
| `/LearningGoals/` | `/Home/learning-goals/` |
| `/Curriculum/` | `/Home/curriculum/` |
| `/Yearly_followup/` | `/Home/yearly-followup/` |
| `/Graduation_Requirements/` | `/Home/graduation-requirements/` |
| `/supervisor-portfolio/` | `/Home/supervisors/` |
| `/supervisor-portfolio/supervisors/<slug>.html` | `/Home/supervisors/<slug>/` (same slugs) |
| `<Repo>/Document.pdf` | `/Home/pdf/<page>.pdf` |
| Master_PDF `master.pdf` | `/Home/pdf/handbook.pdf` |

Supervisor slugs are kept exactly as before (including the mangled ones such as
`k-the-dahlstr-m`) so that old links can be redirected one-to-one.

## Roadmap

### Phase 1 – Build the new site (branch `claude/zen-pascal-s1k6xf`, Home)
- [x] Plan (this file)
- [x] Zensical scaffold, theme, navigation
- [x] Copy the five pages verbatim; rewrite old-site link targets
- [x] Move supervisor YAML + photos; generate supervisor index and profile pages
- [x] PDF build: one PDF per page + full handbook (cover, contents, all sections, supervisor portfolio)
- [x] Content verification script passes (web and PDF)
- [x] Screenshots of every page (desktop + mobile) reviewed
- [x] CI workflow (`publish.yml`): build on every push/PR, deploy only from `main`

### Phase 2 – Go live (manual: merge the Home PR)
- [x] Merge Home PR → site at `/Home/` is replaced in place
      (AAUGS-DP-Biosciences-and-Drug-Research/Home#1, merge commit `5ccbbb0`, 2026-09-26)
- [x] Check the live site: all pages, supervisor profiles, PDFs, DOCX and fonts
      return 200; Figtree loads in the browser and is embedded in the CI-built PDFs

### Phase 3 – Redirect the old sites (merge each old repo's PR, *after* Phase 2)
Merged on 2026-09-26: LearningGoals#1, Curriculum#1, Yearly_followup#1,
Graduation_Requirements#1, supervisor-portfolio#19, Master_PDF#1, .github#1.
Checked live: all 33 old page addresses redirect to the matching new page
(anchors kept), the 6 old PDF addresses serve the "moved" notice, raw file
download links still work, and the org profile has no old links left.
- [x] LearningGoals, Curriculum, Yearly_followup, Graduation_Requirements:
      old build workflow replaced by one that publishes a redirect page and a
      one-page "this document has moved" `Document.pdf`
- [x] supervisor-portfolio: redirects for the index, all 27 profile pages,
      `Supervisor_Portfolio.html` and `.pdf`; broken `center-faces` workflow removed;
      Excel→YAML notebook moved to `Home/tools/`
- [x] Master_PDF: rebuild workflow removed, README points to the handbook,
      `pdfs/master.pdf` replaced by a notice (original kept in `deprecated/`)
- [x] `.github` org profile: links updated

### Phase 4 – Clean-up (manual)
- [ ] Ask the programme office which external pages link to the old URLs and update them
- [ ] Archive (do not delete) the old repositories, starting with `template` as a test
- [x] Move open issue supervisor-portfolio#2 ("Fix the publication formatting") to Home

## Verification result

`scripts/verify_content.py` (run by hand via the *Verify migrated content*
workflow) compares the old published pages, pinned to their last `gh-pages`
commits, with the new build:

- 5 content pages, the supervisor index and all 27 supervisor profiles:
  **word-for-word identical**.
- Every PDF contains every word of its web page (emoji are drawn as images in
  PDFs and are checked visually instead).
- Intended differences, handled explicitly in the script: the old template's
  "← Back to Home" footer link (replaced by the navigation bar), and literal
  "-" characters that the old site showed where lists were not recognised
  (Yearly follow-up, Graduation Requirements; now real bullet lists; these
  whitespace-only fixes are in their own commits).

## Formatting-only changes (text unchanged)

- Yearly follow-up: list indentation fixed so nested bullets and the numbered
  meeting steps render properly; checklists render as checkboxes.
- Graduation Requirements: blank line before the list of article types.
- Home: title and welcome text shown as a hero panel, the major subjects as
  tags, and the "Documentation Categories" as colour tiles (abo.fi style).

## Deprecated files

`deprecated/` keeps the old consolidated `master.pdf` (from Master_PDF) and
`PhD_ECTS_Tracker_Categories_v4.xlsx` (from Curriculum). Not published.

## Text fixes after the migration (2026-09-26, separate PR)

Kept verbatim during the migration, then fixed on their own so the changes are
easy to review:

- Curriculum: "Compulsary courses" → "Compulsory"; "Useful ressources" → "resources"
- Yearly follow-up: "Useful ressources" → "resources"; missing ")" added in
  "Individual Study Plan (ISP) based on…", "Startup (first 3 months)" and
  "During each TFC meeting (≤ 90 min)"; double space in "PhD researcher"
- Learning Goals: removed the note "[Swedish version VERY much in the works still!]"
- Home: ÅAU Survival Guide link updated to the 2026–2027 edition on abo.fi (the
  2023–2024 link had stopped working); "Get Ready to Graduate" and "Fund your
  PhD studies" ("Coming soon") tiles hidden until those pages exist

`scripts/verify_content.py` checks the migration itself, so the *Verify
migrated content* workflow runs it on the migration commit (`5ccbbb0`). On
later commits it would report exactly these intended edits.
