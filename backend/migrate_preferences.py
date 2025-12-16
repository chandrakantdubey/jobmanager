from sqlmodel import create_engine, text, Session
import os

# usage: python3 migrate_preferences.py

postgres_url = os.getenv("DATABASE_URL", "postgresql://jobmanager:password@localhost:5432/jobs")
engine = create_engine(postgres_url, echo=True)

def migrate():
    with Session(engine) as session:
        print("Migrating Resume table for search_preferences...")
        try:
            # Add search_preferences column (JSON type)
            session.exec(text("ALTER TABLE resume ADD COLUMN IF NOT EXISTS search_preferences JSONB DEFAULT '{}'::jsonb;"))
            session.commit()
            print("Migration successful: Added search_preferences column.")
        except Exception as e:
            print(f"Migration failed or column exists: {e}")

if __name__ == "__main__":
    migrate()
