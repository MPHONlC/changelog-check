# Changelog Check

Compares the latest changelog entry across a BBCode forum (any forum using BBCode), GitHub Flavored Markdown, and Bethesda (CommonMark), ignoring each platform's own formatting/markup, and **fails the run if the underlying content differs**. Useful if you maintain the same changelog on all three platforms and want to catch a stale/mistyped entry before it goes out under one platform but not another.

It only compares bullet *content* (verb + description), not styling - a bolded word, a `<kbd>` tag, or a BBCode color won't trigger a mismatch, but a genuinely different word or a missing bullet will.

## Usage

```yaml
name: Changelog Content Check

on:
  push:
    branches: [main]
    paths:
      - 'CHANGELOG_BBCODE.txt'
      - 'CHANGELOG_GFM.txt'
      - 'CHANGELOG_COMMONMARK.txt'
  workflow_dispatch:

jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      - uses: MPHONlC/changelog-check@Version-0.0.1
```

## Inputs

| Input | Required | Default | Description |
|---|---|---|---|
| `bbcode_file` | No | *(auto-detect)* | Path to the BBCode-forum changelog file. Leave blank to auto-detect `CHANGELOG_BBCODE.txt`, then `CHANGELOG_ESOUI.txt` (any case). |
| `bbcode_version_marker` | No | `^\[b\]\[COLOR="Orange"\]Version ` | awk regex marking the start of a version entry in the BBCode file. |
| `github_file` | No | *(auto-detect)* | Path to the GitHub Flavored Markdown changelog file. Leave blank to auto-detect `CHANGELOG_GFM.txt`, then `CHANGELOG_GITHUB.txt` (any case). |
| `github_version_marker` | No | `^### Version ` | awk regex marking the start of a version entry in the GitHub file. |
| `bethesda_file` | No | *(auto-detect)* | Path to the Bethesda (CommonMark) changelog file. Leave blank to auto-detect `CHANGELOG_COMMONMARK.txt`, then `CHANGELOG_PLAINMARKDOWN.txt`, then `CHANGELOG_BETHESDA.txt` (any case). |
| `bethesda_version_marker` | No | `^# VERSION ` | awk regex marking the start of a version entry in the Bethesda file. |

Only the LATEST entry in each file is extracted and compared (each file's `*_version_marker` is used to find where one entry ends and the next begins) - this works whether a given file is cumulative (every version ever released) or single-entry (just the current one).

## What counts as a mismatch

Each file's markup is stripped down to plain bullet text (BBCode tags, `<kbd>`/`<sub>`/bold/link markdown removed), then compared bullet-for-bullet with an exact diff. A mismatch means the actual wording, not the formatting, differs - or a bullet is missing/extra on one platform.

<details>
<summary>Example step summary output on a real mismatch</summary>

````
## Changelog content comparison (formatting ignored)

Bullet counts: BBCode=4, GitHub=4, Bethesda=3

**BBCode vs GitHub: identical bullet content**

**GitHub vs Bethesda: differs**
```diff
--- GitHub
+++ Bethesda
@@ -1,4 +1,3 @@
 Fixed a crash when opening the settings menu.
 Added a new slash command for manual cleanup.
-Improved memory cleanup timing during loading screens.
 Removed the deprecated legacy config migration.
```

**BBCode vs Bethesda: differs**
```diff
--- BBCode
+++ Bethesda
@@ -1,4 +1,3 @@
 Fixed a crash when opening the settings menu.
 Added a new slash command for manual cleanup.
-Improved memory cleanup timing during loading screens.
 Removed the deprecated legacy config migration.
```
````

</details>

## License

MIT - see [LICENSE](LICENSE).
