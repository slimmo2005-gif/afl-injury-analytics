import json
import re
import requests

url = "https://www.afl.com.au/vfl/fixture"
r = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
print("status", r.status_code)

m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.+?)</script>', r.text)
if m:
    data = json.loads(m.group(1))
    print("keys", data.keys())
    props = data.get("props", {}).get("pageProps", {})
    print("pageProps keys", list(props.keys())[:20])
    # dump small excerpt
    text = json.dumps(props)[:3000]
    print(text)
else:
    print("no next data")
    print(r.text[:500])
