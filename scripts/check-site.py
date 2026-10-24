#!/usr/bin/env python3
"""Check the website before it is published. Standard library only; runs locally and in GitHub Actions.

  python3 scripts/check-site.py                   check the public files in this repository
  python3 scripts/check-site.py --assemble _site  copy ONLY the public files into _site, then check that copy
  python3 scripts/check-site.py --draft           local preview only: unresolved {{...}} markers and a missing
                                                  sitemap are reported as warnings (deploys never use this)

Exit status: 0 = ready to publish, 1 = problems found, 2 = usage error.
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import struct
import sys
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parent.parent

PAGES = ["index.html", "terms-of-service.html", "privacy-statement.html"]
PUBLIC_FILES = PAGES + ["robots.txt", "sitemap.xml", ".nojekyll"]
ASSET_TYPES = {".css", ".svg", ".png"}
REQUIRED = PAGES + [
    "robots.txt",
    "assets/site.css",
    "assets/genie-gidsai-logo.svg",
    "assets/genie-gidsai-logo.png",
    "assets/genie-gidsai-logo-entra-215.png",
    "assets/favicon.svg",
    "assets/favicon-32.png",
    "assets/apple-touch-icon.png",
]
# path: (width, height, must be opaque, max bytes)
PNG_RULES = {
    # Microsoft Entra app logo: exactly 215x215 PNG, no transparency, no more than 100 KB.
    "assets/genie-gidsai-logo-entra-215.png": (215, 215, True, 100_000),
    "assets/apple-touch-icon.png": (180, 180, True, 100_000),
    "assets/favicon-32.png": (32, 32, False, 20_000),
    "assets/genie-gidsai-logo.png": (512, 512, False, 300_000),
}
# Files that must never be committed to this public repository.
FORBIDDEN_FILES = re.compile(
    r"(?i)(\.(db|sqlite3?|gguf|safetensors|onnx|pt|pth|ckpt|bin|pem|key|p12|pfx|kdbx|jsonl|log)$"
    r"|(^|/)\.env(\..*)?$|(^|/)id_(rsa|ed25519|ecdsa)(\.pub)?$|(^|/)\.git-credentials$)"
)
TEXT_TYPES = {".html", ".css", ".svg", ".txt", ".xml", ".md", ".yml", ".yaml", ".py", ".json", ""}
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}
NOT_ALLOWED_TAGS = {"script", "iframe", "object", "embed", "form", "style", "base", "frame", "frameset"}
PLACEHOLDER = re.compile(r"\{\{[^{}]*\}\}")
OTHER_PLACEHOLDERS = re.compile(r"\[Insert|\bTODO\b|\bFIXME\b|\blorem ipsum\b", re.I)
SECRETS = [
    ("a private key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("a GitHub token", re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{20,}|\bgithub_pat_[A-Za-z0-9_]{20,}")),
    ("a Google API key", re.compile(r"\bAIza[0-9A-Za-z_\-]{30,}")),
    ("an NVIDIA API key", re.compile(r"\bnvapi-[A-Za-z0-9_\-]{20,}")),
    ("an sk_/sk- style API key", re.compile(r"\bsk[_-][A-Za-z0-9_\-]{20,}")),
    ("a Slack token", re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}")),
    ("an AWS access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("a JSON web token", re.compile(r"\beyJ[A-Za-z0-9_\-]{15,}\.[A-Za-z0-9_\-]{15,}\.")),
    ("an assigned secret", re.compile(
        r"(?i)\b(?:password|passwd|secret|api[_-]?key|access[_-]?token|client[_-]?secret)\b\s*[:=]\s*['\"]?[A-Za-z0-9_\-/+]{12,}")),
]
PRIVATE = [
    ("a private IP address", re.compile(
        r"\b(?:10\.\d{1,3}\.\d{1,3}\.\d{1,3}|192\.168\.\d{1,3}\.\d{1,3}|172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3})\b")),
    ("an email address", re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")),
    ("a home-folder path", re.compile(r"/home/[a-z_][a-z0-9_\-]*")),
]
BAD_HOSTS = re.compile(r"(^|\.)(localhost|example\.(com|org|net))$|^127\.|^0\.0\.0\.0$|^::1$", re.I)
SVG_DANGER = re.compile(
    r"<script|\son[a-z]+\s*=|<foreignObject|<!ENTITY|<!DOCTYPE"
    r"|(?:xlink:)?href\s*=\s*[\"']\s*(?:https?:|//|data:|javascript:)", re.I)

GHA = os.environ.get("GITHUB_ACTIONS") == "true"


class Report:
    def __init__(self) -> None:
        self.errors = 0
        self.warnings = 0
        self.lines: list[str] = []

    @staticmethod
    def _esc(s: str, prop: bool = False) -> str:
        s = s.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
        return s.replace(":", "%3A").replace(",", "%2C") if prop else s

    def add(self, level: str, file: str, line: int | None, msg: str) -> None:
        if level == "error":
            self.errors += 1
        else:
            self.warnings += 1
        where = f"{file}:{line}" if line else file
        self.lines.append(f"- **{level}** `{where}`: {msg}")
        if GHA:
            props = f"file={self._esc(file, True)}" + (f",line={line}" if line else "")
            print(f"::{level} {props}::{self._esc(msg)}")
        else:
            print(f"{level.upper():7} {where}: {msg}")

    def error(self, file: str, msg: str, line: int | None = None) -> None:
        self.add("error", file, line, msg)

    def warn(self, file: str, msg: str, line: int | None = None) -> None:
        self.add("warning", file, line, msg)


class Page(HTMLParser):
    """Collects what the checks need from one HTML page and notices structural problems."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[tuple[str, int]] = []
        self.problems: list[tuple[int, str, str]] = []      # (line, level, message)
        self.ids: dict[str, int] = {}
        self.links: list[tuple[int, str, str, str]] = []    # (line, tag, attribute, value)
        self.lang = ""
        self.title = ""
        self.meta: set[str] = set()
        self.h1 = 0
        self._in_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        line = self.getpos()[0]
        a = {k: (v or "") for k, v in attrs}
        if tag == "html":
            self.lang = a.get("lang", "").strip()
        elif tag == "title":
            self._in_title = True
        elif tag == "meta":
            if "charset" in a:
                self.meta.add("charset")
            name = a.get("name", "").lower()
            if name in ("viewport", "description") and a.get("content", "").strip():
                self.meta.add(name)
            if a.get("http-equiv", "").lower() == "content-security-policy":
                self.meta.add("csp")
        elif tag == "h1":
            self.h1 += 1
        elif tag == "img":
            if "alt" not in a:
                self.problems.append((line, "error", "<img> needs an alt attribute (alt=\"\" if it is decorative)"))
            if not (a.get("width") and a.get("height")):
                self.problems.append((line, "warning", "<img> without width and height can make the page jump while loading"))
        elif tag == "a" and a.get("target") == "_blank" and "noopener" not in a.get("rel", ""):
            self.problems.append((line, "warning", "target=_blank links should have rel=\"noopener\""))
        if tag in NOT_ALLOWED_TAGS:
            self.problems.append((line, "error", f"<{tag}> is not allowed: this is a script-free static site with a strict CSP"))
        for key in a:
            if key.startswith("on"):
                self.problems.append((line, "error", f"inline event handler {key}= is not allowed"))
            elif key == "style":
                self.problems.append((line, "error", "inline style= is blocked by the Content-Security-Policy; use assets/site.css"))
        if a.get("id"):
            if a["id"] in self.ids:
                self.problems.append((line, "error", f"duplicate id \"{a['id']}\" (first on line {self.ids[a['id']]})"))
            else:
                self.ids[a["id"]] = line
        for attr in ("href", "src", "srcset", "action", "poster", "data"):
            if attr in a:
                self.links.append((line, tag, attr, a[attr]))
        if tag not in VOID:
            self.stack.append((tag, line))

    def handle_endtag(self, tag: str) -> None:
        line = self.getpos()[0]
        if tag in VOID:
            return
        if tag == "title":
            self._in_title = False
        if self.stack and self.stack[-1][0] == tag:
            self.stack.pop()
            return
        if any(t == tag for t, _ in self.stack):
            while self.stack and self.stack[-1][0] != tag:
                t, opened = self.stack.pop()
                self.problems.append((opened, "error", f"<{t}> is never closed (</{tag}> on line {line} closes an outer element)"))
            self.stack.pop()
        else:
            self.problems.append((line, "error", f"unexpected </{tag}>"))

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title += data


