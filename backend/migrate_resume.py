from sqlmodel import create_engine, text, Session
import os

# usage: python3 migrate_resume.py

postgres_url = os.getenv("DATABASE_URL", "postgresql://jobmanager:password@localhost:5432/jobs")
engine = create_engine(postgres_url, echo=True)

def migrate():
    with Session(engine) as session:
        print("Migrating Resume table...")
        try:
            # Check if column exists (naive check by trying to select it, or just alter and catch error)
            # Postgres 'ADD COLUMN IF NOT EXISTS' is supported in recent versions
            session.exec(text("ALTER TABLE resume ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT FALSE;"))
            session.commit()
            print("Migration successful: Added is_active column.")
        except Exception as e:
            print(f"Migration failed or column exists: {e}")

if __name__ == "__main__":
    migrate()
