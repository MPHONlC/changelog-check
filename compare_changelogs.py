import re
import sys
import difflib


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
    return bullets


def read(path):
    try:
        with open(path) as f:
            return f.read()
    except FileNotFoundError:
        return None


def changelog_section():
    out = ["## Changelog content comparison (formatting ignored)", ""]
    bbcode_raw = read('latest_changes_bbcode.txt')
    github_raw = read('latest_changes_github.md')
    bethesda_raw = read('latest_changes_bethesda.txt')

    if bbcode_raw is None or github_raw is None or bethesda_raw is None:
        out.append("Could not read one or more of the three extracted changelog files - skipping.")
        return out, False

    bbcode = extract_bullets_simple(bbcode_raw, re.compile(r'^\[\*\]\s*'), 'bbcode')
    github = extract_bullets_wrapped(github_raw)
    bethesda = extract_bullets_simple(bethesda_raw, re.compile(r'^-\s+'), 'md')

    out.append(f"Bullet counts: BBCode={len(bbcode)}, GitHub={len(github)}, Bethesda={len(bethesda)}")
    out.append("")

    pairs = [("BBCode", bbcode, "GitHub", github), ("GitHub", github, "Bethesda", bethesda), ("BBCode", bbcode, "Bethesda", bethesda)]
    any_diff = False
    for name_a, a, name_b, b in pairs:
        diff = list(difflib.unified_diff(a, b, lineterm='', fromfile=name_a, tofile=name_b))
        if diff:
            any_diff = True
            out.append(f"**{name_a} vs {name_b}: differs**")
            out.append("```diff")
            out.extend(diff)
            out.append("```")
        else:
            out.append(f"**{name_a} vs {name_b}: identical bullet content**")
        out.append("")

    if not any_diff:
        out.insert(2, "All three match exactly (ignoring markup).")
        out.insert(3, "")

    return out, any_diff


def main():
    changelog_out, changelog_mismatch = changelog_section()
    print('\n'.join(changelog_out))

    if changelog_mismatch:
        print()
        print("::error::Changelog content differs between BBCode, GitHub, and Bethesda (ignoring formatting) - see the diff above.")
        sys.exit(1)


if __name__ == '__main__':
    main()
