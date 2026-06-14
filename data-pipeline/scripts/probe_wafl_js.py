import re
import requests

js = requests.get("https://wafl.com.au/_nuxt/BtROYF5o.js", timeout=30).text
print("js len", len(js))
for term in ["sportix", "matches", "fixtures", "players", "statistics", "match-stats"]:
    print(term, js.lower().count(term.lower()))

# find url-like strings near sportix
idx = js.lower().find("sportix")
print("sportix context", js[max(0, idx - 100) : idx + 200] if idx >= 0 else "none")

paths = set(re.findall(r'["\'](/[a-zA-Z0-9_/-]{3,80})["\']', js))
interesting = sorted(p for p in paths if any(x in p.lower() for x in ("match", "player", "fixture", "stat", "club", "comp", "team")))
print("paths", interesting[:50])

# search all js chunks for graphql or api paths
for chunk in ["Cwf74cVF.js", "DfJL1DE_.js", "D7412eUt.js", "f5f-uFW3.js"]:
    t = requests.get(f"https://wafl.com.au/_nuxt/{chunk}", timeout=30).text
    if "sportix" in t.lower() or "match-stats" in t.lower():
        print("chunk", chunk, "has sportix")
        for m in re.finditer(r"/[a-z-]+(?:/[a-z-{}]+){1,4}", t):
            s = m.group(0)
            if any(x in s for x in ("match", "player", "stat", "fixture")):
                print(" ", s)
