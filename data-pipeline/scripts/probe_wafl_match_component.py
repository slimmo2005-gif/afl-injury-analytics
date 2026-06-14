import re
import requests

chunk = requests.get("https://wafl.com.au/_nuxt/DKaABlWn.js", timeout=30).text
print("len", len(chunk))
for m in re.finditer(r'https?://[^"\']+|/public/[^"\']+|"[a-z-]+/[a-z-{}]+"', chunk):
    s = m.group(0)
    if any(x in s.lower() for x in ("sportix", "match", "stat", "player", "fixture", "public")):
        print(s[:150])

# also stats table component
chunk2 = requests.get("https://wafl.com.au/_nuxt/D7412eUt.js", timeout=30).text
print("\nStatsTable chunk")
for m in re.finditer(r'https?://[^"\']+|get\("[^"]+"\)|post\("[^"]+"\)|`[^`]*public[^`]*`', chunk2):
    print(m.group(0)[:150])
