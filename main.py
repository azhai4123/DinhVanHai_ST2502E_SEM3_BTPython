import math
import threading
import time

import schedule

from db import (
    count_articles,
    delete_source,
    fetch_articles,
    get_categories,
    get_source,
    get_sources,
    insert_source,
    init_database,
    update_source,
)
from scraper import refresh_links, update_pending_content

# Biến toàn cục để điều khiển thread cron
scheduler_thread = None
stop_event = threading.Event()
cron_running = False


def input_int(prompt: str, minimum: int = None, maximum: int = None):
    """Nhận một số nguyên từ người dùng với kiểm tra giá trị."""
    while True:
        value = input(prompt).strip()
        if not value.isdigit():
            print("Vui lòng nhập số nguyên hợp lệ.")
            continue
        number = int(value)
        if minimum is not None and number < minimum:
            print(f"Giá trị phải lớn hơn hoặc bằng {minimum}.")
            continue
        if maximum is not None and number > maximum:
            print(f"Giá trị phải nhỏ hơn hoặc bằng {maximum}.")
            continue
        return number


def input_nonempty(prompt: str):
    """Nhận chuỗi không được để trống từ người dùng."""
    while True:
        value = input(prompt).strip()
        if value:
            return value
        print("Giá trị không được để trống.")


def display_categories():
    """Hiển thị danh sách các danh mục có sẵn."""
    categories = get_categories()
    print("\nDanh sách danh mục:")
    for category in categories:
        print(f"  {category['id']}. {category['name']}")
    return categories


def choose_category():
    """Yêu cầu người dùng chọn một category_id hợp lệ."""
    categories = display_categories()
    if not categories:
        print("Chưa có danh mục nào.")
        return None
    category_ids = {category['id'] for category in categories}
    while True:
        category_id = input_int("Chọn category_id: ")
        if category_id in category_ids:
            return category_id
        print("Chọn category_id hợp lệ từ danh sách.")


def list_sources():
    """Hiển thị danh sách tất cả nguồn tin hiện có."""
    sources = get_sources()
    if not sources:
        print("\nChưa có nguồn tin nào.")
        return
    print("\nNguồn tin hiện có:")
    print("ID | Source Name | URL | Category | LinkSel | ContentSel")
    print("---|-------------|-----|----------|---------|-----------")
    for source in sources:
        # hiển thị ngắn gọn selector để dễ kiểm tra
        link_sel = source.get('link_selector') or ''
        content_sel = source.get('content_selector') or ''
        print(f"{source['id']} | {source['source_name']} | {source['url']} | {source['category_name']} | {link_sel} | {content_sel}")


def add_source():
    """Thêm nguồn tin mới vào bảng sources."""
    print("\nThêm nguồn tin mới")
    name = input_nonempty("Tên nguồn tin: ")
    url = input_nonempty("URL nguồn tin: ")
    category_id = choose_category()
    if category_id is None:
        return
    # Các selector tùy chọn để crawler dùng
    link_selector = input("Link selector (CSS) [ví dụ: h3.title-news a] (Enter để bỏ qua): ").strip() or None
    title_selector = input("Title selector (CSS) [ví dụ: h1.title-detail] (Enter để bỏ qua): ").strip() or None
    description_selector = input("Description selector (CSS) (Enter để bỏ qua): ").strip() or None
    content_selector = input("Content selector (CSS) (Enter để bỏ qua): ").strip() or None
    image_selector = input("Image selector (CSS) (Enter để bỏ qua): ").strip() or None
    insert_source(name, url, category_id, link_selector=link_selector, title_selector=title_selector, description_selector=description_selector, content_selector=content_selector, image_selector=image_selector)
    print("Thêm nguồn tin thành công.")


def edit_source():
    """Sửa thông tin một nguồn tin đã tồn tại."""
    list_sources()
    source_id = input_int("Nhập ID nguồn cần sửa: ")
    source = get_source(source_id)
    if not source:
        print("Nguồn tin không tồn tại.")
        return
    # Cho phép giữ nguyên giá trị cũ nếu để trống
    name_input = input(f"Tên mới [{source['source_name']}] (Enter để giữ): ").strip()
    name = name_input or source['source_name']
    url_input = input(f"URL mới [{source['url']}] (Enter để giữ): ").strip()
    url = url_input or source['url']
    print("Chọn danh mục mới (Enter để giữ danh mục hiện tại):")
    display_categories()
    cat_input = input("Chọn category_id hoặc Enter: ").strip()
    category_id = int(cat_input) if cat_input.isdigit() else source['category_id']
    # Selector fields
    link_sel = input(f"Link selector [{source.get('link_selector')}] (Enter để giữ): ").strip() or source.get('link_selector')
    title_sel = input(f"Title selector [{source.get('title_selector')}] (Enter để giữ): ").strip() or source.get('title_selector')
    desc_sel = input(f"Description selector [{source.get('description_selector')}] (Enter để giữ): ").strip() or source.get('description_selector')
    content_sel = input(f"Content selector [{source.get('content_selector')}] (Enter để giữ): ").strip() or source.get('content_selector')
    image_sel = input(f"Image selector [{source.get('image_selector')}] (Enter để giữ): ").strip() or source.get('image_selector')
    update_source(source_id, name, url, category_id, link_selector=link_sel, title_selector=title_sel, description_selector=desc_sel, content_selector=content_sel, image_selector=image_sel)
    print("Cập nhật nguồn tin thành công.")


