import re
import requests

chunks = []
r = requests.get("https://wafl.com.au/match/league-peel-thunder-v-east-fremantle-round-1-2024", timeout=30)
for m in re.findall(r'/_nuxt/([A-Za-z0-9_-]+\.js)', r.text):
    chunks.append(m)
chunks = list(dict.fromkeys(chunks))[:25]
print("chunks", len(chunks))

calls = set()
for c in chunks:
    t = requests.get(f"https://wafl.com.au/_nuxt/{c}", timeout=30).text
    for m in re.finditer(r'fetch\(`([^`]+)`\)|fetch\("([^"]+)"\)|\.fetch\(`([^`]+)`\)', t):
        s = next(x for x in m.groups() if x)
        if "/" in s:
            calls.add(s)

print("fetch calls:")
for c in sorted(calls):
    print(" ", c)
