from db import init_database


if __name__ == "__main__":
    print("Initializing news_management database and seeding categories...")
    try:
        init_database()
        print("Database initialized successfully.")
    except Exception as exc:
        print("Failed to initialize the database:", exc)
