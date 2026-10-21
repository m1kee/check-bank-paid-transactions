import re
import tomllib
import unittest
from pathlib import Path

from bankcheck import __version__

ROOT = Path(__file__).resolve().parent.parent
CHANGE_TYPES = ("Added", "Changed", "Deprecated", "Removed", "Fixed", "Security")


def changelog_section(changelog: str, version: str):
    """Return (heading line, body) of a version's section, or None if missing."""
    match = re.search(
        rf"^(## \[{re.escape(version)}\][^\n]*)\n(.*?)(?=^## \[|\Z)", changelog, re.M | re.S
    )
    return (match.group(1), match.group(2)) if match else None


def entries_by_type(body: str) -> dict:
    """Count the "- " entries under each "### <type>" subsection."""
    counts = {}
    current = None
    for line in body.splitlines():
        if line.startswith("### "):
            current = line[4:].strip()
            counts.setdefault(current, 0)
        elif current and line.startswith("- "):
            counts[current] += 1
    return counts


class VersionTests(unittest.TestCase):
    def setUp(self):
        self.changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")

    def test_installed_version_matches_pyproject(self):
        with open(ROOT / "pyproject.toml", "rb") as f:
            expected = tomllib.load(f)["project"]["version"]
        self.assertEqual(
            __version__, expected, "Run 'uv sync' after changing the version in pyproject.toml"
        )

    def test_changelog_has_a_dated_section_for_the_version(self):
        section = changelog_section(self.changelog, __version__)
        self.assertIsNotNone(section, f"CHANGELOG.md has no '## [{__version__}]' section")
        self.assertRegex(
            section[0],
            rf"^## \[{re.escape(__version__)}\] - \d{{4}}-\d{{2}}-\d{{2}}$",
            "The version heading must look like '## [X.Y.Z] - YYYY-MM-DD'",
        )

    def test_changelog_section_has_entries(self):
        section = changelog_section(self.changelog, __version__)
        self.assertIsNotNone(section, f"CHANGELOG.md has no '## [{__version__}]' section")
        counts = entries_by_type(section[1])

        unknown = set(counts) - set(CHANGE_TYPES)
        self.assertFalse(unknown, f"Unknown change types {sorted(unknown)}; use {CHANGE_TYPES}")
        self.assertGreater(
            sum(counts.values()), 0, f"The {__version__} section in CHANGELOG.md has no entries"
        )

    def test_changelog_has_a_link_for_the_version(self):
        has_link = re.search(rf"(?m)^\[{re.escape(__version__)}\]: https://", self.changelog)
        self.assertTrue(has_link, f"Add the '[{__version__}]: <compare url>' link at the end of CHANGELOG.md")


class ChangelogParsingTests(unittest.TestCase):
    """Make sure the checks above catch the cases they are meant to."""

    def test_empty_section_has_no_entries(self):
        changelog = "## [1.0.0] - 2026-01-01\n\n### Added\n\n## [0.9.0] - 2025-12-01\n### Fixed\n- x\n"
        _, body = changelog_section(changelog, "1.0.0")
        self.assertEqual(sum(entries_by_type(body).values()), 0)

    def test_entries_of_the_next_version_are_not_counted(self):
        changelog = "## [1.0.0] - 2026-01-01\n## [0.9.0] - 2025-12-01\n### Fixed\n- x\n"
        _, body = changelog_section(changelog, "1.0.0")
        self.assertEqual(entries_by_type(body), {})

    def test_last_section_is_read_until_the_end(self):
        changelog = "## [1.0.0] - 2026-01-01\n### Fixed\n- a\n- b\n\n[1.0.0]: https://x\n"
        _, body = changelog_section(changelog, "1.0.0")
        self.assertEqual(entries_by_type(body), {"Fixed": 2})

    def test_missing_section(self):
        self.assertIsNone(changelog_section("## [0.1.0] - 2025-01-01\n", "1.0.0"))


if __name__ == "__main__":
    unittest.main()