def delete_source_menu():
    """Xóa một nguồn tin theo ID."""
    list_sources()
    source_id = input_int("Nhập ID nguồn cần xóa: ")
    source = get_source(source_id)
    if not source:
        print("Nguồn tin không tồn tại.")
        return
    confirm = input(f"Xác nhận xóa nguồn '{source['source_name']}'? (y/n): ").strip().lower()
    if confirm == "y":
        delete_source(source_id)
        print("Xóa nguồn tin thành công.")
    else:
        print("Hủy xóa.")


def show_sources_menu():
    """Menu quản lý nguồn tin trong console."""
    while True:
        print("\n=== QUẢN LÝ NGUỒN TIN ===")
        print("1. Xem danh sách nguồn tin")
        print("2. Thêm nguồn tin")
        print("3. Sửa nguồn tin")
        print("4. Xóa nguồn tin")
        print("0. Quay lại")
        choice = input("Chọn chức năng: ").strip()
        if choice == "1":
            list_sources()
        elif choice == "2":
            add_source()
        elif choice == "3":
            edit_source()
        elif choice == "4":
            delete_source_menu()
        elif choice == "0":
            break
        else:
            print("Lựa chọn không đúng. Vui lòng chọn lại.")


def view_articles():
    """Hiển thị bài viết với phân trang 10 bài/trang."""
    total = count_articles()
    if total == 0:
        print("\nChưa có bài viết nào trong hệ thống.")
        return
    page_size = 10
    page = 1
    total_pages = math.ceil(total / page_size)
    while True:
        articles = fetch_articles(page)
        print(f"\n=== DANH SÁCH BÀI VIẾT (Trang {page}/{total_pages}) ===")
        for article in articles:
            status = "Đã lấy nội dung" if article["status"] == 1 else "Chưa lấy nội dung"
            print(f"[{article['id']}] {article['title']}")
            print(f"    Source: {article['source_name']} | Category: {article['category_name']} | Trạng thái: {status}")
            print(f"    URL: {article['url']}")
            print(f"    Ngày tạo: {article['created_at']}")
            print("-")
        if total_pages == 1:
            break
        command = input("[N]ext, [P]revious, [B]ack: ").strip().lower()
        if command == "n" and page < total_pages:
            page += 1
        elif command == "p" and page > 1:
            page -= 1
        elif command == "b":
            break
        else:
            print("Lựa chọn không hợp lệ hoặc đã ở trang đầu/cuối.")


def run_scheduler_loop():
    """Vòng lặp chạy scheduler để thực thi công việc định kỳ."""
    while not stop_event.is_set():
        schedule.run_pending()
        time.sleep(1)


def start_cron():
    """Khởi động cronjob định kỳ bằng thư viện schedule."""
    global scheduler_thread, cron_running
    if cron_running:
        print("Cronjob đã đang chạy.")
        return
    schedule.clear()
    schedule.every().day.at("10:52").do(refresh_links)
    schedule.every(30).minutes.do(update_pending_content)
    stop_event.clear()
    scheduler_thread = threading.Thread(target=run_scheduler_loop, daemon=True)
    scheduler_thread.start()
    cron_running = True
    print("Đã bật cronjob. Hệ thống sẽ thu thập link vào 10:52 và cập nhật nội dung mỗi 30 phút.")


def stop_cron():
    """Dừng cronjob nếu đang chạy."""
    global cron_running
    if not cron_running:
        print("Cronjob chưa được bật.")
        return
    stop_event.set()
    schedule.clear()
    cron_running = False
    print("Đã tắt cronjob.")


def cron_menu():
    """Menu điều khiển cronjob trong console."""
    while True:
        print("\n=== ĐIỀU KHIỂN CRONJOB ===")
        status = "Đang chạy" if cron_running else "Đã tắt"
        print(f"Trạng thái cronjob: {status}")
        print("1. Bật cronjob")
        print("2. Tắt cronjob")
        print("3. Chạy thủ công tất cả tiến trình ngay")
        print("0. Quay lại")
        choice = input("Chọn chức năng: ").strip()
        if choice == "1":
            start_cron()
        elif choice == "2":
            stop_cron()
        elif choice == "3":
            refresh_links()
            update_pending_content()
        elif choice == "0":
            break
        else:
            print("Lựa chọn không đúng. Vui lòng chọn lại.")


def main_menu():
    """Menu chính của ứng dụng."""
    while True:
        print("\n=== HỆ THỐNG NEWS AGGREGATOR ===")
        print("1. Quản lý nguồn tin (Sources)")
        print("2. Xem tin tức (Articles)")
        print("3. Điều khiển Cronjob")
        print("0. Thoát")
        choice = input("Chọn chức năng: ").strip()
        if choice == "1":
            show_sources_menu()
        elif choice == "2":
            view_articles()
        elif choice == "3":
            cron_menu()
        elif choice == "0":
            stop_cron()
            print("Kết thúc chương trình.")
            break
        else:
            print("Lựa chọn không đúng. Vui lòng chọn lại.")


if __name__ == "__main__":
    try:
        init_database()
    except Exception as exc:
        print("Không thể khởi tạo cơ sở dữ liệu:", exc)
        raise
    main_menu()
