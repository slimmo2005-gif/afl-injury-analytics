import re
import requests

r = requests.get(
    "https://www.wheeloratings.com/afl_stats.html",
    timeout=30,
    headers={"User-Agent": "Mozilla/5.0"},
)
print("status", r.status_code, "len", len(r.text))
apis = set(re.findall(r'["\']([^"\']*(?:api|data|stats)[^"\']*)["\']', r.text, re.I))
for a in sorted(apis)[:30]:
    print(" ", a)
scripts = re.findall(r'src="([^"]+\.js)"', r.text)
print("scripts", scripts)

# try common paths
for path in [
    "/data/afl_stats.json",
    "/api/afl_stats",
    "/afl_stats_data.json",
    "/stats/data",
]:
    u = "https://www.wheeloratings.com" + path
    try:
        rr = requests.get(u, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        print(path, rr.status_code, rr.headers.get("content-type", ""), rr.text[:120])
    except Exception as e:
        print(path, e)
