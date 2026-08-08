#!/usr/bin/env python3
"""Render docs/user/*.md to committed HTML under landing/docs/.

Idempotent: no timestamps, no randomness. CI re-runs this and fails on diff.
"""

from __future__ import annotations

import html
import re
import sys
from pathlib import Path

import markdown

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "docs" / "user"
OUT = ROOT / "landing" / "docs"

# Door order — drives index.html ordering and nav
PAGES = ["agents", "getting-started", "commands", "providers", "configuration", "troubleshooting"]

FRONTMATTER = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)
MD_LINK = re.compile(r"\]\((?!https?://|#|/)([\w-]+)\.md(#[\w-]*)?\)")

NAV_LABELS = {
    "agents": "Agents",
    "getting-started": "Getting started",
    "commands": "Commands",
    "providers": "Providers",
    "configuration": "Configuration",
    "troubleshooting": "Troubleshooting",
}

# Styling sampled from landing/index.html's :root (dark bg, warm ink, amber signal).
STYLE = """
  :root {
    --bg: #0E0D0B; --bg-2: #15130F; --bg-3: #1E1B16;
    --ink: #ECE8DC; --ink-2: #B6AE9D; --ink-3: #8D8574;
    --rule: rgba(236,232,220,0.08); --rule-2: rgba(236,232,220,0.14);
    --signal: #F5A524; --phosphor: #C8E887;
    --display: "Unbounded", "Helvetica Neue", system-ui, sans-serif;
    --sans: "Geist", -apple-system, BlinkMacSystemFont, "Helvetica Neue", sans-serif;
    --mono: "Geist Mono", ui-monospace, "SF Mono", Menlo, monospace;
  }
  *, *::before, *::after { box-sizing: border-box; }
  body { margin: 0; background: var(--bg); color: var(--ink); font-family: var(--sans);
         font-size: 17px; line-height: 1.7; -webkit-font-smoothing: antialiased; }
  a { color: var(--signal); text-decoration: none; }
  a:hover { text-decoration: underline; }
  header { border-bottom: 1px solid var(--rule); padding: 20px clamp(20px,5vw,56px); }
  header nav { display: flex; flex-wrap: wrap; gap: 8px 20px; align-items: baseline;
               max-width: 860px; margin: 0 auto; font-size: 14px; }
  header .home { font-family: var(--mono); color: var(--ink); margin-right: 8px; }
  header nav a.here { color: var(--phosphor); }
  header nav a { color: var(--ink-3); }
  main { max-width: 860px; margin: 0 auto; padding: 48px clamp(20px,5vw,56px) 96px; }
  h1, h2, h3, h4 { font-family: var(--display); font-weight: 400; letter-spacing: -0.03em;
                   line-height: 1.25; margin: 2em 0 0.6em; }
  h1 { font-size: clamp(30px, 5vw, 42px); margin-top: 0; }
  h2 { font-size: 26px; padding-top: 20px; border-top: 1px solid var(--rule); }
  h3 { font-size: 20px; }
  p, li { color: var(--ink-2); }
  strong { color: var(--ink); }
  code { font-family: var(--mono); font-size: 0.88em; background: var(--bg-3);
         border: 1px solid var(--rule); border-radius: 4px; padding: 1px 5px; color: var(--phosphor); }
  pre { background: var(--bg-2); border: 1px solid var(--rule); border-radius: 8px;
        padding: 16px; overflow-x: auto; }
  pre code { background: none; border: 0; padding: 0; color: var(--ink); }
  blockquote { margin: 1.5em 0; padding: 2px 0 2px 18px; border-left: 2px solid var(--signal);
               color: var(--ink-3); }
  table { border-collapse: collapse; width: 100%; display: block; overflow-x: auto; margin: 1.5em 0; }
  th, td { border: 1px solid var(--rule-2); padding: 8px 12px; text-align: left; font-size: 15px;
           color: var(--ink-2); }
  th { color: var(--ink); font-weight: 600; background: var(--bg-2); }
  hr { border: 0; border-top: 1px solid var(--rule); margin: 3em 0; }
  .cards { display: grid; gap: 16px; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); }
  .card { display: block; background: var(--bg-2); border: 1px solid var(--rule);
          border-radius: 10px; padding: 20px; color: inherit; }
  .card:hover { border-color: var(--signal); text-decoration: none; }
  .card h2 { font-size: 19px; margin: 0 0 6px; border: 0; padding: 0; color: var(--ink); }
  .card p { margin: 0; font-size: 15px; color: var(--ink-3); }
"""

TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width,initial-scale=1" />
<title>{title} — anyscribe docs</title>
<link rel="icon" type="image/svg+xml" href="data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'><rect width='32' height='32' rx='6' fill='%230E0D0B'/><circle cx='16' cy='16' r='4.5' fill='%23F5A524'/></svg>" />
<style>{style}</style>
</head>
<body>
<header><nav><a class="home" href="/">anyscribe</a>{nav}</nav></header>
<main>
{body}
</main>
</body>
</html>
"""


def nav_html(current: str) -> str:
    links = ['<a href="/docs"%s>Docs</a>' % (' class="here"' if current == "index" else "")]
    for stem in PAGES:
        cls = ' class="here"' if stem == current else ""
        links.append(f'<a href="/docs/{stem}"{cls}>{NAV_LABELS[stem]}</a>')
    return "".join(links)


def read_page(stem: str) -> tuple[dict[str, str], str]:
    text = (SRC / f"{stem}.md").read_text()
    meta: dict[str, str] = {}
    m = FRONTMATTER.match(text)
    if m:
        for line in m.group(1).splitlines():
            if ":" in line and not line.startswith((" ", "-")):
                k, _, v = line.partition(":")
                meta[k.strip()] = v.strip().strip('"')
        text = text[m.end() :]
    return meta, text


def render(stem: str) -> str:
    meta, text = read_page(stem)
    text = MD_LINK.sub(r"](/docs/\1\2)", text)  # sibling .md links → clean URLs
    body = markdown.markdown(text, extensions=["tables", "fenced_code", "toc"])
    title = html.escape(meta.get("title") or NAV_LABELS.get(stem, stem))
    return TEMPLATE.format(title=title, style=STYLE, nav=nav_html(stem), body=body)


def render_index() -> str:
    cards = []
    for stem in PAGES:
        meta, _ = read_page(stem)
        title = html.escape(meta.get("title") or NAV_LABELS[stem])
        summary = html.escape(meta.get("summary", ""))
        cards.append(
            f'<a class="card" href="/docs/{stem}"><h2>{title}</h2><p>{summary}</p></a>'
        )
    body = "<h1>anyscribe docs</h1>\n<div class=\"cards\">\n" + "\n".join(cards) + "\n</div>"
    return TEMPLATE.format(
        title="Documentation", style=STYLE, nav=nav_html("index"), body=body
    )


HREF = re.compile(r'href="([^"]*)"')
ID = re.compile(r'\sid="([^"]+)"')
OK_SCHEMES = ("http://", "https://", "mailto:", "data:")


def check_links(pages: dict[str, str]) -> list[str]:
    """Every link must be an allowed scheme, a site-absolute path, or an anchor;
    every /docs/<x> target a real page, and every #anchor a real rendered id."""
    ids = {name: set(ID.findall(doc)) for name, doc in pages.items()}
    problems = []
    for name, doc in pages.items():
        for href in HREF.findall(doc):
            if href.startswith(OK_SCHEMES):
                continue
            path, _, anchor = href.partition("#")
            if path and not path.startswith("/"):
                # relative links (../building/foo.md) 404 on the deployed site
                problems.append(f"{name}.html: unsupported link {href}")
                continue
            target = name
            if path.rstrip("/") == "/docs":
                target = "index"
            elif path.startswith("/docs/"):
                target = path.rstrip("/").rsplit("/", 1)[-1]
                if target not in PAGES:
                    problems.append(f"{name}.html: link to unknown page {path}")
                    continue
            elif path:
                continue  # some other page of the site; not ours to validate
            if anchor and anchor not in ids[target]:
                problems.append(f"{name}.html: broken anchor {href}")
    return problems


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    pages = {stem: render(stem) for stem in PAGES}
    pages["index"] = render_index()
    problems = check_links(pages)
    if problems:
        for p in problems:
            print(p, file=sys.stderr)
        return 1
    for name, doc in pages.items():
        (OUT / f"{name}.html").write_text(doc)
    print(f"rendered {len(PAGES)} pages + index → {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
