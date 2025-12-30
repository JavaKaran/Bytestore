import asyncio
from database import SessionLocal
from datetime import datetime, timedelta, timezone
from models.file import File, FileStatus
from sqlalchemy.orm import Session
from services.upload_service import UploadService

STALE_AFTER_HOURS = 12 # 12 hours

CLEANUP_INTERVAL_SECONDS = 12 * 60 * 60 # 12 hours in seconds

async def cleanup_old_files():
    while True:
        db = SessionLocal()
        try:
            await clean_files(db)
        except Exception as e:
            print(f"Upload cleanup failed: {e}")
        finally:
            db.close()

        await asyncio.sleep(CLEANUP_INTERVAL_SECONDS)

async def clean_files(db: Session):

    print(f"Cleaning files {datetime.now()}")

    cutoff = datetime.now(timezone.utc) - timedelta(hours=STALE_AFTER_HOURS)

    stale_files = db.query(File).filter(File.updated_at < cutoff, File.status == FileStatus.INITIATED).all()

    upload_service = UploadService(db)

    for file in stale_files:
        try:
            print(f"Aborting multipart upload for file: {file.id}")
            upload_service.abort_multipart_upload(file.id, file.user_id)
        except Exception as e:
            print(f"Error deleting file: {e}")