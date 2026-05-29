import requests
from bs4 import BeautifulSoup

url = "https://vfl.aflmstats.com/game/2024-1-san-col"
r = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
soup = BeautifulSoup(r.text, "html.parser")
for h in soup.find_all(["h1", "h2", "h3", "h4"]):
    print("HEAD", h.name, h.get_text(strip=True))
for i, table in enumerate(soup.find_all("table")):
    prev = table.find_previous(["h2", "h3", "h4"])
    print("TABLE", i, "after", prev.get_text(strip=True) if prev else None)
    rows = table.find_all("tr")[:2]
    for row in rows:
        print(" ", [c.get_text(strip=True) for c in row.find_all(["td", "th"])])
