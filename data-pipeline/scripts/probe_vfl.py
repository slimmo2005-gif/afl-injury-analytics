import re
import requests
from bs4 import BeautifulSoup

r = requests.get("https://www.vfl.com.au/fixture", timeout=30, headers={"User-Agent": "Mozilla/5.0"})
soup = BeautifulSoup(r.text, "html.parser")
links = {a["href"] for a in soup.find_all("a", href=True) if "match" in a["href"].lower()}
print("match links", list(links)[:15])
apis = re.findall(r"https://[^\s\"']+", r.text)
print("urls with json", [u for u in apis if "json" in u.lower()][:10])
