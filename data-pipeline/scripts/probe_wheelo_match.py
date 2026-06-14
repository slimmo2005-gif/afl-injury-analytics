import re
import requests

r = requests.get("https://www.wheeloratings.com/afl_match_stats.html", timeout=30)
m = re.search(r'const dataset = "([^"]+)"', r.text)
print("dataset", m.group(1) if m else None)
for script in re.findall(r'src="([^"]+)"', r.text):
    if "fetch" in script or "match" in script:
        print("script", script)

if m:
    ds = m.group(1)
    rr = requests.get(
        f"https://www.wheeloratings.com/src/afl_stats/{ds}/comps.json",
        timeout=30,
    )
    print("comps", rr.status_code)
    if rr.ok:
        import json

        print(json.dumps(rr.json(), indent=2)[:2500])
