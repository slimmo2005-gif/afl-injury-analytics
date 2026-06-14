import re
import requests

requests.packages.urllib3.disable_warnings()

for host in ("wafl", "sanfl", "vfl"):
    url = f"https://{host}.aflmstats.com/season/2024"
    try:
        r = requests.get(
            url,
            timeout=30,
            verify=False,
            headers={"User-Agent": "afl-injury-analytics/0.3"},
        )
        title = re.search(r"<title>([^<]+)</title>", r.text)
        slugs = re.findall(rf"/game/2024-\d+-[a-z0-9-]+", r.text)
        print(host, r.status_code, title.group(1) if title else "?", "games", len(set(slugs)))
        if slugs:
            print("  sample", slugs[:3])
    except Exception as e:
        print(host, "ERR", e)