def png_info(path: Path) -> tuple[int, int, bool, int] | None:
    """(width, height, has transparency, size in bytes), or None if this is not a PNG."""
    data = path.read_bytes()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    pos, width, height, color_type, transparent = 8, 0, 0, -1, False
    while pos + 8 <= len(data):
        length, ctype = struct.unpack(">I4s", data[pos:pos + 8])
        chunk = data[pos + 8:pos + 8 + length]
        if ctype == b"IHDR":
            width, height, _depth, color_type = struct.unpack(">IIBB", chunk[:10])
        elif ctype == b"tRNS":
            transparent = True
        elif ctype == b"IEND":
            break
        pos += 12 + length
    return width, height, transparent or color_type in (4, 6), len(data)


def published(site: Path) -> set[str]:
    """Relative paths that are (or would be) published from this folder."""
    out = {name for name in PUBLIC_FILES if (site / name).is_file()}
    assets = site / "assets"
    if assets.is_dir():
        out |= {f"assets/{p.name}" for p in assets.iterdir()
                if p.is_file() and p.suffix.lower() in ASSET_TYPES and not p.name.startswith(".")}
    return out


def assemble(dest: Path, rep: Report) -> None:
    dest = dest.resolve()
    if dest == ROOT or ROOT not in dest.parents:
        sys.exit(f"--assemble needs a new folder inside the repository, not {dest}")
    if dest.exists():
        sys.exit(f"{dest.name} already exists; remove it first")
    (dest / "assets").mkdir(parents=True)
    for rel in sorted(published(ROOT)):
        shutil.copy2(ROOT / rel, dest / rel)
    for p in sorted((ROOT / "assets").iterdir()):
        if f"assets/{p.name}" not in published(ROOT):
            rep.warn(f"assets/{p.name}", "not published (only .css, .svg and .png files are)")


