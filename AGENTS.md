# AGENTS.md

This repository is small on purpose. Keep it that way.

The site is a public programme resource maintained by people who may edit it directly on GitHub and by coding agents. Changes should therefore be easy to review, easy to undo, and unsurprising.

## Sources of truth

- Human-facing programme pages live in docs/*.md.
- Supervisor data live in data/supervisors/*.yaml.
- Original supervisor photos live in data/photos/.
- docs/supervisors/ and docs/assets/images/supervisors/ are generated. Do not edit them by hand.
- site/ is build output and must not be committed.

When a generated result is wrong, fix the source or generator rather than patching the generated file.

## Change discipline

- Make the smallest change that solves the problem.
- Do not mix unrelated cleanup into a functional change.
- Prefer deleting obsolete code to keeping compatibility layers that nobody uses.
- Do not keep one-off migration scripts, notebooks, reports, or audit artefacts after their job is finished. Git history is the archive.
- Do not add speculative abstractions, frameworks, helper layers, or configuration for hypothetical future needs.
- Preserve public URLs and supervisor slugs unless a redirect is deliberately added.

## No silent fallbacks

Silent fallback behaviour is forbidden.

If required input is missing, malformed, ambiguous, or unsupported, raise a clear error with enough context to fix it. Do not silently:

- substitute a default value for required data;
- accept legacy aliases without an explicit migration;
- ignore malformed records;
- skip files that should exist;
- catch broad exceptions and continue;
- replace a failed primary operation with a second method without making that behaviour explicit and testable.

Optional behaviour is different from fallback behaviour. A genuinely optional field may be absent, but the code should make that optionality explicit.

## Python

Write ordinary, boring Python.

- Use Python 3.12 syntax and type annotations for function parameters and return values.
- Give every public function a short docstring that explains its purpose, inputs, output, and important failure behaviour.
- Keep functions focused on one job. Split a function once it becomes difficult to understand without scrolling.
- Keep files cohesive. If a Python module grows beyond roughly 300–400 lines, consider splitting it by responsibility when you next make a substantive change there.
- Prefer pure functions for parsing, formatting, and validation.
- Keep filesystem, network, and subprocess work at clear boundaries.
- Use pathlib.Path for paths.
- Use specific exceptions. Avoid bare except and broad except Exception unless the exception is immediately re-raised with useful context.
- Validate external data before using it.
- Do not mutate input structures unless the function explicitly owns them.
- Avoid global mutable state.
- Keep dependencies minimal and pinned in requirements.txt. Remove a dependency when the code that needs it is removed.

Existing large scripts do not justify adding more large scripts. Refactor the touched area when doing so makes the change clearer and safer; do not perform unrelated rewrites.

## Data and supervisor profiles

- Keep one supervisor YAML file per supervisor.
- Treat slug as a permanent identifier.
- Keep selected publications to five unless the site design is deliberately changed.
- Publication entries should end with a bare DOI identifier in the form "DOI: 10.xxxx/...", not a DOI URL.
- Do not invent affiliations, grants, titles, publication details, or profile claims.
- For publication changes, verify DOI/title/author matching rather than trusting pasted citation text.
- Preserve copyright information for supervisor photographs.

## User-facing writing

Write for doctoral researchers and supervisors, not for a software audience.

- Use plain, direct language.
- Prefer short paragraphs and concrete headings.
- Avoid promotional filler and stock AI phrasing such as "unlock", "delve", "seamless", "transformative", "cutting-edge", "robust", "empower", "leverage", "foster", or "exciting" unless the word is genuinely necessary.
- Avoid inflated claims, repetitive summaries, fake enthusiasm, and generic conclusion paragraphs.
- Do not turn every section into a checklist or a stack of micro-headings.
- Keep official requirements distinct from programme recommendations.
- docs/learning-goals.md holds the programme's approved learning goals (English and Swedish). Do not reword them, even to remove the words listed above; change them only when the programme approves new wording.
- Do not paraphrase regulations in a way that changes their meaning. Link to the authoritative Åbo Akademi source when a rule comes from university regulations.

## HTML, CSS, and JavaScript

- Keep accessibility intact: semantic HTML, keyboard access, visible focus, useful alt text, and status text for dynamic controls.
- Avoid inline JavaScript when the behaviour belongs in docs/assets/javascripts/.
- Keep CSS selectors local and understandable. Reuse existing variables and components before adding new ones.
- Do not add third-party tracking, remote fonts, or unnecessary client-side dependencies.

## Tests and validation

Before opening or merging a PR that changes code or content, run the checks relevant to the change. For a full site change, the expected sequence is:

~~~bash
python scripts/gen_supervisors.py
zensical build --strict
python scripts/add_dates.py
python scripts/enrich_sitemap_images.py
python scripts/submit_indexnow.py --sitemap site/sitemap.xml --key-file docs/c3e7a1f9b5d2c8e4a6f0b7d1e9c5a3f2.txt --dry-run
python scripts/check_discovery.py
python scripts/build_pdf.py
~~~

Run python scripts/check_dois.py when supervisor publications change.

A failing check is a problem to fix, not something to suppress. Do not add continue-on-error, blanket exception handling, or conditional skips merely to make CI green. The one deliberate exception is an external notification step whose failure cannot affect the built site; such exceptions must be named and documented in the workflow.

## Pull requests

- Work on a branch and use a focused PR.
- Explain what changed and why.
- Call out deletions and behaviour changes explicitly.
- Keep generated output out of the diff unless it is intentionally versioned.
- Merge only after the build is green.
