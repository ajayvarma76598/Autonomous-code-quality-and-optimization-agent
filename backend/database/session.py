import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from .models.models import Base
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Construct DATABASE_URL from environment components, with local fallbacks
DATABASE_URL = f"postgresql://{os.getenv('DB_USER','postgres.lveosfphvrfolskzxxfq')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST','aws-1-ap-northeast-2.pooler.supabase.com')}:{os.getenv('DB_PORT', '5432')}/{os.getenv('DB_NAME', 'postgres')}"

# Engine configured for psycopg2 by default, with connection pooling keepalives
engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_recycle=1800)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    """
    Initializes the database by attempting to create the vector extension and
    then creating all tables defined in models.py.
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
            conn.commit()
            print("pgvector extension is ready.")
    except Exception as e:
        print(f"Warning: Could not create vector extension automatically: {e}")
        
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully.")

def get_db():
    """
    Dependency to be used in FastAPI endpoints to get a database session.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

if __name__ == "__main__":
    init_db()
