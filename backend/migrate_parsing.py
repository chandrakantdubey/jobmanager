from sqlmodel import create_engine, text, Session
import os

# usage: python3 migrate_parsing.py

postgres_url = os.getenv("DATABASE_URL", "postgresql://jobmanager:password@localhost:5432/jobs")
engine = create_engine(postgres_url, echo=True)

def migrate():
    with Session(engine) as session:
        print("Migrating Resume table for parsed_titles...")
        try:
            # Add parsed_titles column (JSON type)
            session.exec(text("ALTER TABLE resume ADD COLUMN IF NOT EXISTS parsed_titles JSONB DEFAULT '[]'::jsonb;"))
            session.commit()
            print("Migration successful: Added parsed_titles column.")
        except Exception as e:
            print(f"Migration failed or column exists: {e}")

if __name__ == "__main__":
    migrate()
