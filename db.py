import pymysql
from pymysql.cursors import DictCursor
from config import MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, DB_NAME

# Các danh mục mặc định được seed vào bảng categories
CATEGORY_SEED = [
    "Công nghệ",
    "Kinh doanh",
    "Thể thao",
    "Giải trí",
    "Sức khỏe",
]


def get_connection(db: str = None):
    """Tạo kết nối đến MySQL. Nếu db=None thì kết nối chỉ tới server."""
    return pymysql.connect(
        host=MYSQL_HOST,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        port=MYSQL_PORT,
        db=db,
        charset="utf8mb4",
        cursorclass=DictCursor,
        autocommit=True,
    )


def execute(query: str, params=None, db: str = DB_NAME):
    """Thực thi câu lệnh SQL không trả về nhiều hàng."""
    with get_connection(db) as conn:
        with conn.cursor() as cursor:
            cursor.execute(query, params or ())
            return cursor.lastrowid


def fetch_all(query: str, params=None, db: str = DB_NAME):
    """Thực thi câu lệnh SQL và trả về tất cả hàng kết quả."""
    with get_connection(db) as conn:
        with conn.cursor() as cursor:
            cursor.execute(query, params or ())
            return cursor.fetchall()


def fetch_one(query: str, params=None, db: str = DB_NAME):
    """Thực thi câu lệnh SQL và trả về một hàng kết quả."""
    with get_connection(db) as conn:
        with conn.cursor() as cursor:
            cursor.execute(query, params or ())
            return cursor.fetchone()