def check_link(site: Path, pub: set[str], page_rel: str, tag: str, attr: str, value: str,
               ids: dict[str, dict[str, int]]) -> str | None:
    v = value.strip()
    if not v:
        return "empty link"
    if attr == "srcset":
        return "srcset is not used on this site; use src"
    parts = urlsplit(v)
    if v.startswith("//"):
        return "protocol-relative links are not allowed; use https://"
    if parts.scheme:
        if parts.scheme != "https":
            return f"{parts.scheme}: links are not allowed (only https:// and relative links)"
        if BAD_HOSTS.search(parts.hostname or ""):
            return f"placeholder or local address ({parts.hostname})"
        if tag != "a":
            return f"<{tag} {attr}> would load a third-party resource; keep assets in this repository"
        return None
    path = unquote(parts.path)
    if path.startswith("/"):
        return "root-relative links break on a GitHub Pages project site; use a relative link"
    base = (site / page_rel).parent
    if not path:
        target = site / page_rel
    else:
        target = base / path
        if path.endswith("/") or target.is_dir():
            target = target / "index.html"
    try:
        rel = target.resolve().relative_to(site.resolve()).as_posix()
    except ValueError:
        return f"{v} points outside the website"
    if rel not in pub:
        return f"{v} points to {rel}, which is not published" if target.exists() else f"{v}: {rel} does not exist"
    if parts.fragment and rel.endswith(".html") and parts.fragment not in ids.get(rel, {}):
        return f"{v}: no element with id=\"{parts.fragment}\" in {rel}"
    return None


