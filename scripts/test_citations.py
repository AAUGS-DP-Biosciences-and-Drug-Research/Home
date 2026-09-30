"""Checks for scripts/citations.py. Run: python scripts/test_citations.py (no test framework needed)."""

from __future__ import annotations

import json
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import citations as c  # noqa: E402


def test_markup_is_limited_and_escaped() -> None:
    """Only italics, sub- and superscripts survive; everything else is escaped or dropped."""
    assert c.clean_markup("A &lt;i&gt;E. coli&lt;/i&gt; H&lt;sub&gt;2&lt;/sub&gt;S &amp; p &lt; 0.05") == \
        "A <i>E. coli</i> H<sub>2</sub>S &amp; p &lt; 0.05"
    assert c.clean_markup("<script>alert(1)</script>") == "alert(1)"
    assert c.clean_markup('<i onclick="x()">t</i>') == "<i>t</i>"
    assert c.clean_markup("<scp>ABC</scp> <mml:math><mml:mi>x</mml:mi></mml:math>") == "ABC x"


def test_tags_are_balanced() -> None:
    """A stray tag cannot leak formatting into the rest of the page."""
    assert c.clean_markup("<i>open") == "<i>open</i>"
    assert c.clean_markup("stray</sub> x") == "stray x"
    assert c.clean_markup("<i>a<sub>b</i>") == "<i>a<sub>b</sub></i>"


def test_typography() -> None:
    """Typographic hyphens become plain ones and no space stays in front of a subscript."""
    assert c.clean_markup("Mitochondria‐Targeted H <sub>2</sub>S") == "Mitochondria-Targeted H<sub>2</sub>S"


def test_dois() -> None:
    """Only bare DOIs are accepted."""
    assert c.check_doi("10.1016/j.ejps.2025.107132")
    for bad in ("https://doi.org/10.1000/x", "doi:10.1000/x", " 10.1000/x", "10.1/x", "", None):
        try:
            c.check_doi(bad)
        except ValueError:
            continue
        raise AssertionError(f"accepted {bad!r}")


def test_citation_format() -> None:
    """Every citation reads 'Title. Journal. Year. DOI: link', without doubled full stops."""
    cache = {"10.1000/a": {"title": "Plain title", "journal": "Nature", "year": 2024},
             "10.1000/b": {"title": "Is it? <i>Yes</i>", "journal": "Cell &amp; Co", "year": 2020},
             "10.1000/c": {"title": "Ends with a stop.", "journal": "Ecology", "year": 2019}}
    link = '<a href="https://doi.org/{0}" target="_blank" rel="noopener">{0}</a>'
    assert c.citation_html("10.1000/a", cache) == "Plain title. Nature. 2024. DOI: " + link.format("10.1000/a")
    assert c.citation_html("10.1000/A", cache).startswith("Plain title. Nature. 2024.")  # DOIs are case-insensitive
    assert c.citation_html("10.1000/c", cache).startswith("Ends with a stop. Ecology. 2019.")
    try:
        c.citation_html("10.1000/missing", cache)
    except KeyError:
        pass
    else:
        raise AssertionError("a missing DOI must be an error")


def test_record_needs_title_journal_year() -> None:
    """A registry record without a journal or year is an error, not an empty citation."""
    ok = {"title": ["T"], "container-title": ["J"], "published-print": {"date-parts": [[2021]]}, "issued": {"date-parts": [[2020]]}}
    assert c.entry_from_record("10.1000/x", ok) == {"title": "T", "journal": "J", "year": 2021}
    assert c.entry_from_record("10.1000/x", {**ok, "published-print": None})["year"] == 2020
    assert c.entry_from_record("10.1000/x", {k: v for k, v in ok.items() if k != "issued"})["year"] == 2021
    for dropped in (("title",), ("container-title",), ("issued", "published-print")):
        broken = {k: v for k, v in ok.items() if k not in dropped}
        try:
            c.entry_from_record("10.1000/x", broken)
        except ValueError:
            continue
        raise AssertionError(f"accepted a record without {dropped}")


