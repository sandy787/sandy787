#!/usr/bin/env python3
"""Render assets/phone.svg: an iPhone "Spotlight" card built from live GitHub data.

Usage:
  GITHUB_TOKEN=... python scripts/render_phone.py            # live data via GraphQL
  python scripts/render_phone.py --sample                    # offline sample data

Data sources (all from the GitHub GraphQL API):
  - contributionsCollection.contributionCalendar  -> 52-week heatmap, totals, streak
  - repositories(stargazerCount)                  -> total stars
  - followers.totalCount
"""
import argparse
import datetime as dt
import json
import os
import sys
import urllib.request

USER = os.environ.get("GH_USER", "sandy787")
OUT = os.environ.get("PHONE_OUT", "assets/phone.svg")

# GitHub's dark-theme contribution palette, level 0..4
LEVELS = ["#1b2129", "#0e4429", "#006d32", "#26a641", "#39d353"]

APPS = [
    ("GoDAM Studio", "App Store", "#1f6feb"),
    ("PDF Auto Unlocker", "Mac App Store", "#d29922"),
    ("Sikandar", "Score tracker · iOS & iPadOS", "#8957e5"),
]

QUERY = """
query($login: String!) {
  user(login: $login) {
    followers { totalCount }
    repositories(first: 100, ownerAffiliations: OWNER, isFork: false) {
      nodes { stargazerCount }
    }
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount contributionLevel } }
      }
    }
  }
}
"""

LEVEL_NAMES = {
    "NONE": 0, "FIRST_QUARTILE": 1, "SECOND_QUARTILE": 2,
    "THIRD_QUARTILE": 3, "FOURTH_QUARTILE": 4,
}


def fetch_live(token):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": USER}}).encode(),
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        data = json.load(r)
    if "errors" in data:
        raise SystemExit(f"GraphQL error: {data['errors']}")
    u = data["data"]["user"]
    cal = u["contributionsCollection"]["contributionCalendar"]
    weeks = []
    for w in cal["weeks"]:
        weeks.append([
            {"date": d["date"], "count": d["contributionCount"],
             "level": LEVEL_NAMES.get(d["contributionLevel"], 0)}
            for d in w["contributionDays"]
        ])
    return {
        "weeks": weeks,
        "total": cal["totalContributions"],
        "stars": sum(n["stargazerCount"] for n in u["repositories"]["nodes"]),
        "followers": u["followers"]["totalCount"],
    }


def sample():
    """Approximation of the real graph (Oct→Sep) for offline rendering."""
    rows = [
        "0000000", "0000000", "0000000", "0000010", "0000000", "0000000", "0000000", "0000100",
        "0000000", "0000000", "0000000", "0000000", "0000000", "0100000", "0000000", "0000000",
        "0000010", "0001000", "0000000", "0000000", "0000000", "0001000", "0000000", "0000000",
        "0000000", "0000000", "0001000", "0000001", "0000000", "0100000", "0100100", "0000000",
        "0011110", "0122221", "0001321", "0001311", "0000112", "0100320", "0100120", "0100120",
        "0000001", "0001101", "0020111", "0100011", "0011000", "0000000", "0011211", "0112230",
        "0011000", "0122222", "0011231", "0110101",
    ]
    today = dt.date.today()
    start = today - dt.timedelta(days=7 * len(rows) - 1)
    weeks, total = [], 0
    for wi, r in enumerate(rows):
        week = []
        for di, c in enumerate(r):
            lvl = int(c)
            cnt = [0, 1, 3, 6, 10][lvl]
            total += cnt
            week.append({"date": (start + dt.timedelta(days=wi * 7 + di)).isoformat(),
                         "count": cnt, "level": lvl})
        weeks.append(week)
    return {"weeks": weeks, "total": total, "stars": 15, "followers": 16}