def check_text(rep: Report, rel: str, text: str, *, placeholders: bool, draft: bool) -> None:
    for i, line in enumerate(text.splitlines(), 1):
        for label, rx in SECRETS + PRIVATE:
            if rx.search(line):
                rep.error(rel, f"looks like {label}; this repository is public", i)
        if placeholders:
            if PLACEHOLDER.search(line):
                (rep.warn if draft else rep.error)(rel, f"unresolved marker {PLACEHOLDER.search(line).group(0)}", i)
            if OTHER_PLACEHOLDERS.search(line):
                rep.error(rel, f"placeholder text \"{OTHER_PLACEHOLDERS.search(line).group(0)}\"", i)


def check_repository(rep: Report, draft: bool) -> None:
    """Every file in the repository, published or not: no secrets, private data, databases or model files.
    Markdown files are also checked for unresolved {{...}} markers (workflow files use ${{ }} syntax, so they are not)."""
    for p in sorted(ROOT.rglob("*")):
        rel = p.relative_to(ROOT).as_posix()
        if not p.is_file() or rel.startswith((".git/", "_site/")) or "/__pycache__/" in f"/{rel}":
            continue
        if FORBIDDEN_FILES.search(rel):
            rep.error(rel, "this kind of file (database, model, key, log or environment file) must not be in the repository")
            continue
        if p.suffix.lower() in TEXT_TYPES and p.stat().st_size < 2_000_000:
            check_text(rep, rel, p.read_text(encoding="utf-8", errors="replace"),
                       placeholders=p.suffix.lower() == ".md", draft=draft)


