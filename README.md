# News Aggregator CLI (Python + MySQL)

Ứng dụng Console quản lý nguồn tin, tự động thu thập link tin tức và cập nhật nội dung chi tiết.

## Yêu cầu
- Python 3.8+
- MySQL server đang chạy
- Các gói Python trong `requirements.txt`

## Cài đặt
1. Cài thư viện:
```bash
pip install -r requirements.txt
```
2. Cấu hình MySQL bằng Laragon
- Mặc định Laragon sử dụng:
  - `MYSQL_HOST=127.0.0.1`
  - `MYSQL_PORT=3306`
  - `MYSQL_USER=root`
  - `MYSQL_PASSWORD=` (để trống)
  - `MYSQL_DB=news_management`

3. Tạo file `.env` (nếu chưa có):
```bash
copy .env.example .env
```
4. Khởi tạo database và seed dữ liệu:
```bash
python init_db.py
```

## Kết nối với Laragon
1. Mở Laragon và Start MySQL.
2. Mở phpMyAdmin hoặc MySQL console của Laragon để kiểm tra kết nối.
3. Nếu muốn tự tạo database bằng Laragon, dùng phpMyAdmin hoặc chạy SQL:
```sql
CREATE DATABASE IF NOT EXISTS news_management CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```
4. Sau đó chạy:
```bash
python init_db.py
```

## Chạy ứng dụng
```bash
python main.py
```

## Chức năng chính
- Quản lý nguồn tin: Thêm / Sửa / Xóa / Xem danh sách nguồn.
- Xem tin tức đã thu thập với phân trang (10 bài mỗi trang).
- Bật / Tắt cronjob thu thập tự động.
- Chạy thủ công quy trình lấy link và cập nhật nội dung ngay.
- Khi thêm hoặc sửa `source`, bạn có thể nhập các CSS selector để crawler hoạt động chính xác trên từng trang:
  - `link_selector` — selector cho link bài trên trang nguồn (ví dụ `h3.title-news a`)
  - `title_selector`, `description_selector`, `content_selector`, `image_selector` — selectors để lấy chi tiết bài
  Nếu không nhập selector, hệ thống sẽ cố gắng dùng parser mặc định theo domain (VnExpress, Tuổi Trẻ) hoặc generic.

- Script `export_backup.py` để xuất `articles` ra JSON và CSV (thư mục `exports/`).

## Cronjob
- `Cronjob 1`: Thu thập danh sách link mới vào `08:00` mỗi ngày.
- `Cronjob 2`: Cập nhật nội dung chi tiết mỗi `30 phút`.

## Lưu ý
- Khi lưu link mới, hệ thống kiểm tra trùng `url` để tránh trùng lặp.
- Yêu cầu `User-Agent` được thêm vào header để giảm khả năng bị chặn.
- Tập trung hỗ trợ 2 nguồn báo phổ biến là VnExpress và Tuổi trẻ.

## Ghi chú
- Nếu bạn cần demo/video, chạy chương trình và quay lại hành động thêm nguồn, bật cron, xem tin và chạy thủ công.
- Lưu link video vào `README.md` nếu có.
## Export / Backup
Bạn có thể xuất dữ liệu `articles` sang `exports/` bằng cách chạy:

```bash
python export_backup.py
```

Hai file sẽ được tạo: một JSON và một CSV với timestamp.
