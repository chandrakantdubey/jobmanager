import os
from sqlmodel import SQLModel, create_engine, Session

# Database Connection
# Check for DATABASE_URL env var (Docker), else use localhost (Manual)
postgres_url = os.getenv("DATABASE_URL", "postgresql://jobmanager:password@localhost:5432/jobs")

connect_args = {} 
engine = create_engine(postgres_url, echo=True, connect_args=connect_args)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session
