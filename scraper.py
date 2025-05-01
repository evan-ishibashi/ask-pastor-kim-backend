# backend/scraper.py

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import time
import json
import re
from collections import deque

BASE_URL = "https://lighthousesouthbay.org"
visited = set()

def is_valid_url(url):
    parsed = urlparse(url)
    return parsed.netloc == "lighthousesouthbay.org" or parsed.netloc == ""

def get_links(soup, base_url):
    links = set()
    for a_tag in soup.find_all("a", href=True):
        full_url = urljoin(base_url, a_tag["href"])
        if is_valid_url(full_url) and full_url.startswith(BASE_URL):

            # Remove all image file URLs
            if re.search(r"wp-content/uploads", full_url):
                print("wp-content ran")
                continue
            if re.match(r"^\S*\.(gif|png|jpg|jpeg|mp3)$", full_url):
                print(".jpg ran")
                continue
            links.add(full_url.split("#")[0])  # remove #fragment
    return links

def clean_text(soup):

    # remove the following tags from text
    for tag in soup(["nav", "footer", "script", "style", "header"]):
        tag.decompose()

    # Remove the full header on site
    header = soup.find("div", attrs={"data-elementor-type": "header"})
    if header:
        header.decompose()
    text = soup.get_text(separator="\n", strip=True)
    return text

def crawl(url, max_pages=10):
    to_visit = deque([url])

    with open("lighthouse_pages.json", "w", encoding="utf-8") as f:
        f.write("[\n")
        first = True

        while to_visit and len(visited) < max_pages:
            current = to_visit.popleft()
            if current in visited:
                continue
            try:
                print(f"Crawling: {current}")
                res = requests.get(current, timeout=10)
                if res.status_code != 200:
                    continue
                soup = BeautifulSoup(res.text, "html.parser")
                text = clean_text(soup)

                page_data = {
                    "url": current,
                    "text": text
                }

                if not first:
                    f.write(",\n")
                json.dump(page_data, f, ensure_ascii=False, indent=2)
                first = False

                links = get_links(soup, current)
                to_visit.extend(links - visited)
                visited.add(current)
                time.sleep(0.5)
            except Exception as e:
                print(f"Error crawling {current}: {e}")

        f.write("\n]\n")

if __name__ == "__main__":
    crawl(BASE_URL, max_pages=100)