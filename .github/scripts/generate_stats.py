#!/usr/bin/env python3
import json
import os
import urllib.request
from collections import defaultdict
from html import escape
from pathlib import Path

API = "https://api.github.com/graphql"
USERNAME = os.environ.get("USERNAME", "")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
OUT = Path("assets/stats.svg")

QUERY = r"""
query($login: String!) {
  user(login: $login) {
    repositories(first: 100, ownerAffiliations: OWNER, privacy: PUBLIC) {
      nodes {
        name
        isFork
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
          edges {
            size
            node { name }
          }
        }
      }
    }
    contributionsCollection {
      totalCommitContributions
      contributionCalendar {
        totalContributions
      }
    }
  }
}
"""

def request_data():
    body = json.dumps({"query": QUERY, "variables": {"login": USERNAME}}).encode()
    req = urllib.request.Request(
        API,
        data=body,
        headers={
            "Authorization": f"bearer {TOKEN}",
            "Content-Type": "application/json",
            "User-Agent": "YSimatov-profile-stats",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        payload = json.loads(r.read().decode())
    if payload.get("errors"):
        raise RuntimeError(payload["errors"])
    return payload["data"]["user"]

def render(commits, repos, contributions, top_language):
    top_language = escape(top_language or "—")
    return f"""<svg width="1200" height="190" viewBox="0 0 1200 190" fill="none" xmlns="http://www.w3.org/2000/svg">
<defs>
  <linearGradient id="bg" x1="0" y1="0" x2="1200" y2="190" gradientUnits="userSpaceOnUse">
    <stop stop-color="#08040E"/>
    <stop offset="0.55" stop-color="#10071A"/>
    <stop offset="1" stop-color="#071019"/>
  </linearGradient>
  <filter id="g"><feGaussianBlur stdDeviation="3" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
  <pattern id="grid" width="28" height="28" patternUnits="userSpaceOnUse">
    <path d="M28 0H0V28" stroke="#A855F7" stroke-opacity=".045"/>
  </pattern>
</defs>
<rect x="1" y="1" width="1198" height="188" rx="18" fill="url(#bg)" stroke="#7C3AED" stroke-opacity=".30"/>
<rect x="1" y="1" width="1198" height="188" rx="18" fill="url(#grid)"/>
<text x="42" y="38" fill="#8B8198" font-size="12" font-family="ui-monospace,Consolas,monospace" letter-spacing="2">SYSTEM // LIVE STATS</text>
<circle cx="1148" cy="33" r="3.5" fill="#22D3EE" filter="url(#g)"><animate attributeName="opacity" values="1;.3;1" dur="2.2s" repeatCount="indefinite"/></circle>
<path d="M42 57H1158" stroke="#7C3AED" stroke-opacity=".20"/>
<g font-family="ui-monospace,Consolas,monospace">
  <text x="88" y="94" fill="#6F647A" font-size="11" letter-spacing="1.2">12M COMMITS</text>
  <text x="88" y="139" fill="#C084FC" font-size="25" font-weight="700">{commits}</text>

  <text x="365" y="94" fill="#6F647A" font-size="11" letter-spacing="1.2">PUBLIC REPOS</text>
  <text x="365" y="139" fill="#E9E4F0" font-size="25" font-weight="700">{repos}</text>

  <text x="648" y="94" fill="#6F647A" font-size="11" letter-spacing="1.2">12M CONTRIBUTIONS</text>
  <text x="648" y="139" fill="#22D3EE" font-size="25" font-weight="700">{contributions}</text>

  <text x="955" y="94" fill="#6F647A" font-size="11" letter-spacing="1.2">TOP LANGUAGE</text>
  <text x="955" y="139" fill="#C084FC" font-size="25" font-weight="700">{top_language}</text>
</g>
</svg>"""

def main():
    if not USERNAME or not TOKEN:
        print("USERNAME or GITHUB_TOKEN is missing; keeping existing stats card.")
        return

    try:
        user = request_data()
        nodes = user["repositories"]["nodes"] or []
        own_repos = [
            r for r in nodes
            if not r.get("isFork") and r.get("name", "").lower() != USERNAME.lower()
        ]

        langs = defaultdict(int)
        for repo in own_repos:
            for edge in (repo.get("languages") or {}).get("edges", []):
                langs[edge["node"]["name"]] += int(edge.get("size", 0))

        top_language = max(langs.items(), key=lambda x: x[1])[0] if langs else "—"
        cc = user["contributionsCollection"]
        commits = cc["totalCommitContributions"]
        contributions = cc["contributionCalendar"]["totalContributions"]

        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(
            render(commits, len(own_repos), contributions, top_language),
            encoding="utf-8",
        )
        print("Updated", OUT)
    except Exception as exc:
        # Do not break the 3D contribution update if the stats endpoint has a transient issue.
        print(f"Stats update skipped: {exc}")

if __name__ == "__main__":
    main()
