import re
import requests

for url in [
    "https://www.afl.com.au/wafl/matches/6115",
    "https://www.afl.com.au/sanfl/matches/1",
    "https://www.afl.com.au/sanfl/matches/100",
]:
    r = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
    print(url, r.status_code, len(r.text))
    if r.ok:
        for pat in [r"__NEXT_DATA__", r"player", r"statistics", r"championdata", r"matchId"]:
            print(" ", pat, bool(re.search(pat, r.text, re.I)))

# search wafl match page for player names from known match
r = requests.get("https://www.afl.com.au/wafl/matches/6115", timeout=30, headers={"User-Agent": "Mozilla/5.0"})
if "Will Brodie" in r.text or "Colton" in r.text:
    print("found player names in afl.com wafl page")