def check_site(site: Path, rep: Report, draft: bool) -> set[str]:
    pub = published(site)
    for rel in REQUIRED:
        if rel not in pub:
            rep.error(rel, "required file is missing")
    if "sitemap.xml" not in pub:
        (rep.warn if draft else rep.error)("sitemap.xml", "missing (it needs the published address, added once the repository exists)")

    pages: dict[str, Page] = {}
    for rel in PAGES:
        if rel in pub:
            parser = Page()
            text = (site / rel).read_text(encoding="utf-8")
            parser.feed(text)
            parser.close()
            pages[rel] = parser
    ids = {rel: p.ids for rel, p in pages.items()}

    for rel, p in pages.items():
        for line, level, msg in p.problems:
            rep.add(level, rel, line, msg)
        for tag, line in p.stack:
            rep.error(rel, f"<{tag}> is never closed", line)
        if not p.lang:
            rep.error(rel, "<html> needs a lang attribute")
        if not p.title.strip():
            rep.error(rel, "the page needs a <title>")
        for need in ("charset", "viewport", "description"):
            if need not in p.meta:
                rep.error(rel, f"missing <meta {need}>")
        if "csp" not in p.meta:
            rep.warn(rel, "no Content-Security-Policy meta tag")
        if p.h1 != 1:
            rep.error(rel, f"expected exactly one <h1>, found {p.h1}")
        hrefs = {v.split("#")[0] for _, tag, attr, v in p.links if tag == "a"}
        for policy in ("terms-of-service.html", "privacy-statement.html"):
            if policy not in hrefs:
                rep.error(rel, f"every page must link to {policy}")
        for line, tag, attr, value in p.links:
            if PLACEHOLDER.search(value):
                continue                                    # reported once by the text check
            problem = check_link(site, pub, rel, tag, attr, value, ids)
            if problem:
                rep.error(rel, problem, line)

    for rel in sorted(pub):
        path = site / rel
        if path.suffix.lower() in {".html", ".css", ".svg", ".txt", ".xml"}:
            text = path.read_text(encoding="utf-8", errors="replace")
            check_text(rep, rel, text, placeholders=True, draft=draft)
            if path.suffix.lower() == ".svg":
                m = SVG_DANGER.search(text)
                if m:
                    rep.error(rel, f"unsafe SVG content: {m.group(0)!r}")

    for rel, (w, h, opaque, max_bytes) in PNG_RULES.items():
        if rel not in pub:
            continue
        info = png_info(site / rel)
        if info is None:
            rep.error(rel, "not a valid PNG file")
            continue
        width, height, transparent, size = info
        if (width, height) != (w, h):
            rep.error(rel, f"must be {w}x{h} pixels, is {width}x{height}")
        if opaque and transparent:
            rep.error(rel, "must not have transparency")
        if size > max_bytes:
            rep.error(rel, f"is {size:,} bytes; the limit is {max_bytes:,}")

    if "sitemap.xml" in pub:
        try:
            locs = [(e.text or "").strip() for e in ET.parse(site / "sitemap.xml").getroot().iter()
                    if e.tag.endswith("}loc")]
        except ET.ParseError as e:
            rep.error("sitemap.xml", f"is not valid XML: {e}")
            locs = []
        covered = set()
        for loc in locs:
            u = urlsplit(loc)
            name = u.path.rsplit("/", 1)[-1] or "index.html"
            if u.scheme != "https" or BAD_HOSTS.search(u.hostname or ""):
                rep.error("sitemap.xml", f"{loc} must be a real https:// address")
            elif name not in PAGES:
                rep.error("sitemap.xml", f"{loc} is not one of the site's pages")
            covered.add(name)
        for page in PAGES:
            if page not in covered:
                rep.error("sitemap.xml", f"does not list {page}")

    if "robots.txt" in pub:
        for i, line in enumerate((site / "robots.txt").read_text(encoding="utf-8").splitlines(), 1):
            if line.lower().startswith("sitemap:"):
                url = line.split(":", 1)[1].strip()
                if not url.startswith("https://") or not url.endswith("/sitemap.xml"):
                    rep.error("robots.txt", "the Sitemap line must be an https:// address ending in /sitemap.xml", i)

    total = sum((site / rel).stat().st_size for rel in pub)
    if total > 5_000_000:
        rep.warn(".", f"the published site is {total:,} bytes; keep it small")
    return pub


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--assemble", metavar="DIR", help="copy only the public files into DIR, then check DIR")
    ap.add_argument("--draft", action="store_true", help="local preview: unresolved markers are warnings")
    args = ap.parse_args()
    if args.assemble and args.draft:
        print("--draft cannot be combined with --assemble (deploys are always checked strictly)", file=sys.stderr)
        return 2

    rep = Report()
    check_repository(rep, args.draft)
    site = ROOT
    if args.assemble:
        site = Path(args.assemble)
        if not site.is_absolute():
            site = Path.cwd() / site
        assemble(site, rep)
    pub = check_site(site, rep, args.draft)

    if rep.errors:
        verdict = "NOT ready to publish"
    elif args.draft:
        verdict = "fine as a draft (run without --draft for the publishing check)"
    else:
        verdict = "ready to publish"
    print(f"\n{len(pub)} public files checked: {rep.errors} error(s), {rep.warnings} warning(s). The site is {verdict}.")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as f:
            f.write(f"### Website check: {verdict}\n\n{len(pub)} public files, {rep.errors} error(s), "
                    f"{rep.warnings} warning(s).\n\n")
            f.write("\n".join(rep.lines[:200]) + ("\n\n" if rep.lines else ""))
            f.write("<details><summary>Published files</summary>\n\n" + "\n".join(f"- `{p}`" for p in sorted(pub)) + "\n\n</details>\n")
    return 1 if rep.errors else 0


if __name__ == "__main__":
    sys.exit(main())
