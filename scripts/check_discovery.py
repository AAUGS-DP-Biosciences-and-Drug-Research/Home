"""Validate crawler/discovery outputs after the site build."""

from __future__ import annotations

import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
NS = {
    "sm": "http://www.sitemaps.org/schemas/sitemap/0.9",
    "image": "http://www.google.com/schemas/sitemap-image/1.1",
}
SITE_URL = "https://aaugs-dp-biosciences-and-drug-research.github.io/Home/"


def fail(message: str) -> None:
    raise SystemExit(f"Discovery validation failed: {message}")


def main() -> None:
    required = [
        SITE / "llms.txt",
        SITE / "sitemap.xml",
        SITE / "licensing" / "index.html",
        SITE / "assets" / "image_rights.json",
        SITE / "c3e7a1f9b5d2c8e4a6f0b7d1e9c5a3f2.txt",
    ]
    missing = [str(path.relative_to(SITE)) for path in required if not path.is_file()]
    if missing:
        fail(f"missing public files: {', '.join(missing)}")

    rights = json.loads((SITE / "assets" / "image_rights.json").read_text(encoding="utf-8"))
    rows = rights.get("images")
    if not isinstance(rows, list) or not rows:
        fail("image_rights.json has no image records")
    for row in rows:
        provided_by = str(row.get("provided_by") or "").strip()
        notice = str(row.get("copyright_notice") or "").strip()
        if not provided_by or not notice:
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

    image_entries = tree.findall("sm:url/image:image/image:loc", NS)
    sitemap_images = {}
    for url_node in tree.findall("sm:url", NS):
        for img in url_node.findall("image:image/image:loc", NS):
            sitemap_images[img.text.strip()] = url_node.findtext("sm:loc", "", NS).strip()
    expected_images = {f"{SITE_URL}{row['path']}": row["profile_url"] for row in rows}
    if sitemap_images != expected_images:
        fail(f"sitemap images do not match image_rights.json: sitemap={sitemap_images}, expected={expected_images}")
    for row in rows:
        if not (SITE / row["path"]).is_file():
            fail(f"image listed in image_rights.json does not exist: {row['path']}")

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
        graph = payload.get("@graph")
        if not isinstance(graph, list):
            fail(f"expected JSON-LD @graph in {html_file.relative_to(SITE)}")
        types = {node.get("@type") for node in graph if isinstance(node, dict)}
        if not {"ProfilePage", "Person", "BreadcrumbList"} <= types:
            fail(
                f"expected ProfilePage, Person and BreadcrumbList JSON-LD in "
                f"{html_file.relative_to(SITE)}"
            )
        slug = html_file.parent.name
        has_photo = (SITE / "assets" / "images" / "supervisors" / f"{slug}.jpg").is_file()
        if has_photo and "og:image" not in html:
            fail(f"missing social image metadata in {html_file.relative_to(SITE)}")

    print(
        f"Discovery validation passed: {len(sitemap_urls)} pages, "
        f"{len(rows)} attributed supervisor images and {len(image_entries)} sitemap images."
    )


if __name__ == "__main__":
    main()
