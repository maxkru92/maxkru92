#!/usr/bin/env python3
"""KC stats: GitHub GraphQL contributionsCollection -> flat SVG cards (no third-party services)."""
import json, os, re, sys, urllib.request, datetime as dt
from pathlib import Path

LOGIN = os.environ.get("KC_LOGIN", "maxkru92")
TOKEN = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
ROOT = Path(__file__).resolve().parent.parent
C = dict(bg="#04080c", panel="#0a1218", border="#16242e", text="#c8d6dc", muted="#8199a6", cyan="#00e5ff", gold="#d4af37")
FONT = "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"

def gql(q, v):
    req = urllib.request.Request("https://api.github.com/graphql", json.dumps({"query": q, "variables": v}).encode(),
                                 {"Authorization": f"bearer {TOKEN}", "Content-Type": "application/json", "User-Agent": "kc-stats"})
    d = json.load(urllib.request.urlopen(req))
    if "errors" in d: sys.exit(f"GraphQL error: {d['errors']}")
    return d["data"]

Q_CAL = """query($l:String!){user(login:$l){followers{totalCount}
 contributionsCollection{totalCommitContributions totalPullRequestContributions totalIssueContributions
  restrictedContributionsCount contributionCalendar{totalContributions weeks{contributionDays{date contributionCount}}}}}}"""
Q_REPO = """query($l:String!,$c:String){user(login:$l){repositories(first:100,after:$c,ownerAffiliations:OWNER,isFork:false){
 totalCount pageInfo{hasNextPage endCursor} nodes{stargazerCount languages(first:20,orderBy:{field:SIZE,direction:DESC}){edges{size node{name}}}}}}}"""

def fetch():
    u = gql(Q_CAL, {"l": LOGIN})["user"]; cc = u["contributionsCollection"]
    days = [d for w in cc["contributionCalendar"]["weeks"] for d in w["contributionDays"]]
    weeks = [[d["contributionCount"] for d in w["contributionDays"]] for w in cc["contributionCalendar"]["weeks"]]
    cur = 0
    for i, d in enumerate(reversed(days)):
        if d["contributionCount"] > 0: cur += 1
        elif i == 0: continue  # today may still be empty
        else: break
    lon = run = 0
    for d in days:
        run = run + 1 if d["contributionCount"] else 0; lon = max(lon, run)
    stars = 0; langs = {}; cursor = None; total_repos = 0
    while True:
        r = gql(Q_REPO, {"l": LOGIN, "c": cursor})["user"]["repositories"]; total_repos = r["totalCount"]
        for n in r["nodes"]:
            stars += n["stargazerCount"]
            for e in n["languages"]["edges"]: langs[e["node"]["name"]] = langs.get(e["node"]["name"], 0) + e["size"]
        if not r["pageInfo"]["hasNextPage"]: break
        cursor = r["pageInfo"]["endCursor"]
    tot = sum(langs.values()) or 1
    top = sorted(((k, 100 * v / tot) for k, v in langs.items()), key=lambda x: -x[1])[:6]
    return dict(asOf=dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d"), total=cc["contributionCalendar"]["totalContributions"],
                commits=cc["totalCommitContributions"], prs=cc["totalPullRequestContributions"], private=cc["restrictedContributionsCount"],
                currentStreak=cur, longestStreak=lon, activeDays=sum(1 for d in days if d["contributionCount"]),
                stars=stars, ownRepos=total_repos, followers=u["followers"]["totalCount"], langs=top, weeks=weeks,
                start=days[0]["date"], end=days[-1]["date"])

