# generate_rss.py
import os
import re
import requests
from urllib.parse import urlparse, urlunparse
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator
from datetime import datetime, timezone

BASE_URL = "https://dime.jp/genre/"
RSS_OUTPUT_DIR = "rss"
RSS_OUTPUT_FILE = "dime.xml"

UA = {"User-Agent": "Mozilla/5.0 (+https://github.com/fumopan/dime-rss)"}
TIMEOUT = 15  # 秒


def guess_mime(url: str) -> str:
    path = urlparse(url).path.lower()
    if path.endswith(".jpg") or path.endswith(".jpeg"):
        return "image/jpeg"
    if path.endswith(".png"):
        return "image/png"
    if path.endswith(".gif"):
        return "image/gif"
    if path.endswith(".webp"):
        return "image/webp"
    return "image/jpeg"  # よく使われる既定


def clean_thumb_url(url: str) -> str:
    """
    ファイル名の末尾にある -{W}x{H} を拡張子直前から除去する。
    例: .../shutterstock_2471661487-365x205.jpg -> .../shutterstock_2471661487.jpg
    クエリやフラグメントは保持。
    """
    if not url:
        return url
    pr = urlparse(url)
    # パスのファイル名部分だけ置換
    cleaned_path = re.sub(r"-(\d+)x(\d+)(?=\.\w+$)", "", pr.path)
    return urlunparse((pr.scheme, pr.netloc, cleaned_path, pr.params, pr.query, pr.fragment))


def fetch_article_title_and_ogimage(link: str) -> tuple[str, str | None]:
    """
    記事ページにアクセスして <h1> タイトルと og:image を返す。
    取得できない場合は (\"(no title)\", None)。
    """
    try:
        r = requests.get(link, headers=UA, timeout=TIMEOUT)
        r.raise_for_status()
        soup = BeautifulSoup(r.content, "html.parser")
        # タイトル
        h1 = soup.find("h1")
        title = h1.get_text(strip=True) if h1 else "(no title)"
        # og:image
        og = soup.select_one('meta[property="og:image"]')
        ogimg = og["content"].strip() if og and og.get("content") else None
        return title, ogimg
    except Exception:
        return "(no title)", None


def fetch_articles():
    r = requests.get(BASE_URL, headers=UA, timeout=TIMEOUT)
    r.raise_for_status()
    soup = BeautifulSoup(r.content, "html.parser")

    # 必要ならデバッグHTMLを出力
    # with open("dime_debug.html", "w", encoding="utf-8") as f:
    #     f.write(soup.prettify())

    items = soup.select("li.entryList_item")
    articles = []

    for item in items[:10]:
        link_tag = item.select_one("a.entryList_item_link")
        date_tag = item.select_one("span.entryList_item_date")
        img_tag = item.select_one("div.entryList_item_img img")

        if not (link_tag and date_tag):
            continue

        link = link_tag.get("href", "").strip()
        date_str = date_tag.get_text(strip=True)

        # 一覧のサムネ候補（lazy対応）
        thumb = None
        if img_tag:
            thumb = (
                img_tag.get("src")
                or img_tag.get("data-src")
                or (img_tag.get("srcset", "").split()[0] if img_tag.get("srcset") else None)
            )
        # 記事ページからタイトル＆og:image
        title, ogimg = fetch_article_title_and_ogimage(link)
        if not thumb and ogimg:
            thumb = ogimg

        # サムネURLをクリーンアップ
        thumb = clean_thumb_url(thumb) if thumb else None

        # 日付をUTC付きに
        try:
            pub_date = datetime.strptime(date_str, "%Y.%m.%d").replace(tzinfo=timezone.utc)
        except Exception:
            pub_date = datetime.utcnow().replace(tzinfo=timezone.utc)

        articles.append(
            {
                "title": title,
                "link": link,
                "pubDate": pub_date,
                "thumb": thumb,
            }
        )

    return articles


def generate_rss(articles):
    fg = FeedGenerator()
    fg.title("DIME 非公式 RSS")
    fg.link(href=BASE_URL, rel="alternate")
    fg.description("DIMEの最新記事を自動取得して生成したRSSフィードです。")

    for a in articles:
        # 必須フィールドがないものはスキップして安定運用
        if not all([a.get("title"), a.get("link"), a.get("pubDate")]):
            print(f"⚠ 不完全な記事をスキップ: {a}")
            continue

        fe = fg.add_entry()
        fe.title(a["title"])
        fe.link(href=a["link"])
        fe.pubDate(a["pubDate"])

        # サムネイルを enclosure で添付（多くのリーダーがサムネイル扱い）
        if a.get("thumb"):
            fe.enclosure(a["thumb"], 0, guess_mime(a["thumb"]))

        # （任意）見た目重視で description にも画像を出したいときは以下を有効化
        # if a.get("thumb"):
        #     img_html = f'<p><img src="{a["thumb"]}" referrerpolicy="no-referrer" /></p>'
        #     fe.description(img_html + a["title"])
        # else:
        #     fe.description(a["title"])

    os.makedirs(RSS_OUTPUT_DIR, exist_ok=True)
    fg.rss_file(os.path.join(RSS_OUTPUT_DIR, RSS_OUTPUT_FILE))


if __name__ == "__main__":
    try:
        arts = fetch_articles()
        print(f"{len(arts)} 件の記事を取得しました")
        generate_rss(arts)
        print(f"RSSファイルを書き出しました: {os.path.join(RSS_OUTPUT_DIR, RSS_OUTPUT_FILE)}")
    except Exception as e:
        # ここで例外を握りつぶさずログだけ出して終わる（Actionsのログで原因追跡しやすく）
        import traceback

        traceback.print_exc()
        raise
