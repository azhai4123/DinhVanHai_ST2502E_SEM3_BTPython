import os
import json
import csv
from datetime import datetime
from db import fetch_all

EXPORT_DIR = os.path.join(os.path.dirname(__file__), "exports")
os.makedirs(EXPORT_DIR, exist_ok=True)


def export_articles_json(filename: str = None):
    articles = fetch_all(
        "SELECT a.id, a.title, a.url, a.summary, a.content, a.status, a.created_at, s.source_name, c.name AS category_name "
        "FROM articles a JOIN sources s ON a.source_id = s.id JOIN categories c ON a.category_id = c.id ORDER BY a.id"
    )
    if filename is None:
        filename = f"articles_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    path = os.path.join(EXPORT_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(articles, f, ensure_ascii=False, default=str, indent=2)
    return path


def export_articles_csv(filename: str = None):
    articles = fetch_all(
        "SELECT a.id, a.title, a.url, a.summary, a.content, a.status, a.created_at, s.source_name, c.name AS category_name "
        "FROM articles a JOIN sources s ON a.source_id = s.id JOIN categories c ON a.category_id = c.id ORDER BY a.id"
    )
    if filename is None:
        filename = f"articles_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    path = os.path.join(EXPORT_DIR, filename)
    with open(path, "w", newline='', encoding="utf-8") as csvfile:
        if not articles:
            headers = ["id","title","url","summary","content","status","created_at","source_name","category_name"]
            writer = csv.writer(csvfile)
            writer.writerow(headers)
            return path
        headers = list(articles[0].keys())
        writer = csv.DictWriter(csvfile, fieldnames=headers)
        writer.writeheader()
        for row in articles:
            writer.writerow(row)
    return path


if __name__ == "__main__":
    print("Exporting articles to JSON and CSV in:", EXPORT_DIR)
    j = export_articles_json()
    c = export_articles_csv()
    print("Exported:", j)
    print("Exported:", c)
