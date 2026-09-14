import os
import re
import sys
import argparse
import difflib


PLATFORM_ALIASES = {
    'bbcode': ['BBCODE', 'ESOUI'],
    'gfm': ['GFM', 'GITHUB'],
    'commonmark': ['COMMONMARK', 'PLAINMARKDOWN', 'BETHESDA'],
}


def resolve_platform_file(explicit, prefix, kind):
    if explicit:
        return explicit
    aliases = PLATFORM_ALIASES[kind]
    try:
        entries = os.listdir('.')
    except OSError:
        entries = []
    for alias in aliases:
        pattern = re.compile(r'^' + re.escape(prefix) + r'_' + re.escape(alias) + r'\.txt$', re.IGNORECASE)
        for entry in entries:
            if pattern.match(entry):
                return entry
    return f'{prefix}_{aliases[0]}.txt'


def read(path):
    try:
        with open(path) as f:
            return f.read()
    except FileNotFoundError:
        return None


def clean_inline(s, kind):
    if kind == 'bbcode':
        s = re.sub(r'\[/?[A-Za-z]+(=[^\]]*)?\]', '', s)
    else:
        s = re.sub(r'</?kbd>', '', s)
        s = re.sub(r'</?sub>', '', s)
        s = re.sub(r'\*\*([^*]+)\*\*', r'\1', s)
        s = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', s)
    s = re.sub(r'[ \t]+', ' ', s).strip()
    return s


def extract_bullets_simple(text, marker_re, kind):
    bullets = []
    for line in text.splitlines():
        m = marker_re.match(line)
        if m:
            bullets.append(clean_inline(line[m.end():], kind))
    return bullets


def extract_bullets_wrapped(text):
    bullets = []
    in_bullet = False
    for line in text.splitlines():
        if line.startswith('#'):
            in_bullet = False
            continue
        m = re.match(r'^\*\s+', line)
        if m:
            bullets.append(clean_inline(line[m.end():], 'md'))
            in_bullet = True
        elif in_bullet and line.strip():
            bullets[-1] = bullets[-1] + ' ' + clean_inline(line, 'md')
        elif not line.strip():
            in_bullet = False
    if bullets:
        return bullets
    for line in text.splitlines():
        if line.startswith('#') or not line.strip():
            continue
        bullets.append(clean_inline(line, 'md'))
    return bullets


def extract_latest_entry(text, version_marker):
    marker_re = re.compile(version_marker)
    found = False
    out = []
    for line in text.splitlines():
        if marker_re.search(line):
            if found:
                break
            found = True
        if found:
            out.append(line)
    return '\n'.join(out)


def changelog_content_section(bbcode_raw, github_raw, bethesda_raw):
    out = ["## Changelog content comparison", ""]

    if not bbcode_raw:
        out.append("Could not extract a latest entry from the BBCode changelog - it's the reference source, so nothing else can be checked against it.")
        return out, False, []
    if not github_raw or not bethesda_raw:
        out.append("Could not extract a latest entry from one or more of the changelog files - skipping.")
        return out, False, []

    bbcode = extract_bullets_simple(bbcode_raw, re.compile(r'^\[\*\]\s*'), 'bbcode')
    github = extract_bullets_wrapped(github_raw)
    bethesda = extract_bullets_simple(bethesda_raw, re.compile(r'^-\s+'), 'md')

    out.append(f"Bullet counts: BBCode={len(bbcode)}, GitHub={len(github)}, Bethesda={len(bethesda)}")
    out.append("")

    pairs = [("BBCode", bbcode, "GitHub", github), ("GitHub", github, "Bethesda", bethesda), ("BBCode", bbcode, "Bethesda", bethesda)]
    any_diff = False
    differs_from_bbcode = []
    for name_a, a, name_b, b in pairs:
        diff = list(difflib.unified_diff(a, b, lineterm='', fromfile=name_a, tofile=name_b))
        if diff:
            any_diff = True
            if name_a == "BBCode":
                differs_from_bbcode.append(name_b)
            out.append(f"**{name_a} vs {name_b}: differs**")
            out.append("```diff")
            out.extend(diff)
            out.append("```")
        else:
            out.append(f"**{name_a} vs {name_b}: identical bullet content**")
        out.append("")

    if not any_diff:
        out.insert(2, "All three match exactly.")
        out.insert(3, "")

    return out, any_diff, differs_from_bbcode


def extract_plain_date(text):
    m = re.search(r'^Version:\s*(\S+)\s*\((\d{4}-\d{2}-\d{2})\)', text, re.M)
    return (m.group(1), m.group(2)) if m else None


def extract_bethesda_date(text):
    m = re.search(r'^#\s*VERSION\s+(\S+)\s*\((\d{4}-\d{2}-\d{2})\)', text, re.M | re.I)
    return (m.group(1), m.group(2)) if m else None


def extract_github_date(text):
    m = re.search(r'^###\s*Version\s+(\S+)', text, re.M)
    if not m:
        return None
    version = m.group(1)
    line = text[m.start():text.find('\n', m.start()) if '\n' in text[m.start():] else len(text)]
    date_m = re.search(r'\((\d{2})/(\d{2})/(\d{4})\)', line)
    if not date_m:
        return None
    return (version, f'{date_m.group(3)}-{date_m.group(1)}-{date_m.group(2)}')


