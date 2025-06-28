# generate_rss.py
import requests
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator
from datetime import datetime
import os

BASE_URL = "https://dime.jp/genre/"
RSS_OUTPUT_DIR = "rss"
RSS_OUTPUT_FILE = "dime.xml"

def fetch_articles():
    res = requests.get(BASE_URL)
    soup = BeautifulSoup(res.content, "html.parser")
    items = soup.select("div.catlist__item")

    articles = []
    for item in items[:10]:  # 最新10件のみ
        a_tag = item.find("a")
        url = a_tag["href"]
        title_tag = item.select_one("h3.catlist__title")
        date_tag = item.select_one("div.catlist__date")

        if not (url and title_tag and date_tag):
            continue

        title = title_tag.text.strip()
        date_str = date_tag.text.strip()
        try:
            pub_date = datetime.strptime(date_str, "%Y.%m.%d")
        except ValueError:
            pub_date = datetime.utcnow()

        articles.append({
            "title": title,
            "link": url,
            "pubDate": pub_date
        })

    return articles

def generate_rss(articles):
    fg = FeedGenerator()
    fg.title("DIME 非公式 RSS")
    fg.link(href=BASE_URL, rel='alternate')
    fg.description("DIMEの最新記事を自動取得して生成したRSSフィードです。")

    for a in articles:
        fe = fg.add_entry()
        fe.title(a["title"])
        fe.link(href=a["link"])
        fe.pubDate(a["pubDate"])

    os.makedirs(RSS_OUTPUT_DIR, exist_ok=True)
    fg.rss_file(os.path.join(RSS_OUTPUT_DIR, RSS_OUTPUT_FILE))

if __name__ == "__main__":
    articles = fetch_articles()
    generate_rss(articles)
