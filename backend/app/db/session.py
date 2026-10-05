import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# 1. Read secrets from the environment variables (never hardcoded!)
DB_USER = os.getenv("POSTGRES_USER", "neerniti_admin")
DB_PASS = os.getenv("POSTGRES_PASSWORD", "neerniti_local_dev_password")
DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")
DB_DB = os.getenv("POSTGRES_DB", "neerniti_db")

# 2. Construct the connection URL
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_DB}"

# 3. Create the Engine (the object that actually talks to PostgreSQL)
engine = create_engine(DATABASE_URL, echo=False)

# 4. Create a Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """Dependency to get a database session for each API request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()