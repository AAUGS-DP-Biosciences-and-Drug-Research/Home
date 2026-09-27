# Doctoral Programme in Biosciences and Drug Research website

This repository builds the unofficial programme website for the Doctoral Programme in Biosciences and Drug Research at Åbo Akademi University:

https://aaugs-dp-biosciences-and-drug-research.github.io/Home/

The site is built from Markdown and YAML with [Zensical](https://zensical.org). Pull requests build a preview; pushes to main rebuild the site and PDFs and publish them to GitHub Pages.

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

Custom code in this repository is MIT licensed. Supervisor photographs and profile text are not covered by that licence. Photographs remain © the named supervisor and are not licensed for reuse.

See [LICENSE-CONTENT.md](LICENSE-CONTENT.md) and the website's **Licensing and image rights** page for details.