def test_hostile_input_is_fast_and_inert() -> None:
    """Long or odd input neither stalls the build nor produces markup."""
    start = time.time()
    c.clean_markup("<" * 20000 + "i" * 20000)
    c.clean_markup("<i" + "a" * 20000)
    c.clean_markup("<i " + "a" * 200000)
    assert time.time() - start < 2
    assert c.clean_markup("a < b > c") == "a &lt; b &gt; c"  # not a tag: no text is lost
    assert c.clean_markup("x<i/>y") == "xy"
    assert "<script" not in c.clean_markup("&lt;script&gt;alert(1)&lt;/script&gt; &amp;lt;script&amp;gt;")


def test_year_falls_back_to_first_online_year() -> None:
    """A print date without a year does not hide a valid 'issued' date."""
    record = {"title": ["T"], "container-title": ["J"], "published-print": {"date-parts": [[None]]},
              "issued": {"date-parts": [[2020]]}}
    assert c.entry_from_record("10.1000/x", record)["year"] == 2020
    record["published-print"] = {"date-parts": [[]]}
    assert c.entry_from_record("10.1000/x", record)["year"] == 2020


def test_punctuation_is_not_doubled() -> None:
    """A title that already ends in punctuation gets no extra full stop."""
    for ending in (":", ",", ";", "?", "…"):
        cache = {"10.1000/a": {"title": f"Foo{ending}", "journal": "J", "year": 2020}}
        assert c.citation_html("10.1000/a", cache).startswith(f"Foo{ending} J. 2020.")


def test_damaged_cache_is_refused() -> None:
    """Saved text that clean_markup would not have produced is never used."""
    good = {"title": "A <i>b</i> &amp; c", "journal": "J", "year": 2020}
    bad_titles = ["<sub>", "</i>", "<i></sub></i>", "x<script>y", "<I>x</I>", "a &#60; b", "a < b", "<i onclick=x>t</i>"]
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "publications.json"
        path.write_text(json.dumps({"10.1000/a": good}), encoding="utf-8")
        assert c.load_cache(path)
        for title in bad_titles:
            path.write_text(json.dumps({"10.1000/a": {**good, "title": title}}), encoding="utf-8")
            try:
                c.load_cache(path)
            except ValueError:
                continue
            raise AssertionError(f"accepted the saved title {title!r}")
        path.write_text(json.dumps({"10.1000/a": {**good, "year": "2020"}}), encoding="utf-8")
        try:
            c.load_cache(path)
        except ValueError:
            pass
        else:
            raise AssertionError("accepted a year that is not a number")


def test_overrides_are_validated() -> None:
    """A bad override is refused when it is read, before it can reach the saved file."""
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "overrides.yaml"
        for text in ('10.1000/a:\n  year: "2020"\n', '10.1000/a:\n  title: ""\n', '10.1000/a:\n  volume: 3\n',
                     '10.1000/a:\n  year: true\n', "https://doi.org/10.1000/a:\n  year: 2020\n"):
            path.write_text(text, encoding="utf-8")
            try:
                c.load_overrides(path)
            except ValueError:
                continue
            raise AssertionError(f"accepted the override {text!r}")
        path.write_text("10.1000/A:\n  year: 2020\n  journal: J\n", encoding="utf-8")
        assert c.load_overrides(path) == {"10.1000/a": {"year": 2020, "journal": "J"}}


def test_dois_are_ascii() -> None:
    """Look-alike and invisible characters are not accepted in a DOI."""
    for bad in ("10.1000/a\u200bb", "10.1000/a\u202eb", "10.\uff11\uff10\uff10\uff10/x", "10.1000/a b", "10.1000/a\nb"):
        try:
            c.check_doi(bad)
        except ValueError:
            continue
        raise AssertionError(f"accepted {bad!r}")


def test_saved_citations_are_valid() -> None:
    """data/publications.json loads and every entry passes the safety checks."""
    assert c.load_cache()


if __name__ == "__main__":
    tests = [f for name, f in sorted(globals().items()) if name.startswith("test_")]
    for test in tests:
        test()
    print(f"{len(tests)} checks passed")
