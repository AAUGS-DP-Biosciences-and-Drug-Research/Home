# Doctoral Programme in Biosciences and Drug Research website

This repository builds the unofficial programme website for the Doctoral Programme in Biosciences and Drug Research at Åbo Akademi University:

https://aaugs-dp-biosciences-and-drug-research.github.io/Home/

The site is built from Markdown and YAML with [Zensical](https://zensical.org). Pull requests build a preview; pushes to main rebuild the site and PDFs and publish them to GitHub Pages. The build job only has read access; a separate deploy job, which runs only for main, publishes to the gh-pages branch and then notifies IndexNow of new or changed pages.

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

The normal update route is a GitHub issue. Each profile has a **Suggest changes to this profile** button that opens an issue prefilled with the current information. Apply the requested changes to the YAML file, check any publication DOIs, and close the issue when the change is merged.

A profile can also be edited directly in GitHub. Copy an existing YAML file when adding a new supervisor rather than inventing a new structure.

Each YAML file is a list with one entry. `name`, `slug`, `unit` (subject) and `university` are required. `name`, `group`, `unit` and `university` must not contain `<`, `>`, `"` or line breaks, because they are used in page titles and metadata. The build stops with an error naming the file if a rule is broken.

Photos belong in data/photos/ and should use the profile slug as the file name. If no photo is present, the site shows initials.

## Publication checks

scripts/check_dois.py checks the selected publications in supervisor profiles. It verifies that each DOI resolves, the registered title matches the citation, the supervisor appears among the authors, and the article is not marked as retracted.

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
python scripts/gen_supervisors.py
zensical build --strict
python scripts/add_dates.py
python scripts/enrich_sitemap_images.py
python scripts/submit_indexnow.py --sitemap site/sitemap.xml --key-file docs/c3e7a1f9b5d2c8e4a6f0b7d1e9c5a3f2.txt --dry-run
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
