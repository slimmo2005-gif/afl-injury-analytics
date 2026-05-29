import re
import requests

r = requests.get(
    "https://www.afl.com.au/vfl/fixture",
    timeout=30,
    headers={"User-Agent": "Mozilla/5.0"},
)
text = r.text
for pattern in [
    r"https://[^\"']+\.json[^\"']*",
    r"competitionId[\"']?\s*:\s*\d+",
    r"VFL",
    r"matchId[\"']?\s*:\s*\d+",
]:
    found = re.findall(pattern, text[:200000])
    print(pattern, len(found), found[:5])
