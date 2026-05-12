import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# The database URL for SQLite
DATABASE_URL = "sqlite:///./nyayasetu.db"

# Create the SQLAlchemy engine
# connect_args={"check_same_thread": False} is needed only for SQLite
engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)

# SessionLocal class will be a database session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for the ORM models
Base = declarative_base()

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
