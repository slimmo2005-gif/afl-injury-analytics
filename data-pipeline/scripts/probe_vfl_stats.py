import re
import requests
from bs4 import BeautifulSoup

r = requests.get(
    "https://vfl.aflmstats.com/season/2024",
    timeout=30,
    headers={"User-Agent": "Mozilla/5.0"},
)
text = r.text
hrefs = re.findall(r'href="([^"]+)"', text)
print("hrefs sample", [h for h in hrefs if "match" in h.lower() or "game" in h.lower()][:15])
print("total hrefs", len(hrefs))

soup = BeautifulSoup(text, "html.parser")
# Match stats links might be last column
for tr in soup.find_all("tr"):
    cells = tr.find_all("td")
    if len(cells) >= 5 and cells[0].get_text(strip=True).isdigit() is False:
        last = cells[-1]
        a = last.find("a")
        if a and a.get("href"):
            print("row link", a["href"], [c.get_text(strip=True) for c in cells[:3]])
            url = a["href"]
            if url.startswith("/"):
                url = "https://vfl.aflmstats.com" + url
            m = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
            print("status", m.status_code)
            ms = BeautifulSoup(m.text, "html.parser")
            for table in ms.find_all("table")[:1]:
                for row in table.find_all("tr")[:6]:
                    print([c.get_text(" ", strip=True) for c in row.find_all(["td", "th"])])
            break
