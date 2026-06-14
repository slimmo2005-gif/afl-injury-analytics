import re
import requests
from bs4 import BeautifulSoup

pages = []
for p in range(1, 12):
    r = requests.get(
        f"https://sanfl.com.au/inside-sanfl/resources/page/{p}/?s=stats",
        timeout=30,
        headers={"User-Agent": "Mozilla/5.0"},
    )
    if r.status_code != 200:
        break
    pages.append(r.text)

text = "\n".join(pages)
pdfs = re.findall(r'href="(https://sanfl-content[^"]+\.pdf)"', text)
titles = re.findall(r'>([^<]*2024[^<]*SANFL[^<]*Stats[^<]*)<', text, re.I)
print("2024 pdf count", sum(1 for u in pdfs if "2024" in u or "2024" in text))
for u in pdfs:
    if "2024" in u or "2024" in u.lower():
        print(u)

# broader: mens post round pdfs 2024
for u in pdfs:
    if "Mens-Post" in u or "mens" in u.lower():
        print("mens", u[:120])

print("sample titles", titles[:10])
