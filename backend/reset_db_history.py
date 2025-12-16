from database import engine, get_session
from sqlmodel import text

def reset_table():
    with engine.connect() as conn:
        print("Dropping SearchHistory table...")
        conn.execute(text("DROP TABLE IF EXISTS searchhistory CASCADE"))
        conn.commit()
        print("Done. It will be recreated on server startup.")

if __name__ == "__main__":
    reset_table()
