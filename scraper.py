import time
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from config import USER_AGENT
from db import (
    article_url_exists,
    get_pending_articles,
    get_sources,
    insert_article,
    update_article_content,
)

# Header dùng khi gửi request để tránh bị server chặn vì bot
HEADERS = {"User-Agent": USER_AGENT}
TIMEOUT = 12


def fetch_page(url: str):
    """Tải nội dung HTML của một trang và trả về BeautifulSoup."""
    response = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    response.raise_for_status()
    return BeautifulSoup(response.text, "html.parser")


def normalize_url(base_url: str, link: str):
    """Chuyển URL relative thành URL tuyệt đối nếu cần."""
    if not link:
        return None
    parsed = urlparse(link)
    if parsed.scheme and parsed.netloc:
        return link
    return urljoin(base_url, link)


def parse_vnexpress_list(url: str):
    """Lấy danh sách link từ trang VnExpress."""
    soup = fetch_page(url)
    articles = []
    seen = set()
    for element in soup.select("article a[href], h3 a[href], .title-news a[href]"):
        link = normalize_url(url, element.get("href"))
        if not link or "video" in link or link in seen:
            continue
        title = element.get_text(strip=True)
        if title:
            seen.add(link)
            articles.append({"title": title, "url": link})
    return articles


def parse_tuoitre_list(url: str):
    """Lấy danh sách link từ trang Tuổi Trẻ."""
    soup = fetch_page(url)
    articles = []
    seen = set()
    for element in soup.select(".box-news a[href], .title-news a[href], a[href*='tuoitre.vn']"):
        link = normalize_url(url, element.get("href"))
        if not link or "video" in link or link in seen:
            continue
        title = element.get_text(strip=True)
        if title:
            seen.add(link)
            articles.append({"title": title, "url": link})
    return articles


def parse_generic_list(url: str):
    """Lấy danh sách link từ trang chung nếu không phải VnExpress hoặc Tuổi Trẻ."""
    soup = fetch_page(url)
    articles = []
    seen = set()
    parsed_base = urlparse(url)
    for element in soup.select("a[href]"):
        href = element.get("href")
        link = normalize_url(url, href)
        if not link or link in seen:
            continue
        parsed_link = urlparse(link)
        if parsed_link.netloc != parsed_base.netloc:
            continue
        title = element.get_text(strip=True)
        if title and len(title) > 30:
            seen.add(link)
            articles.append({"title": title, "url": link})
    return articles


def parse_source_links(source):
    """Chọn parser phù hợp theo domain của source."""
    """Lấy danh sách link từ một source.

    Nếu source có `link_selector` trong DB thì dùng selector đó, ngược lại
    fallback về các parser theo domain hoặc generic.
    """
    url = source["url"]
    link_selector = source.get("link_selector") if isinstance(source, dict) else getattr(source, 'link_selector', None)
    if link_selector:
        try:
            soup = fetch_page(url)
            articles = []
            seen = set()
            for element in soup.select(link_selector):
                link = normalize_url(url, element.get("href") or element.get('data-src') or element.get('src'))
                if not link or link in seen:
                    continue
                title = element.get_text(strip=True) or element.get('title') or ''
                seen.add(link)
                articles.append({"title": title, "url": link})
            return articles
        except Exception:
            # nếu selector không hợp lệ, fallback
            pass

    parsed = urlparse(url)
    domain = parsed.netloc.lower()
    if "vnexpress" in domain:
        return parse_vnexpress_list(url)
    if "tuoitre" in domain or "tuoitre.vn" in domain:
        return parse_tuoitre_list(url)
    return parse_generic_list(url)


def extract_article_detail(url: str):
    """Lấy summary và nội dung chi tiết của bài viết."""
    # Backward-compatible: this function supports basic extraction without selectors.
    soup = fetch_page(url)
    summary = None
    content = None
    description = soup.select_one("meta[name='description']")
    if description and description.get("content"):
        summary = description.get("content").strip()
    body = soup.select_one("article") or soup.select_one(".fck_detail") or soup.select_one(".detail-content")
    if body:
        paragraphs = [p.get_text(strip=True) for p in body.find_all("p") if p.get_text(strip=True)]
        if paragraphs:
            content = "\n\n".join(paragraphs)
            if not summary:
                summary = paragraphs[0]
    if not content:
        fallback = [p.get_text(strip=True) for p in soup.select("p") if p.get_text(strip=True)]
        if fallback:
            content = "\n\n".join(fallback[:20])
            if not summary:
                summary = fallback[0]
    return summary or "", content or ""


def refresh_links():
    """Thu thập link mới từ các nguồn đã thêm và lưu vào bảng articles."""
    print("[Cronjob] Bắt đầu thu thập danh sách link mới...")
    sources = get_sources()
    total_new = 0
    for source in sources:
        try:
            found = parse_source_links(source)
        except Exception as exc:
            print(f"  Lỗi khi lấy link từ {source['source_name']} ({source['url']}): {exc}")
            continue
        for item in found:
            if not article_url_exists(item["url"]):
                insert_article(source["id"], source["category_id"], item["title"], item["url"])
                total_new += 1
    print(f"[Cronjob] Hoàn thành. Thêm {total_new} link mới.")
    return total_new


def update_pending_content():
    """Cập nhật nội dung chi tiết cho những bài mới vừa lấy link."""
    print("[Cronjob] Bắt đầu cập nhật nội dung chi tiết cho tin mới...")
    pending = get_pending_articles()
    updated = 0
    for article in pending:
        try:
            summary, content = extract_article_detail(article["url"])
            if content:
                update_article_content(article["id"], summary, content)
                updated += 1
                time.sleep(1)
            else:
                print(f"  Không lấy được nội dung cho {article['url']}")
        except Exception as exc:
            print(f"  Lỗi khi lấy nội dung {article['url']}: {exc}")
    print(f"[Cronjob] Hoàn thành. Cập nhật {updated} bài viết.")
    return updated
