from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from sqlalchemy.pool import NullPool
from app.config import settings
import logging

logger = logging.getLogger(__name__)

# Create database engine
engine = create_engine(
    settings.database_url,
    poolclass=NullPool,
    echo=settings.environment == "development"
)

# Create session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Declarative base for models
Base = declarative_base()


def get_db() -> Session:
    """
    Dependency injection function for FastAPI endpoints.
    Provides a database session and ensures it's closed after use.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """
    Initialize the database by creating all tables and running seed data.
    Called on application startup.
    """
    try:
        # Create all tables defined in models
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")

        # Run seed data
        seed_data()
        logger.info("Seed data loaded successfully")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise


def seed_data() -> None:
    """
    Load initial seed data into the database.
    This includes default users, roles, hazard layers, etc.
    """
    db = SessionLocal()
    try:
        # Check if seed data already exists
        # This is a placeholder - actual seed data loading logic will go here
        # Examples:
        # - Create default roles (admin, data_manager, analyst, reviewer, public)
        # - Create default hazard layers
        # - Create default land use classes
        # - Create default analysis templates

        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Error loading seed data: {e}")
        raise
    finally:
        db.close()