def init_database():
    """Tạo database và các bảng nếu chưa tồn tại."""
    with get_connection(db=None) as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
    with get_connection(DB_NAME) as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS categories (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(255) NOT NULL UNIQUE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS sources (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    source_name VARCHAR(255) NOT NULL,
                    url VARCHAR(512) NOT NULL,
                    -- CSS selector để tìm link bài trên trang nguồn (ví dụ: h3.title-news a)
                    link_selector VARCHAR(512) DEFAULT NULL,
                    -- selectors để lấy chi tiết bài: title, description, content, image
                    title_selector VARCHAR(512) DEFAULT NULL,
                    description_selector VARCHAR(512) DEFAULT NULL,
                    content_selector VARCHAR(512) DEFAULT NULL,
                    image_selector VARCHAR(512) DEFAULT NULL,
                    category_id INT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS articles (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    source_id INT NOT NULL,
                    category_id INT NOT NULL,
                    title VARCHAR(512) NOT NULL,
                    url VARCHAR(768) NOT NULL UNIQUE,
                    summary TEXT,
                    content LONGTEXT,
                    status TINYINT NOT NULL DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (source_id) REFERENCES sources(id) ON DELETE CASCADE,
                    FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE,
                    INDEX idx_status (status)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )
            # Nếu bảng sources đã tồn tại trước đó (phiên bản cũ), bổ sung các cột selector cần thiết
            # Kiểm tra từng cột trong INFORMATION_SCHEMA trước khi thêm
            cols = [
                ("link_selector", "VARCHAR(512) DEFAULT NULL"),
                ("title_selector", "VARCHAR(512) DEFAULT NULL"),
                ("description_selector", "VARCHAR(512) DEFAULT NULL"),
                ("content_selector", "VARCHAR(512) DEFAULT NULL"),
                ("image_selector", "VARCHAR(512) DEFAULT NULL"),
            ]
            for col_name, col_def in cols:
                cursor.execute(
                    "SELECT COUNT(*) AS cnt FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'sources' AND COLUMN_NAME = %s",
                    (DB_NAME, col_name),
                )
                exists = cursor.fetchone()
                if exists and exists.get("cnt", 0) == 0:
                    cursor.execute(f"ALTER TABLE sources ADD COLUMN {col_name} {col_def}")
    seed_categories()
    # Seed default sources (VnExpress, Tuoi Tre) nếu cần
    try:
        seed_sources()
    except Exception:
        # Nếu seed sources lỗi thì không phá vỡ khởi tạo DB
        pass


def seed_categories():
    """Chèn danh mục mặc định nếu bảng categories chưa có dữ liệu."""
    existing = fetch_all("SELECT name FROM categories")
    existing_names = {row["name"] for row in existing}
    for category in CATEGORY_SEED:
        if category not in existing_names:
            execute("INSERT INTO categories (name) VALUES (%s)", (category,))


# Một vài nguồn mặc định (có selector cơ bản) để seed nhanh khi khởi tạo
DEFAULT_SOURCES = [
    (
        "VnExpress - Thể thao",
        "https://vnexpress.net/the-thao",
        "h3.title-news a",
        "h1.title-detail",
        "meta[name=description]",
        "article.fck_detail",
        "figure.photo a img",
        3,  # category_id (sẽ tương ứng với "Thể thao" trong CATEGORY_SEED)
    ),
    (
        "TuoiTre - Thể thao",
        "https://tuoitre.vn/the-thao.htm",
        "a.story__thumb",
        "h1.news__title",
        "meta[name=description]",
        ".main-content",
        "figure img",
        3,
    ),
]


def seed_sources():
    """Chèn các nguồn mặc định nếu chưa có trong bảng sources."""
    # Lấy id các categories để mapping nếu cần (đơn giản ở đây giả sử thứ tự giống CATEGORY_SEED)
    for src in DEFAULT_SOURCES:
        name, url, link_sel, title_sel, desc_sel, content_sel, img_sel, category_id = src
        existing = fetch_one("SELECT id FROM sources WHERE url = %s", (url,))
        if not existing:
            insert_source(name, url, category_id, link_selector=link_sel, title_selector=title_sel,
                          description_selector=desc_sel, content_selector=content_sel, image_selector=img_sel)


def get_categories():
    """Lấy danh sách tất cả danh mục."""
    return fetch_all("SELECT id, name FROM categories ORDER BY id")


def get_category(category_id: int):
    """Lấy thông tin một category theo id."""
    return fetch_one("SELECT id, name FROM categories WHERE id = %s", (category_id,))


def get_sources():
    """Lấy danh sách tất cả nguồn tin cùng tên danh mục."""
    return fetch_all(
        "SELECT s.id, s.source_name, s.url, s.link_selector, s.title_selector, s.description_selector, s.content_selector, s.image_selector, s.category_id, c.name AS category_name FROM sources s JOIN categories c ON s.category_id = c.id ORDER BY s.id"
    )


def get_source(source_id: int):
    """Lấy một nguồn tin theo id."""
    return fetch_one(
        "SELECT id, source_name, url, link_selector, title_selector, description_selector, content_selector, image_selector, category_id FROM sources WHERE id = %s",
        (source_id,),
    )


def insert_source(source_name: str, url: str, category_id: int, link_selector: str = None, title_selector: str = None, description_selector: str = None, content_selector: str = None, image_selector: str = None):
    """Thêm một nguồn tin mới, hỗ trợ các selector để crawling."""
    return execute(
        "INSERT INTO sources (source_name, url, link_selector, title_selector, description_selector, content_selector, image_selector, category_id) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
        (source_name, url, link_selector, title_selector, description_selector, content_selector, image_selector, category_id),
    )


def update_source(source_id: int, source_name: str, url: str, category_id: int, link_selector: str = None, title_selector: str = None, description_selector: str = None, content_selector: str = None, image_selector: str = None):
    """Cập nhật thông tin nguồn tin và selector nếu cần."""
    execute(
        "UPDATE sources SET source_name = %s, url = %s, link_selector = %s, title_selector = %s, description_selector = %s, content_selector = %s, image_selector = %s, category_id = %s WHERE id = %s",
        (source_name, url, link_selector, title_selector, description_selector, content_selector, image_selector, category_id, source_id),
    )


def delete_source(source_id: int):
    """Xóa nguồn tin khỏi bảng sources."""
    execute("DELETE FROM sources WHERE id = %s", (source_id,))


def article_url_exists(url: str):
    """Kiểm tra URL bài viết đã tồn tại trong bảng articles chưa."""
    existing = fetch_one("SELECT id FROM articles WHERE url = %s", (url,))
    return existing is not None


def insert_article(source_id: int, category_id: int, title: str, url: str):
    """Lưu một bài viết mới với trạng thái chưa lấy nội dung."""
    execute(
        "INSERT INTO articles (source_id, category_id, title, url, status) VALUES (%s, %s, %s, %s, 0)",
        (source_id, category_id, title, url),
    )


def get_pending_articles():
    """Lấy danh sách bài viết có status = 0 để xử lý chi tiết sau."""
    return fetch_all("SELECT id, source_id, category_id, title, url FROM articles WHERE status = 0 ORDER BY id")


def update_article_content(article_id: int, summary: str, content: str):
    """Cập nhật summary và content, đồng thời đổi trạng thái bài viết đã lấy nội dung."""
    execute(
        "UPDATE articles SET summary = %s, content = %s, status = 1 WHERE id = %s",
        (summary, content, article_id),
    )


def count_articles():
    """Đếm tổng số bài viết trong bảng articles."""
    result = fetch_one("SELECT COUNT(*) AS total FROM articles")
    return result["total"] if result else 0


def fetch_articles(page: int, page_size: int = 10):
    """Lấy danh sách bài viết theo trang với LIMIT/OFFSET."""
    offset = (page - 1) * page_size
    return fetch_all(
        "SELECT a.id, a.title, a.url, a.status, a.created_at, s.source_name, c.name AS category_name "
        "FROM articles a "
        "JOIN sources s ON a.source_id = s.id "
        "JOIN categories c ON a.category_id = c.id "
        "ORDER BY a.created_at DESC LIMIT %s OFFSET %s",
        (page_size, offset),
    )
