#!/usr/bin/env python3
"""Check an ILIAS translation against its source without hiding existing defects.

Example: python3 scripts/validate_language.py --language pt --changed-since v11.4
Omit --changed-since for a complete structural audit. A successful check verifies
keys and interpolation/markup contracts, not the semantic quality of translations.
"""

import argparse
from collections import Counter
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
PRINTF = re.compile(r"%%|%(?:\d+\$)?[-+0# ]*(?:\d+|\*)?(?:\.(?:\d+|\*))?[bcdeEfFgGosuxX]")
NAMED = re.compile(r"\[/?[A-Z][A-Z0-9_]*\]")
POSITIONAL = re.compile(r"%[1-9]\d*(?![\dA-Za-z$])")
DOLLAR_POSITIONAL = re.compile(r"\$[1-9]\d*\$")
START = "<!-- language file start -->"
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}


class Markup(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.tags = Counter()
        self.attributes = Counter()

    def handle_starttag(self, tag, attrs):
        self.tags[("start", tag)] += 1
        for name, value in attrs:
            # Visible alternative text and tooltips may be translated.
            if name not in {"alt", "title", "aria-label"}:
                self.attributes[(tag, name, value)] += 1

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if tag not in VOID:
            self.tags[("end", tag)] += 1


def contracts(value):
    markup = Markup()
    markup.feed(value)
    return {
        "printf": Counter(PRINTF.findall(value)),
        "named": Counter(NAMED.findall(value)),
        "positional": Counter(POSITIONAL.findall(PRINTF.sub("", value))),
        "dollar_positional": Counter(DOLLAR_POSITIONAL.findall(value)),
        "html_tags": markup.tags,
        "html_attributes": markup.attributes,
    }


def parse(text, label):
    rows = {}
    issues = []
    started = False
    for number, line in enumerate(text.splitlines(), 1):
        if not started:
            started = line.strip() == START
            continue
        parts = line.strip().split("#:#")
        if len(parts) != 3:
            issues.append({"kind": "syntax", "file": label, "line": number})
            continue
        module, key, raw = parts
        identity = (module, key)
        if not module or not key:
            issues.append({"kind": "empty_key", "file": label, "line": number})
            continue
        if identity in rows:
            issues.append({"kind": "duplicate", "file": label, "line": number, "key": "/".join(identity)})
        rows[identity] = raw.split("###", 1)[0].strip()
    if not started:
        issues.append({"kind": "missing_header", "file": label})
    return rows, issues


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--language", default="pt")
    parser.add_argument("--source", default="en")
    parser.add_argument("--changed-since", help="Validate values changed since this Git revision; report inherited issues separately.")
    parser.add_argument("--module", action="append", help="Limit value checks to this module (repeatable).")
    parser.add_argument("--json", action="store_true", help="Emit all findings as JSON.")
    args = parser.parse_args()
    if not re.fullmatch(r"[a-z]{2}", args.language) or not re.fullmatch(r"[a-z]{2}", args.source):
        parser.error("Language identifiers must be two lowercase ISO 639 letters.")
    target_path = f"lang/ilias_{args.language}.lang"
    source, source_issues = parse((ROOT / f"lang/ilias_{args.source}.lang").read_text(encoding="utf-8"), args.source)
    target, issues = parse((ROOT / target_path).read_text(encoding="utf-8"), args.language)
    for key in sorted(source.keys() - target.keys()):
        issues.append({"kind": "missing_key", "key": "/".join(key)})
    for key in sorted(target.keys() - source.keys()):
        issues.append({"kind": "extra_key", "key": "/".join(key)})
    baseline = None
    if args.changed_since:
        old = subprocess.run(["git", "show", f"{args.changed_since}:{target_path}"], cwd=ROOT, text=True, capture_output=True, check=True)
        baseline, _ = parse(old.stdout, "baseline")
    checked = equal = inherited = 0
    for key in sorted(source.keys() & target.keys()):
        if args.module and key[0] not in args.module:
            continue
        equal += source[key] == target[key]
        expected, actual = contracts(source[key]), contracts(target[key])
        mismatches = [name for name in expected if expected[name] != actual[name]]
        if baseline is not None and baseline.get(key) == target[key]:
            inherited += bool(mismatches)
            continue
        checked += 1
        for kind in mismatches:
            issues.append({"kind": kind, "key": "/".join(key)})
    result = {
        "source_keys": len(source), "translation_keys": len(target), "checked_values": checked,
        "equal_to_source": equal, "inherited_contract_issues": inherited,
        "source_issues": source_issues, "issues": issues,
    }
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(json.dumps({k: v if not isinstance(v, list) else len(v) for k, v in result.items()}, ensure_ascii=False))
        for issue in issues[:20]:
            print(json.dumps(issue, ensure_ascii=False))
        if len(issues) > 20:
            print(f"... {len(issues) - 20} additional findings; use --json for the full list.")
    return bool(issues)


if __name__ == "__main__":
    sys.exit(main())
