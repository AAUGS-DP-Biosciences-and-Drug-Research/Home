"""Validate crawler/discovery outputs after the site build."""

from __future__ import annotations

import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
SITE_URL = "https://aaugs-dp-biosciences-and-drug-research.github.io/Home/"


def fail(message: str) -> None:
    raise SystemExit(f"Discovery validation failed: {message}")


def main() -> None:
    required = [
        SITE / "llms.txt",
        SITE / "sitemap.xml",
        SITE / "licensing" / "index.html",
        SITE / "assets" / "image_rights.json",
    ]
    missing = [str(path.relative_to(SITE)) for path in required if not path.is_file()]
    if missing:
        fail(f"missing public files: {', '.join(missing)}")

    rights = json.loads((SITE / "assets" / "image_rights.json").read_text(encoding="utf-8"))
    rows = rights.get("images")
    if not isinstance(rows, list) or not rows:
        fail("image_rights.json has no image records")
    for row in rows:
        holder = str(row.get("copyright_holder") or "").strip()
        notice = str(row.get("copyright_notice") or "").strip()
        if not holder or notice != f"© {holder}":
            fail(f"invalid supervisor image attribution: {row!r}")
        if row.get("reuse") != "permission_required":
            fail(f"unexpected supervisor image reuse policy: {row!r}")

    tree = ET.parse(SITE / "sitemap.xml")
    sitemap_urls = {
        node.text.strip()
        for node in tree.findall("sm:url/sm:loc", NS)
        if node.text and node.text.strip()
    }
    expected_urls = set()
    for html_file in SITE.rglob("index.html"):
        rel = html_file.relative_to(SITE)
        parent = rel.parent.as_posix()
        expected_urls.add(SITE_URL if parent == "." else f"{SITE_URL}{parent}/")
    if sitemap_urls != expected_urls:
        missing_urls = sorted(expected_urls - sitemap_urls)
        extra_urls = sorted(sitemap_urls - expected_urls)
        fail(f"sitemap mismatch; missing={missing_urls}, extra={extra_urls}")

    profile_dir = SITE / "supervisors"
    for html_file in sorted(profile_dir.glob("*/index.html")):
        html = html_file.read_text(encoding="utf-8")
        match = re.search(
            r'<script type="application/ld\+json">(.*?)</script>',
            html,
            flags=re.DOTALL,
        )
        if not match:
            fail(f"missing JSON-LD in {html_file.relative_to(SITE)}")
        payload = json.loads(match.group(1))
        if payload.get("@type") != "ProfilePage":
            fail(f"expected ProfilePage JSON-LD in {html_file.relative_to(SITE)}")
        if not isinstance(payload.get("mainEntity"), dict) or payload["mainEntity"].get("@type") != "Person":
            fail(f"expected Person mainEntity in {html_file.relative_to(SITE)}")

    print(
        f"Discovery validation passed: {len(sitemap_urls)} pages, "
        f"{len(rows)} attributed supervisor images."
    )


if __name__ == "__main__":
    main()
