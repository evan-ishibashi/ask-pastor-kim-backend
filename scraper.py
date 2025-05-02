import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import time
import json
import re
import os
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
            if re.search(r"wp-content/uploads", full_url):
                continue
            if re.match(r"^\S*\.(gif|png|jpg|jpeg|mp3)$", full_url):
                continue
            links.add(full_url.split("#")[0])
    return links

def clean_text(soup):
    for tag in soup(["footer", "script", "style", "header"]):
        tag.decompose()
    header = soup.find("div", attrs={"data-elementor-type": "header"})
    if header:
        header.decompose()
    return soup.get_text(separator="\n", strip=True)

def load_existing_data(filename):
    if not os.path.exists(filename):
        return [], set()
    with open(filename, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
            existing_urls = set(page["url"] for page in data)
            return data, existing_urls
        except Exception as e:
            print(f"Error loading existing data: {e}")
            return [], set()

def crawl(url):
    to_visit = deque([url])

    # Load existing pages if available
    try:
        with open("lighthouse_pages.json", "r", encoding="utf-8") as f:
            existing_data = json.load(f)
    except FileNotFoundError:
        existing_data = []

    visited_urls = set(page["url"] for page in existing_data)
    new_data = []

    while to_visit:
        current = to_visit.popleft()
        if current in visited or current in visited_urls:
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

            new_data.append(page_data)

            links = get_links(soup, current)
            to_visit.extend(links - visited - visited_urls)
            visited.add(current)
            time.sleep(0.5)
        except Exception as e:
            print(f"Error crawling {current}: {e}")

    # Save combined data
    with open("lighthouse_pages.json", "w", encoding="utf-8") as f:
        json.dump(existing_data + new_data, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Added {len(new_data)} new pages.")

if __name__ == "__main__":
    crawl(BASE_URL)
    crawl(BASE_URL + "/our-resources/")