def esc(s): return str(s).replace("&", "&amp;").replace("<", "&lt;")
def fmt(n): return f"{n:,}".replace(",", ".")
W = 880
def frame(h, title, body, s):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{h}" viewBox="0 0 {W} {h}" font-family="{FONT}">
<rect width="{W}" height="{h}" fill="{C['bg']}"/><rect x="0.5" y="0.5" width="{W-1}" height="{h-1}" rx="6" fill="{C['panel']}" stroke="{C['border']}"/>
<rect x="28" y="28" width="6" height="6" fill="{C['cyan']}"/>
<text x="44" y="35" font-size="11" letter-spacing="2" fill="{C['muted']}">KRUPP CAPITAL · {esc(title)}</text>
<text x="{W-28}" y="35" font-size="11" letter-spacing="1" fill="{C['muted']}" text-anchor="end">@{LOGIN}</text>
<line x1="28" y1="50" x2="{W-28}" y2="50" stroke="{C['border']}"/>
{body}
<line x1="28" y1="{h-40}" x2="{W-28}" y2="{h-40}" stroke="{C['border']}"/>
<text x="28" y="{h-20}" font-size="10" fill="{C['muted']}">Quelle: GitHub GraphQL contributionsCollection · Stand {s['asOf']} UTC</text>
</svg>'''

def card_stats(s):
    items = [("CONTRIBUTIONS · 12M", fmt(s["total"]), C["cyan"]), ("PUBLIC COMMITS", fmt(s["commits"]), C["text"]),
             ("AKTUELLE STREAK", f"{s['currentStreak']} T", C["gold"]), ("LÄNGSTE STREAK", f"{s['longestStreak']} T", C["text"]),
             ("AKTIVE TAGE", fmt(s["activeDays"]), C["text"]), ("STARS", fmt(s["stars"]), C["text"]),
             ("REPOS", fmt(s["ownRepos"]), C["text"]), ("PRIVAT · 12M", fmt(s["private"]), C["muted"])]
    cw = (W - 56) / 4; b = []
    for i, (k, v, col) in enumerate(items):
        x = 28 + (i % 4) * cw; y = 70 + (i // 4) * 92
        if i % 4: b.append(f'<line x1="{x:.1f}" y1="{y}" x2="{x:.1f}" y2="{y+72}" stroke="{C["border"]}"/>')
        px = x + (0 if i % 4 == 0 else 18)
        b.append(f'<text x="{px:.1f}" y="{y+18}" font-size="10" letter-spacing="1.5" fill="{C["muted"]}">{k}</text>')
        b.append(f'<text x="{px:.1f}" y="{y+56}" font-size="30" font-weight="700" letter-spacing="-0.3" fill="{col}" style="font-variant-numeric:tabular-nums">{v}</text>')
    b.append(f'<line x1="28" y1="156" x2="{W-28}" y2="156" stroke="{C["border"]}"/>')
    return frame(300, "TRACK RECORD", "\n".join(b), s)

def card_langs(s):
    b = []; y = 78
    for i, (n, p) in enumerate(s["langs"]):
        col = C["cyan"] if i == 0 else (C["gold"] if i == 1 else C["text"])
        b.append(f'<text x="28" y="{y+4}" font-size="12" fill="{C["text"]}">{esc(n)}</text>')
        b.append(f'<line x1="180" y1="{y}" x2="{W-110}" y2="{y}" stroke="{C["border"]}" stroke-width="2"/>')
        b.append(f'<line x1="180" y1="{y}" x2="{180+(W-290)*p/100:.1f}" y2="{y}" stroke="{col}" stroke-width="2"/>')
        b.append(f'<text x="{W-28}" y="{y+4}" font-size="12" fill="{C["muted"]}" text-anchor="end" style="font-variant-numeric:tabular-nums">{p:.1f} %</text>')
        y += 30
    return frame(y + 46, "SPRACHEN · BYTES, EIGENE REPOS", "\n".join(b), s)

def card_cal(s):
    cell, gap = 12, 3; x0, y0 = 62, 84
    mx = max([c for w in s["weeks"] for c in w] + [1])
    shades = [C["border"], "#0b3a44", "#0a6573", "#05a3b8", C["cyan"]]
    b = []
    for i, d in enumerate(["Mo", "Mi", "Fr"]):
        b.append(f'<text x="28" y="{y0+(2*i+1)*(cell+gap)+10}" font-size="9" fill="{C["muted"]}">{d}</text>')
    start = dt.date.fromisoformat(s["start"]); lastm = None
    for wi, w in enumerate(s["weeks"]):
        wd = start + dt.timedelta(days=7 * wi - (start.isoweekday() % 7))
        m = (start + dt.timedelta(days=7 * wi)).month
        if m != lastm and 0 < wi < len(s["weeks"]) - 2:
            b.append(f'<text x="{x0+wi*(cell+gap)}" y="{y0-10}" font-size="9" fill="{C["muted"]}">{["Jan","Feb","Mär","Apr","Mai","Jun","Jul","Aug","Sep","Okt","Nov","Dez"][m-1]}</text>'); lastm = m
        for di, c in enumerate(w):
            lvl = 0 if c == 0 else min(4, 1 + int(3 * (c / mx) ** 0.5))
            b.append(f'<rect x="{x0+wi*(cell+gap)}" y="{y0+di*(cell+gap)}" width="{cell}" height="{cell}" rx="1.5" fill="{shades[lvl]}"><title>{c}</title></rect>')
    ly = y0 + 7 * (cell + gap) + 18
    b.append(f'<text x="28" y="{ly+9}" font-size="10" fill="{C["muted"]}">{fmt(s["total"])} Contributions · {s["start"]} → {s["end"]}</text>')
    for i, sh in enumerate(shades):
        b.append(f'<rect x="{W-28-5*(cell+gap)+i*(cell+gap)}" y="{ly}" width="{cell}" height="{cell}" rx="1.5" fill="{sh}"/>')
    return frame(ly + 70, "CONTRIBUTION-KALENDER · 12M", "\n".join(b), s)

def main():
    if not TOKEN: sys.exit("GH_TOKEN fehlt")
    s = fetch(); (ROOT / "assets").mkdir(exist_ok=True)
    for name, fn in [("kc-stats.svg", card_stats), ("kc-languages.svg", card_langs), ("kc-calendar.svg", card_cal)]:
        (ROOT / "assets" / name).write_text(fn(s), encoding="utf-8")
    rd = ROOT / "README.md"; t = rd.read_text(encoding="utf-8")
    line = f"<!-- KC-STATS:START -->\n<sub>Stand {s['asOf']} UTC · automatisch täglich aktualisiert via GitHub GraphQL contributionsCollection</sub>\n<!-- KC-STATS:END -->"
    t2 = re.sub(r"<!-- KC-STATS:START -->.*?<!-- KC-STATS:END -->", line, t, flags=re.S)
    if t2 != t: rd.write_text(t2, encoding="utf-8")
    print(json.dumps({k: v for k, v in s.items() if k != "weeks"}))

if __name__ == "__main__": main()
