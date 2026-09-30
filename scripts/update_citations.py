"""Save the citation data (title, journal, year) of every DOI listed in the profiles.

Usage:
    python scripts/update_citations.py            add DOIs that are not saved yet, drop unused ones
    python scripts/update_citations.py --refresh  fetch every DOI again (after registry corrections)

Writes data/publications.json, which the site build reads. Run it, and commit
the result, whenever a profile's DOI list changes.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from citations import CACHE_FILE, entry_for, fetch_record, load_cache, load_overrides, save_cache  # noqa: E402
from gen_supervisors import YAML_DIR, load_entries  # noqa: E402


def profile_dois() -> list[str]:
    """Every DOI listed in the supervisor files, once each, in file order."""
    seen: dict[str, str] = {}
    for path in sorted(YAML_DIR.glob("*.y*ml")):
        for entry in load_entries(path):
            for doi in entry.get("publications") or []:
                seen.setdefault(doi.lower(), doi)
    return list(seen.values())


def main() -> None:
    """Fetch what is missing (or everything with --refresh) and rewrite the saved file.

    DOIs that have an entry in data/citation_overrides.yaml are always fetched
    again, so a new or changed override takes effect. Progress is saved even if
    a fetch fails, so the next run continues where this one stopped.
    """
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--refresh", action="store_true", help="fetch every DOI again")
    args = parser.parse_args()

    dois = profile_dois()
    wanted = {doi.lower() for doi in dois}
    overrides = load_overrides()
    unused = sorted(set(overrides) - wanted)
    if unused:
        sys.exit(f"data/citation_overrides.yaml lists DOIs that no profile uses: {', '.join(unused)}")

    # --refresh may be the way to repair a damaged file, so it does not validate the old one.
    existing = load_cache(validate=not args.refresh) if CACHE_FILE.is_file() else {}
    cache = {doi: entry for doi, entry in existing.items() if doi in wanted}
    todo = [doi for doi in dois if args.refresh or doi.lower() not in cache or doi.lower() in overrides]
    try:
        for number, doi in enumerate(todo, 1):
            cache[doi.lower()] = entry_for(doi, fetch_record(doi), overrides)
            print(f"[{number}/{len(todo)}] {doi}")
            time.sleep(0.2)  # be gentle with the registry
    finally:
        save_cache(cache)
    load_cache()  # the saved file must pass the same checks as the site build
    print(f"Saved {len(cache)} citations: {len(todo)} fetched, {len(set(existing) - wanted)} no longer used and dropped.")


if __name__ == "__main__":
    main()
