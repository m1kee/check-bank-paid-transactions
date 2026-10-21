import tomllib
import unittest
from pathlib import Path

from bankcheck import __version__

ROOT = Path(__file__).resolve().parent.parent


class VersionTests(unittest.TestCase):
    def test_installed_version_matches_pyproject(self):
        with open(ROOT / "pyproject.toml", "rb") as f:
            expected = tomllib.load(f)["project"]["version"]
        self.assertEqual(
            __version__, expected, "Run 'uv sync' after changing the version in pyproject.toml"
        )

    def test_changelog_has_an_entry_for_the_version(self):
        changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        self.assertIn(f"## [{__version__}]", changelog)


if __name__ == "__main__":
    unittest.main()