def extract_bbcode_date(text):
    m = re.search(r'Version\s+([0-9][^\s\[\]:"]*)', text)
    if not m:
        return None
    version = m.group(1).rstrip(':')
    line = text[m.start():text.find('\n', m.start()) if '\n' in text[m.start():] else len(text)]
    date_m = re.search(r'\((\d{2})/(\d{2})/(\d{4})\)', line)
    if not date_m:
        return None
    return (version, f'{date_m.group(3)}-{date_m.group(1)}-{date_m.group(2)}')


def extract_manifest_version(text):
    m = re.search(r'^##\s*Version:\s*(\S+)', text, re.M)
    return m.group(1) if m else None


def extract_manifest_api_version(text):
    m = re.search(r'^##\s*APIVersion:\s*(.+)$', text, re.M)
    return m.group(1).strip() if m else None


def changelog_date_section(plain_file, bbcode_file, github_file, bethesda_file, manifest_file, bethesda_optional):
    sources = [
        ('CHANGELOG.md', plain_file, extract_plain_date, False),
        ('CHANGELOG_BBCODE.txt', bbcode_file, extract_bbcode_date, False),
        ('CHANGELOG_GFM.txt', github_file, extract_github_date, False),
        ('CHANGELOG_COMMONMARK.txt', bethesda_file, extract_bethesda_date, bethesda_optional),
    ]

    results = {}
    problems = []
    out = ["## Changelog date/version consistency check", ""]

    for label, path, extractor, optional in sources:
        text = read(path)
        if text is None:
            if optional:
                out.append(f"{label} ({path}): not found - treating as not yet published there, skipping.")
            else:
                problems.append(f"{label} ({path}): file not found")
            continue
        result = extractor(text)
        if result is None:
            problems.append(f"{label} ({path}): could not find a recognizable 'Version ... (date)' entry")
            continue
        results[label] = result

    api_version = None
    if manifest_file:
        manifest_text = read(manifest_file)
        if manifest_text is None:
            problems.append(f"manifest ({manifest_file}): file not found")
        else:
            manifest_version = extract_manifest_version(manifest_text)
            if manifest_version is None:
                problems.append(f"manifest ({manifest_file}): no '## Version:' field found")
            else:
                results['Manifest'] = (manifest_version, None)
            api_version = extract_manifest_api_version(manifest_text)

    out.append("| Source | Version | Date |")
    out.append("|---|---|---|")
    for label, (version, date) in results.items():
        out.append(f"| {label} | {version} | {date or '(n/a)'} |")
    out.append("")

    versions = {v for v, _ in results.values()}
    dates = {d for _, d in results.values() if d is not None}

    if len(versions) > 1:
        problems.append(f"Version numbers disagree: {sorted(versions)}")
    if len(dates) > 1:
        problems.append(f"Dates disagree (normalized to YYYY-MM-DD): {sorted(dates)}")

    if not problems:
        out.append(f"All sources agree: version `{versions.pop() if versions else '(none)'}`, date `{dates.pop() if dates else '(n/a)'}`.")

    if api_version:
        out.append(f"API Version (manifest): `{api_version}`")

    out.append("")

    return out, problems


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--bbcode-file', default='')
    parser.add_argument('--bbcode-version-marker', default=r'^\[b\]\[COLOR="Orange"\]Version ')
    parser.add_argument('--github-file', default='')
    parser.add_argument('--github-version-marker', default=r'^### Version ')
    parser.add_argument('--bethesda-file', default='')
    parser.add_argument('--bethesda-version-marker', default=r'^# VERSION ')
    parser.add_argument('--plain-file', default='CHANGELOG.md')
    parser.add_argument('--manifest-file', default='')
    parser.add_argument('--bethesda-optional', action='store_true')
    args = parser.parse_args()

    bbcode_file = resolve_platform_file(args.bbcode_file, 'CHANGELOG', 'bbcode')
    github_file = resolve_platform_file(args.github_file, 'CHANGELOG', 'gfm')
    bethesda_file = resolve_platform_file(args.bethesda_file, 'CHANGELOG', 'commonmark')

    bbcode_full = read(bbcode_file)
    github_full = read(github_file)
    bethesda_full = read(bethesda_file)

    bbcode_latest = extract_latest_entry(bbcode_full, args.bbcode_version_marker) if bbcode_full is not None else None
    github_latest = extract_latest_entry(github_full, args.github_version_marker) if github_full is not None else None
    bethesda_latest = extract_latest_entry(bethesda_full, args.bethesda_version_marker) if bethesda_full is not None else None

    date_out, date_problems = changelog_date_section(
        args.plain_file, bbcode_file, github_file, bethesda_file, args.manifest_file, args.bethesda_optional
    )
    content_out, content_mismatch, differs_from_bbcode = changelog_content_section(bbcode_latest, github_latest, bethesda_latest)

    report = date_out + content_out
    summary_path = os.environ.get('GITHUB_STEP_SUMMARY')
    if summary_path:
        with open(summary_path, 'a') as f:
            f.write('\n'.join(report) + '\n')
    else:
        print('\n'.join(report))

    for p in date_problems:
        print(f"::error::{p}")

    if content_mismatch and differs_from_bbcode:
        names = " and ".join(differs_from_bbcode)
        print(f"::error::Changelog content of {names} differs from BBCode - see the diff above.")
    elif content_mismatch:
        print("::error::Changelog content differs - see the diff above.")

    if date_problems or content_mismatch:
        sys.exit(1)


if __name__ == '__main__':
    main()
