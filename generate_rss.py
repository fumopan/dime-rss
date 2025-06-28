import requests
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator
from datetime import datetime, timezone
import os

BASE_URL = "https://dime.jp/genre/"
RSS_OUTPUT_DIR = "rss"
RSS_OUTPUT_FILE = "dime.xml"

def fetch_articles():
    res = requests.get(BASE_URL, headers={"User-Agent": "Mozilla/5.0"})
    soup = BeautifulSoup(res.content, "html.parser")

    # デバッグ用にHTMLを保存（任意）
    with open("dime_debug.html", "w", encoding="utf-8") as f:
        f.write(soup.prettify())

    items = soup.select("li.entryList_item")
    articles = []

    for item in items[:10]:
        link_tag = item.select_one("a.entryList_item_link")
        title_tag = item.select_one("p.entryList_item_title")
        date_tag = item.select_one("span.entryList_item_date")

        if not (link_tag and title_tag and date_tag):
            continue

        link = link_tag["href"]
        title = title_tag.get_text(strip=True)
        date_str = date_tag.get_text(strip=True)

        try:
            pub_date = datetime.strptime(date_str, "%Y.%m.%d").replace(tzinfo=timezone.utc)
        except Exception:
            pub_date = datetime.utcnow().replace(tzinfo=timezone.utc)

        articles.append({
            "title": title,
            "link": link,
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
    if articles:
        print(f"{len(articles)} 件の記事を取得しました")
    else:
        print("記事が取得できませんでした")
    generate_rss(articles)
