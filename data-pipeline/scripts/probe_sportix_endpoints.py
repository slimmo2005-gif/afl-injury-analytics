import re
import requests

KEY = "290|yQfFH5WycjbEb8eUtVtTCXZt2aWOxFpDjUYEdxgQ9326de46"
H = {"Authorization": f"Bearer {KEY}", "Accept": "application/json"}

# grep all nuxt chunks for public/ endpoints
chunks = [
    "BtROYF5o.js", "Cwf74cVF.js", "DfJL1DE_.js", "D7412eUt.js",
    "f5f-uFW3.js", "DplOWySu.js", "BCx48o62.js", "6gYeLWMS.js",
]
endpoints = set()
for c in chunks:
    t = requests.get(f"https://wafl.com.au/_nuxt/{c}", timeout=30).text
    for m in re.finditer(r'["`]([a-zA-Z0-9_/-]+)["`]', t):
        s = m.group(1)
        if s.startswith(("matches", "fixtures", "competitions", "clubs", "players", "seasons")):
            endpoints.add(s)
    for m in re.finditer(r'\$\{[^}]+\}/([a-zA-Z0-9_/${}-]+)', t):
        endpoints.add(m.group(0)[:80])

print("endpoint strings", sorted(endpoints))

# try common sportix patterns
API = "https://api.sportix.cloud/public"
tests = [
    ("GET", "/matches", {"season": 2024}),
    ("GET", "/matches", {"filter[season]": 2024}),
    ("GET", "/matches", {"filters[season]": 2024}),
    ("GET", "/matches", {"filters[competition]": "league"}),
    ("GET", "/clubs", None),
    ("GET", "/players", {"filters[club]": "peel-thunder"}),
    ("GET", "/players", {"filters[club]": "Peel Thunder"}),
]
for method, ep, params in tests:
    r = requests.get(API + ep, headers=H, params=params, timeout=20)
    print(ep, params, r.status_code, r.text[:250].replace("\n", " "))
