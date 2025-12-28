from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text
from database import engine, get_db, Base
from routers import *
from models import *
from core.config import settings

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="G-Drive API",
    description="FastAPI backend for G-Drive application",
    version="1.0.0"
)

origins = settings.ORIGIN.split(",") if settings.ORIGIN else ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Initialize database connection on startup"""
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        print("Database connection successful")
    except Exception as e:
        print(f"Database connection failed: {e}")


@app.get("/")
async def root():
    return {"message": "Welcome to G-Drive API"}


app.include_router(auth_router)
app.include_router(file_router)
app.include_router(folder_router)
app.include_router(upload_router)


@app.get("/health")
async def health_check(db: Session = Depends(get_db)):
    """Health check endpoint that also verifies database connection"""
    try:
        # Test database connection
        db.execute(text("SELECT 1"))
        return {
            "status": "healthy",
            "database": "connected"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e)
        }

