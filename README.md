# Changelog Check

Checks a project's changelog across four sources in one report: the plain-setext `CHANGELOG.md`, a BBCode-forum file (any forum using BBCode), a GitHub Flavored Markdown file (kbd-markdown, `MM/DD/YYYY`), and a Bethesda file (CommonMark) - plus, optionally, the `.addon` manifest.

It checks two things and **fails the run on either**:
- **Version/date consistency**: the latest entry's version and date agree across all sources.
- **Content**: the latest entry's bullet content agrees across BBCode, GitHub, and Bethesda, ignoring each platform's own formatting/markup (a bolded word, a `<kbd>` tag, a BBCode color won't trigger a mismatch, but a genuinely different word or a missing bullet will).

## Usage

```yaml
name: Changelog Check

on:
  push:
    branches: [main]
    paths:
      - 'CHANGELOG.md'
      - 'CHANGELOG_BBCODE.txt'
      - 'CHANGELOG_GFM.txt'
      - 'CHANGELOG_COMMONMARK.txt'
  workflow_dispatch:

jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      - uses: MPHONlC/changelog-check@Version-0.0.2
        with:
          manifest_file: 'YourAddon.addon'
```

## Inputs

| Input | Required | Default | Description |
|---|---|---|---|
| `plain_file` | No | `CHANGELOG.md` | Plain-setext root changelog. |
| `bbcode_file` | No | *(auto-detect)* | Path to the BBCode-forum changelog file. Leave blank to auto-detect `CHANGELOG_BBCODE.txt`, then `CHANGELOG_ESOUI.txt` (any case). |
| `bbcode_version_marker` | No | `^\[b\]\[COLOR="Orange"\]Version ` | Regex marking the start of a version entry in the BBCode file. |
| `github_file` | No | *(auto-detect)* | Path to the GitHub Flavored Markdown changelog file. Leave blank to auto-detect `CHANGELOG_GFM.txt`, then `CHANGELOG_GITHUB.txt` (any case). |
| `github_version_marker` | No | `^### Version ` | Regex marking the start of a version entry in the GitHub file. |
| `bethesda_file` | No | *(auto-detect)* | Path to the Bethesda (CommonMark) changelog file. Leave blank to auto-detect `CHANGELOG_COMMONMARK.txt`, then `CHANGELOG_PLAINMARKDOWN.txt`, then `CHANGELOG_BETHESDA.txt` (any case). |
| `bethesda_version_marker` | No | `^# VERSION ` | Regex marking the start of a version entry in the Bethesda file. |
| `manifest_file` | No | `''` | Optional `.addon` manifest to also cross-check the version against and to report the API version. Leave blank to skip. |
| `bethesda_optional` | No | `false` | If `true`, a missing Bethesda file is treated as "not published there yet" instead of an error. |

Only the LATEST entry in each file is extracted and compared (each file's `*_version_marker` finds where one entry ends and the next begins) - this works whether a given file is cumulative (every version ever released) or single-entry (just the current one).

A changelog entry that's a single plain sentence with no bullet marker at all (e.g. an initial-release changelog reading just "Initial release.") is treated as one bullet on every platform, the same as an explicit `[*]`/`-`/`* ` bullet would be.

## License

MIT - see [LICENSE](LICENSE).