def streaks(weeks):
    days = [d for w in weeks for d in w]
    days.sort(key=lambda d: d["date"])
    # current streak: count back from today (or yesterday if today is empty)
    cur, i = 0, len(days) - 1
    if days and days[-1]["count"] == 0:
        i -= 1
    while i >= 0 and days[i]["count"] > 0:
        cur += 1
        i -= 1
    longest = run = 0
    for d in days:
        run = run + 1 if d["count"] > 0 else 0
        longest = max(longest, run)
    return cur, longest


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def render(data):
    W, H = 300, 620
    weeks = data["weeks"][-52:]
    cur, longest = streaks(weeks)
    today = dt.date.today().strftime("%d %b %Y")

    o = []
    o.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="GitHub activity for {USER}">')
    o.append("""<style>
  text{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif;fill:#e6edf3}
  .muted{fill:#8b949e}.b{font-weight:600}.cap{fill:#8b949e;font-size:9px;letter-spacing:.6px}
</style>""")
    # device body + screen
    o.append(f'<rect x="0" y="0" width="{W}" height="{H}" rx="40" fill="#2a2f36"/>')
    o.append(f'<rect x="6" y="6" width="{W-12}" height="{H-12}" rx="34" fill="#000"/>')
    # status bar + dynamic island
    o.append('<text x="26" y="34" font-size="12" class="b">9:41</text>')
    o.append(f'<rect x="{W/2-46}" y="18" width="92" height="26" rx="13" fill="#0d1117"/>')
    o.append(f'<circle cx="{W/2-30}" cy="31" r="3" fill="#3fb950"/>')
    o.append(f'<text x="{W/2-22}" y="35" font-size="10" fill="#3fb950">streak {cur}d</text>')
    o.append(f'<text x="{W-26}" y="34" font-size="11" text-anchor="end" class="b">●●● ▲</text>')

    y = 58
    # search field
    o.append(f'<rect x="20" y="{y}" width="{W-40}" height="36" rx="12" fill="#161b22" stroke="#30363d"/>')
    o.append(f'<circle cx="38" cy="{y+18}" r="5.5" fill="none" stroke="#8b949e" stroke-width="2"/>')
    o.append(f'<line x1="42.5" y1="{y+22.5}" x2="46" y2="{y+26}" stroke="#8b949e" stroke-width="2" stroke-linecap="round"/>')
    o.append(f'<text x="56" y="{y+23}" font-size="14">prajwal</text>')
    o.append(f'<rect x="111" y="{y+10}" width="2" height="16" fill="#4493f8"/>')
    y += 52

    # top hit
    o.append(f'<text x="24" y="{y}" class="cap">TOP HIT</text>'); y += 8
    o.append(f'<rect x="20" y="{y}" width="{W-40}" height="60" rx="16" fill="#161b22" stroke="#30363d"/>')
    o.append(f'<circle cx="52" cy="{y+30}" r="20" fill="#21262d" stroke="#30363d"/>')
    o.append(f'<text x="52" y="{y+35}" font-size="14" text-anchor="middle" class="b muted">PS</text>')
    o.append(f'<text x="84" y="{y+27}" font-size="13" class="b">Prajwal Sanap</text>')
    o.append(f'<text x="84" y="{y+43}" font-size="11" class="muted">iOS Engineer · rtCamp</text>')
    y += 74

    # contributions
    o.append(f'<text x="24" y="{y}" class="cap">GITHUB · CONTRIBUTIONS, LAST YEAR</text>'); y += 8
    n = len(weeks)
    gap = 1.0
    gx, inner = 24, W - 48
    cell = (inner - gap * (n - 1)) / n
    grid_h = 7 * cell + 6 * gap
    card_h = 10 + grid_h + 26
    o.append(f'<rect x="16" y="{y}" width="{W-32}" height="{card_h:.0f}" rx="16" fill="#161b22" stroke="#30363d"/>')
    gy = y + 10
    for wi, w in enumerate(weeks):
        for di, d in enumerate(w):
            x = gx + wi * (cell + gap)
            yy = gy + di * (cell + gap)
            o.append(f'<rect x="{x:.2f}" y="{yy:.2f}" width="{cell:.2f}" height="{cell:.2f}" rx="0.8" fill="{LEVELS[d["level"]]}"><title>{d["date"]}: {d["count"]}</title></rect>')
    ty = gy + grid_h + 17
    o.append(f'<text x="24" y="{ty:.0f}" font-size="10" class="muted">{data["total"]:,} contributions in the last year</text>')
    first, last = weeks[0][0]["date"], weeks[-1][-1]["date"]
    o.append(f'<text x="{W-24}" y="{ty:.0f}" font-size="9" text-anchor="end" class="muted">{first[:7]} → {last[:7]}</text>')
    y += int(card_h) + 14

    # applications
    o.append(f'<text x="24" y="{y}" class="cap">APPLICATIONS</text>'); y += 8
    row = 44
    o.append(f'<rect x="20" y="{y}" width="{W-40}" height="{row*len(APPS)}" rx="16" fill="#161b22" stroke="#30363d"/>')
    for i, (name, sub, color) in enumerate(APPS):
        ry = y + i * row
        if i:
            o.append(f'<line x1="20" y1="{ry}" x2="{W-20}" y2="{ry}" stroke="#30363d"/>')
        o.append(f'<rect x="32" y="{ry+8}" width="28" height="28" rx="7" fill="{color}"/>')
        o.append(f'<text x="70" y="{ry+20}" font-size="12" class="b">{esc(name)}</text>')
        o.append(f'<text x="70" y="{ry+34}" font-size="10" class="muted">{esc(sub)}</text>')
    y += row * len(APPS) + 14

    # siri suggestions: streak + stats
    o.append(f'<text x="24" y="{y}" class="cap">SIRI SUGGESTIONS</text>'); y += 8
    def days(n):
        return f"{n} day" if n == 1 else f"{n} days"
    rows = [("Current streak", days(cur)), ("Longest streak", days(longest)),
            ("Stars · Followers", f"{data['stars']} · {data['followers']}")]
    rh = 30
    o.append(f'<rect x="20" y="{y}" width="{W-40}" height="{rh*len(rows)}" rx="16" fill="#161b22" stroke="#30363d"/>')
    for i, (k, v) in enumerate(rows):
        ry = y + i * rh
        if i:
            o.append(f'<line x1="20" y1="{ry}" x2="{W-20}" y2="{ry}" stroke="#30363d"/>')
        o.append(f'<text x="32" y="{ry+19}" font-size="12">{esc(k)}</text>')
        o.append(f'<text x="{W-32}" y="{ry+19}" font-size="12" text-anchor="end" class="b">{esc(v)}</text>')
    y += rh * len(rows) + 16
    o.append(f'<text x="{W/2}" y="{y}" font-size="9" text-anchor="middle" class="muted">rebuilt nightly by GitHub Actions · {today}</text>')

    # keyboard hint row
    keys = "qwertyuiop"
    kw = (W - 40 - 9 * 4) / 10
    ky = H - 56
    for i, k in enumerate(keys):
        kx = 20 + i * (kw + 4)
        o.append(f'<rect x="{kx:.1f}" y="{ky}" width="{kw:.1f}" height="30" rx="5" fill="#30363d"/>')
        o.append(f'<text x="{kx+kw/2:.1f}" y="{ky+19}" font-size="11" text-anchor="middle">{k}</text>')
    o.append(f'<rect x="{W/2-55}" y="{H-18}" width="110" height="5" rx="3" fill="#c9d1d9"/>')
    o.append("</svg>")
    return "\n".join(o)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", action="store_true", help="render with built-in sample data")
    args = ap.parse_args()
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if args.sample or not token:
        if not args.sample:
            print("no GITHUB_TOKEN; rendering sample data", file=sys.stderr)
        data = sample()
    else:
        data = fetch_live(token)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(render(data))
    print(f"wrote {OUT}: {data['total']} contributions, {data['stars']} stars")


if __name__ == "__main__":
    main()
