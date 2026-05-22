import os
from dotenv import load_dotenv

# Tải biến môi trường từ file .env nếu có
load_dotenv()

# Cấu hình kết nối MySQL, phù hợp với Laragon mặc định
MYSQL_HOST = os.getenv("MYSQL_HOST", "127.0.0.1")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", 3306))
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
DB_NAME = os.getenv("MYSQL_DB", "news_management")

# User-Agent dùng khi gửi request để tránh bị chặn bởi một số trang web
USER_AGENT = os.getenv(
    "NEWS_AGGREGATOR_USER_AGENT",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
)
