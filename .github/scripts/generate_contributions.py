#!/usr/bin/env python3
"""Generates assets/contrib-heatmap.svg and assets/contrib-activity.svg
straight from the GitHub GraphQL API. No third-party image service involved.

Usage:
  GITHUB_TOKEN=... python generate_contributions.py MokioGeki-ID
  python generate_contributions.py MokioGeki-ID --placeholder   # empty state, no network
  python generate_contributions.py MokioGeki-ID --demo          # fake data, for local preview
"""
import datetime as dt
import json
import math
import os
import random
import sys
import urllib.request
from xml.sax.saxutils import escape

ASSETS = os.path.join(os.path.dirname(__file__), "..", "..", "assets")
FONT = "'Segoe UI',system-ui,-apple-system,'Helvetica Neue',Arial,sans-serif"
BG_TOP, BG_BOT, LINE = "#0d1a33", "#0a1224", "#1e3a5f"
TEXT, SOFT, MUTED = "#e2e8f0", "#cbd5e1", "#94a3b8"
ICE, AMBER = "#7dd3fc", "#fbbf24"
LEVELS = ["#111d36", "#1b4a78", "#2b7bb0", "#5bb8e8", "#a5e3ff"]
MONTHS = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]

QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount weekday } }
      }
    }
  }
}"""


def fetch(login, token):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": login}}).encode(),
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json",
                 "User-Agent": "profile-contrib-svg"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        payload = json.load(r)
    if "errors" in payload:
        raise SystemExit(f"GitHub API error: {payload['errors']}")
    cal = payload["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    days = [d for w in cal["weeks"] for d in w["contributionDays"]]
    return cal["totalContributions"], days


def demo_data():
    rnd = random.Random(7)
    today = dt.date.today()
    start = today - dt.timedelta(days=364)
    start -= dt.timedelta(days=(start.weekday() + 1) % 7)  # back to Sunday
    days, d = [], start
    while d <= today:
        n = rnd.choice([0, 0, 0, 1, 2, 3, 5, 8]) if d.weekday() < 5 else rnd.choice([0, 0, 0, 1, 2])
        days.append({"date": d.isoformat(), "contributionCount": n, "weekday": (d.weekday() + 1) % 7})
        d += dt.timedelta(days=1)
    return sum(x["contributionCount"] for x in days), days


def placeholder_data():
    today = dt.date.today()
    start = today - dt.timedelta(days=364)
    start -= dt.timedelta(days=(start.weekday() + 1) % 7)
    days, d = [], start
    while d <= today:
        days.append({"date": d.isoformat(), "contributionCount": 0, "weekday": (d.weekday() + 1) % 7})
        d += dt.timedelta(days=1)
    return 0, days


def text(x, y, s, size, fill, weight=400, anchor="start"):
    return (f'<text x="{x}" y="{y}" font-family="{FONT}" font-size="{size}" font-weight="{weight}" '
            f'fill="{fill}" text-anchor="{anchor}">{escape(str(s))}</text>\n')


def frame(w, h, label, uid):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" '
            f'aria-label="{escape(label)}">\n<title>{escape(label)}</title>\n'
            f'<defs><linearGradient id="{uid}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{BG_TOP}"/>'
            f'<stop offset="1" stop-color="{BG_BOT}"/></linearGradient>'
            f'<linearGradient id="{uid}a" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{ICE}" stop-opacity="0.38"/>'
            f'<stop offset="1" stop-color="{ICE}" stop-opacity="0"/></linearGradient></defs>\n'
            f'<rect x="0.5" y="0.5" width="{w-1}" height="{h-1}" rx="16" fill="url(#{uid})" stroke="{LINE}"/>\n')


def level(n, peak):
    if n <= 0 or peak <= 0:
        return 0
    return max(1, min(4, math.ceil(n / peak * 4)))


def heatmap(total, days, empty=False):
    w, h = 1000, 232
    cell, gap = 13, 3
    step = cell + gap
    weeks = []
    for d in days:  # group into Sunday-first weeks
        if d["weekday"] == 0 or not weeks:
            weeks.append([])
        weeks[-1].append(d)
    weeks = weeks[-53:]
    peak = max((d["contributionCount"] for d in days), default=0)
    x0, y0 = 104, 86
    label = (f"Peta kontribusi setahun terakhir: {total} kontribusi." if not empty
             else "Peta kontribusi setahun terakhir. Menunggu pembaruan pertama dari GitHub Actions.")
    s = frame(w, h, label, "hm")
    s += text(44, 52, "Kontribusi setahun terakhir", 17, "#f1f5f9", 700)
    if empty:
        s += text(956, 52, "Menunggu pembaruan pertama dari GitHub Actions", 13, MUTED, 500, "end")
    else:
        s += text(956, 52, f"{total:,} kontribusi".replace(",", "."), 15, ICE, 600, "end")
    last_month = None
    for i, wk in enumerate(weeks):
        m = int(wk[0]["date"][5:7])
        if m != last_month and (i == 0 or i < len(weeks) - 2):
            if i == 0 or int(wk[0]["date"][8:10]) <= 14 or True:
                s += text(x0 + i * step, y0 - 12, MONTHS[m - 1], 12, MUTED, 500)
            last_month = m
    for r, name in ((1, "Sen"), (3, "Rab"), (5, "Jum")):
        s += text(44, y0 + r * step + cell - 2, name, 11.5, MUTED, 500)
    best = max(days, key=lambda d: d["contributionCount"], default=None)
    for i, wk in enumerate(weeks):
        for d in wk:
            n = d["contributionCount"]
            color = LEVELS[level(n, peak)]
            if best and not empty and n == peak and d["date"] == best["date"] and peak > 0:
                color = AMBER
            s += (f'<rect x="{x0 + i*step}" y="{y0 + d["weekday"]*step}" width="{cell}" height="{cell}" rx="3" '
                  f'fill="{color}"><title>{d["date"]}: {n} kontribusi</title></rect>\n')
    ly = h - 30
    s += text(x0, ly + 10, "Sedikit", 12, MUTED)
    for k, c in enumerate(LEVELS):
        s += f'<rect x="{x0 + 52 + k*18}" y="{ly}" width="13" height="13" rx="3" fill="{c}"/>\n'
    s += text(x0 + 52 + 5*18 + 6, ly + 10, "Banyak", 12, MUTED)
    if not empty and peak > 0:
        s += f'<rect x="{x0 + 330}" y="{ly}" width="13" height="13" rx="3" fill="{AMBER}"/>\n'
        s += text(x0 + 350, ly + 10, f"Hari tersibuk: {peak} kontribusi", 12, MUTED)
    return s + "</svg>\n"


def activity(days, empty=False):
    w, h = 1000, 280
    recent = days[-30:]
    counts = [d["contributionCount"] for d in recent]
    total = sum(counts)
    ymax = max(4, max(counts, default=0))
    ymax = int(math.ceil(ymax / 4) * 4)
    px0, px1, py0, py1 = 76, 956, 86, 222
    label = (f"Aktivitas 30 hari terakhir: {total} kontribusi." if not empty
             else "Aktivitas 30 hari terakhir. Menunggu pembaruan pertama dari GitHub Actions.")
    s = frame(w, h, label, "ac")
    s += text(44, 52, "Aktivitas 30 hari terakhir", 17, "#f1f5f9", 700)
    if empty:
        s += text(956, 52, "Menunggu pembaruan pertama dari GitHub Actions", 13, MUTED, 500, "end")
    else:
        s += text(956, 52, f"{total} kontribusi", 15, ICE, 600, "end")
    for k in range(5):
        y = py1 - (py1 - py0) * k / 4
        s += f'<line x1="{px0}" y1="{y:.1f}" x2="{px1}" y2="{y:.1f}" stroke="#14264a"/>\n'
        s += text(px0 - 12, f"{y + 4:.1f}", f"{ymax * k // 4}", 11.5, MUTED, 400, "end")
    n = len(recent)
    xs = [px0 + (px1 - px0) * i / max(1, n - 1) for i in range(n)]
    ys = [py1 - (py1 - py0) * c / ymax for c in counts]
    if not empty and n > 1:
        pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in zip(xs, ys))
        s += f'<polygon points="{px0},{py1} {pts} {px1},{py1}" fill="url(#aca)"/>\n'
        s += f'<polyline points="{pts}" fill="none" stroke="{AMBER}" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round"/>\n'
        for x, y, c, d in zip(xs, ys, counts, recent):
            if c > 0:
                s += (f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.6" fill="{BG_BOT}" stroke="{ICE}" stroke-width="2">'
                      f'<title>{d["date"]}: {c} kontribusi</title></circle>\n')
    for i in range(0, n, 5):
        d = dt.date.fromisoformat(recent[i]["date"])
        s += text(f"{xs[i]:.1f}", py1 + 24, f"{d.day} {MONTHS[d.month-1]}", 11.5, MUTED, 400, "middle")
    if n:
        d = dt.date.fromisoformat(recent[-1]["date"])
        s += text(f"{xs[-1]:.1f}", py1 + 24, f"{d.day} {MONTHS[d.month-1]}", 11.5, MUTED, 400, "end")
    return s + "</svg>\n"


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = {a for a in sys.argv[1:] if a.startswith("--")}
    login = args[0] if args else "MokioGeki-ID"
    if "--placeholder" in flags:
        total, days = placeholder_data()
    elif "--demo" in flags:
        total, days = demo_data()
    else:
        token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
        if not token:
            raise SystemExit("Set GITHUB_TOKEN (or use --placeholder / --demo).")
        total, days = fetch(login, token)
    empty = "--placeholder" in flags
    os.makedirs(ASSETS, exist_ok=True)
    out = os.environ.get("OUT_DIR", ASSETS)
    with open(os.path.join(out, "contrib-heatmap.svg"), "w", encoding="utf-8") as f:
        f.write(heatmap(total, days, empty))
    with open(os.path.join(out, "contrib-activity.svg"), "w", encoding="utf-8") as f:
        f.write(activity(days, empty))
    print(f"ok: {total} contributions, {len(days)} days")


if __name__ == "__main__":
    main()
