#!/usr/bin/env python3
"""
Builds top-langs.svg (the "Top Languages" card for the GitHub profile).

It reads the public repositories of the user, adds up the code size of every
language, and draws the result as a small SVG picture. No third-party service
is used, so the card cannot go offline.

Run by hand:   python scripts/top_langs.py
Preview only:  python scripts/top_langs.py --demo
"""
import json
import os
import sys
import urllib.request
from xml.sax.saxutils import escape

USER = os.environ.get("GH_USER", "Hyzen-collab")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
OUTPUT = os.environ.get("OUTPUT", "top-langs.svg")
MAX_LANGS = int(os.environ.get("MAX_LANGS", "6"))

# Languages you do not want in the card, e.g. EXCLUDE_LANGS="HTML,CSS"
EXCLUDE_LANGS = {x.strip() for x in os.environ.get("EXCLUDE_LANGS", "").split(",") if x.strip()}
# Repositories you do not want counted (the profile repository itself is skipped automatically)
EXCLUDE_REPOS = {x.strip() for x in os.environ.get("EXCLUDE_REPOS", "").split(",") if x.strip()} | {USER}

COLORS = {
    "C++": "#f34b7d", "C": "#8a8a8a", "C#": "#178600", "Dart": "#00b4ab", "Python": "#3572a5",
    "JavaScript": "#f1e05a", "TypeScript": "#3178c6", "PHP": "#8892bf", "HTML": "#e34c26",
    "CSS": "#9b6bdf", "Java": "#b07219", "Kotlin": "#a97bff", "Swift": "#f05138",
    "Shell": "#89e051", "SQL": "#e38c00", "Go": "#00add8", "Rust": "#dea584",
}
FALLBACK = ["#58a6ff", "#d2a8ff", "#ffa657", "#7ee787", "#ff7b72", "#79c0ff"]


def api(url):
    """Calls the GitHub API and returns the JSON answer."""
    request = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": "top-langs-card",
        **({"Authorization": "Bearer " + TOKEN} if TOKEN else {}),
    })
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def collect_languages():
    """Returns {language: bytes of code} for all own, non-fork repositories."""
    totals = {}
    page = 1
    while True:
        repos = api(f"https://api.github.com/users/{USER}/repos?type=owner&per_page=100&page={page}")
        if not repos:
            break
        for repo in repos:
            if repo["fork"] or repo["name"] in EXCLUDE_REPOS:
                continue
            for language, size in api(repo["languages_url"]).items():
                if language not in EXCLUDE_LANGS:
                    totals[language] = totals.get(language, 0) + size
        page += 1
    return totals


def demo_languages():
    """Sample numbers, only for previewing the design."""
    return {"C++": 450, "Dart": 200, "JavaScript": 120, "PHP": 80, "Python": 60, "HTML": 50, "C#": 40}


def build_svg(totals):
    total = sum(totals.values()) or 1
    ranked = sorted(totals.items(), key=lambda item: item[1], reverse=True)
    top, rest = ranked[:MAX_LANGS], ranked[MAX_LANGS:]
    if rest:
        top.append(("Other", sum(size for _, size in rest)))

    width, pad = 495, 28
    bar_w = width - pad * 2
    rows = (len(top) + 1) // 2
    height = 104 + rows * 30

    # Colour bar, split into one piece per language
    pieces, x = [], pad
    for index, (name, size) in enumerate(top):
        w = bar_w * size / total
        color = COLORS.get(name, FALLBACK[index % len(FALLBACK)]) if name != "Other" else "#6e7681"
        pieces.append(f'<rect x="{x:.2f}" y="70" width="{w + 0.5:.2f}" height="10" fill="{color}"/>')
        x += w

    # Legend in two columns
    legend = []
    for index, (name, size) in enumerate(top):
        color = COLORS.get(name, FALLBACK[index % len(FALLBACK)]) if name != "Other" else "#6e7681"
        cx = pad + (index % 2) * (bar_w / 2)
        cy = 112 + (index // 2) * 30
        legend.append(
            f'<circle cx="{cx + 5:.1f}" cy="{cy - 4}" r="5" fill="{color}"/>'
            f'<text x="{cx + 18:.1f}" y="{cy}" class="name">{escape(name)}</text>'
            f'<text x="{cx + bar_w / 2 - 22:.1f}" y="{cy}" class="pct" text-anchor="end">{size / total * 100:.1f}%</text>'
        )

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="Top languages">
  <style>
    text {{ font-family: -apple-system, "Segoe UI", Helvetica, Arial, sans-serif; }}
    .title {{ font-size: 20px; font-weight: 700; fill: #f0f6fc; }}
    .sub   {{ font-size: 12px; fill: #8b949e; }}
    .name  {{ font-size: 14px; fill: #e6edf3; }}
    .pct   {{ font-size: 14px; fill: #8b949e; }}
  </style>
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#161b22"/><stop offset="1" stop-color="#0d1117"/>
    </linearGradient>
    <clipPath id="round"><rect x="{pad}" y="70" width="{bar_w}" height="10" rx="5"/></clipPath>
  </defs>
  <rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="14" fill="url(#bg)" stroke="#30363d"/>
  <rect x="{pad}" y="26" width="4" height="22" rx="2" fill="#f34b7d"/>
  <text x="{pad + 14}" y="43" class="title">Top Languages</text>
  <text x="{pad}" y="62" class="sub">Based on public repositories of @{escape(USER)}</text>
  <g clip-path="url(#round)">{"".join(pieces)}</g>
  {"".join(legend)}
</svg>
'''


def main():
    totals = demo_languages() if "--demo" in sys.argv else collect_languages()
    if not totals:
        sys.exit("No languages found, the old card was kept.")
    with open(OUTPUT, "w", encoding="utf-8") as file:
        file.write(build_svg(totals))
    print(f"Saved {OUTPUT} with {len(totals)} languages")


if __name__ == "__main__":
    main()
