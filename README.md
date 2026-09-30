# Doctoral Programme in Biosciences and Drug Research website

This repository builds the unofficial programme website for the Doctoral Programme in Biosciences and Drug Research at Åbo Akademi University:

https://aaugs-dp-biosciences-and-drug-research.github.io/Home/

The site is built from Markdown and YAML with [Zensical](https://zensical.org). Pull requests build a preview; pushes to main rebuild the site and PDFs and publish them to GitHub Pages. The build job only has read access; a separate deploy job, which runs only for main, publishes to the gh-pages branch. Search engines find the pages through `sitemap.xml`.

## Where to edit

| Content | Source |
|---|---|
| Home page | docs/index.md |
| Learning goals | docs/learning-goals.md |
| Curriculum | docs/curriculum.md |
| Yearly follow-up | docs/yearly-followup.md |
| Graduation requirements | docs/graduation-requirements.md |
| Supervisor profiles | data/supervisors/*.yaml |
| Supervisor photos | data/photos/ |
| Downloadable files | docs/files/ |
| Site styling | docs/assets/stylesheets/extra.css |

The generated files under docs/supervisors/ and docs/assets/images/supervisors/ should not be edited by hand.

## Updating a supervisor profile

Each supervisor has one YAML file in data/supervisors/. Existing slugs are permanent because they are part of the public URL.

The normal update route is a GitHub issue. Each profile has a **Suggest changes to this profile** button that opens an issue prefilled with the current information. Apply the requested changes to the YAML file and close the issue when the change is merged. If the publications changed, follow [Publications](#publications) below.

A profile can also be edited directly in GitHub. Copy an existing YAML file when adding a new supervisor rather than inventing a new structure.

Each YAML file is a list with one entry. `name`, `slug`, `unit` (subject) and `university` are required. `name`, `group`, `unit` and `university` must not contain `<`, `>`, `"` or line breaks, because they are used in page titles and metadata. The build stops with an error naming the file if a rule is broken.

Photos belong in data/photos/ and should use the profile slug as the file name. If no photo is present, the site shows initials.

## Publications

A profile lists up to five publications as bare DOIs, for example `10.1016/j.ejps.2025.107132` (no `https://doi.org/`, no citation text):

~~~yaml
  publications:
  - 10.1016/j.ejps.2025.107132
  - 10.1002/smsc.202400084
~~~

The site shows every publication in the same form, `Title. Journal. Year. DOI: 10.x/y`, built from the DOI registry (Crossref). The journal is written out in full, the year is that of the journal issue, and titles keep italics, subscripts and superscripts. The registry data is saved in `data/publications.json` so that the site build never depends on the network. After changing a profile's DOIs, run

~~~bash
python scripts/update_citations.py            # add new DOIs, drop unused ones
python scripts/update_citations.py --refresh  # fetch everything again, after registry corrections
~~~

and commit `data/publications.json` with the profile. The build stops with an error if a listed DOI is not saved yet. If a registry record is wrong (a stray space, a typo, a series shown instead of the book), correct it in `data/citation_overrides.yaml` and run `python scripts/update_citations.py`; DOIs with an override are fetched again on every run. Keep that file short.

## Publication checks

scripts/check_dois.py checks the publications in supervisor profiles. It verifies that each DOI is registered, the supervisor appears among the authors, the article is not retracted, withdrawn or flagged with an expression of concern, and the citation saved in `data/publications.json` still matches the registry.

The scheduled **Check publication DOIs** workflow runs monthly and opens or updates an issue when something needs attention.

Run the same check locally with:

~~~bash
python scripts/check_dois.py
~~~

## Build locally

Install the Python dependencies:

~~~bash
pip install -r requirements.txt
~~~

Generate supervisor pages and start a live preview:

~~~bash
python scripts/gen_supervisors.py
zensical serve
~~~

For the full CI-equivalent build:

~~~bash
python scripts/test_citations.py
python scripts/gen_supervisors.py
zensical build --strict
python scripts/add_dates.py
python scripts/enrich_sitemap_images.py
python scripts/check_discovery.py
python scripts/build_pdf.py
~~~

WeasyPrint also needs Pango. On Debian/Ubuntu:

~~~bash
sudo apt install libpango-1.0-0 libpangoft2-1.0-0
~~~

## Repository rules

See [AGENTS.md](AGENTS.md) before changing code or generated content. The short version is: keep changes small, fail loudly instead of silently falling back, delete dead code, add type annotations and useful docstrings, and keep source files easy to read.

## Licensing

Custom code in this repository is MIT licensed. Supervisor photographs and profile text are not covered by that licence. Photographs are provided by the supervisors; copyright stays with the copyright holder (usually the photographer or the supervisor), and they are not licensed for reuse.

See [LICENSE-CONTENT.md](LICENSE-CONTENT.md) and the website's **Licensing and image rights** page for details.

### Third-party components

| What | Source | Licence |
|---|---|---|
| Site generator and theme | [Zensical](https://zensical.org) | MIT (bundled third-party scripts: see `assets/javascripts/LICENSE` in the built site) |
| PDF rendering | [WeasyPrint](https://weasyprint.org) | BSD |
| QR codes | [segno](https://github.com/heuer/segno) | BSD |
| Font | [Figtree](https://github.com/erikdkennedy/figtree), via Fontsource, self-hosted in `docs/assets/fonts/` | SIL Open Font License 1.1 (`docs/assets/fonts/OFL.txt`) |
| Emoji in PDFs | Noto Color Emoji (system font on the build machine) | SIL Open Font License 1.1 |
| Åbo Akademi University logo | [abo.fi logo page](https://www.abo.fi/en/about-abo-akademi-university/for-media/the-abo-akademi-university-logo/) | © Åbo Akademi University; used unmodified on white, as the university's graphic guide requires |
| Colours | Åbo Akademi graphic guide and www.abo.fi | Colour values only; no code, images or icons are copied from www.abo.fi |

The site makes no requests to Google, Adobe or font CDNs. The only outside request is to the GitHub API, for the repository name and version shown next to the "Edit these pages on GitHub" link.
