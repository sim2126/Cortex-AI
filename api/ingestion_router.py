from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Body
from typing import List
import os
import shutil
from pathlib import Path
import logging
import asyncio
import httpx

# Add the root directory to the Python path
import sys
sys.path.append(str(Path(__file__).parent.parent))

from ingestion.engine import IngestionEngine
from ingestion.sources import LocalDirectorySource, WebUrlSource

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/ingestion",
    tags=["Ingestion"]
)

UPLOAD_DIR = "temp_uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)
MAX_FILE_SIZE_MB = 6
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

def process_in_background(source, temp_file_path=None):
    """Generic background processing function."""
    task_name = temp_file_path if temp_file_path else "link ingestion"
    logger.info(f"Background task started for: {task_name}")
    try:
        engine = IngestionEngine(data_sources=[source])
        engine.run()
        logger.info(f"Background task successfully processed: {task_name}")
    except Exception as e:
        logger.error(f"Background processing for {task_name} failed: {e}", exc_info=True)
    finally:
        # Clean up the temporary file only if it was a file upload
        if temp_file_path and os.path.exists(temp_file_path):
            # Since the source for files is the whole directory, we must be careful
            # A better approach would be to process the file directly, but for this
            # simple case, we remove the file after processing.
            try:
                os.remove(temp_file_path)
                logger.info(f"Cleaned up temporary file: {temp_file_path}")
            except Exception as e:
                 logger.error(f"Failed to clean up temp file {temp_file_path}: {e}")


@router.post("/upload/pdf")
async def upload_pdf(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    """Accepts a PDF, validates it, and schedules it for background processing."""
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Invalid file type. Only PDFs are accepted.")
    
    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(status_code=413, detail=f"File size exceeds {MAX_FILE_SIZE_MB} MB limit.")
    
    await file.seek(0)
    temp_file_path = os.path.join(UPLOAD_DIR, file.filename)
    
    with open(temp_file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # We will pass the specific file path to the background task for cleanup
    source = LocalDirectorySource(path=UPLOAD_DIR)
    background_tasks.add_task(process_in_background, source, temp_file_path)

    return {"message": "PDF upload successful. Processing has started in the background."}

async def check_urls(urls: List[str]) -> (List[str], List[str]):
    """Checks a list of URLs asynchronously to see if they are publicly accessible."""
    valid_urls, invalid_urls = [], []
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    async with httpx.AsyncClient(headers=headers, follow_redirects=True, timeout=10.0) as client:
        tasks = [client.head(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    for i, result in enumerate(results):
        if isinstance(result, httpx.Response) and 200 <= result.status_code < 300:
            # Use the final URL after redirects
            valid_urls.append(str(result.url))
        else:
            invalid_urls.append(urls[i])
            logger.warning(f"Failed to access URL {urls[i]}: {result}")
    return valid_urls, invalid_urls

@router.post("/links")
async def ingest_links(background_tasks: BackgroundTasks, urls: List[str] = Body(..., embed=True)):
    """
    Validates a list of URLs, schedules the valid ones for background processing,
    and returns any invalid URLs to the client.
    """
    if not urls:
        raise HTTPException(status_code=400, detail="URL list cannot be empty.")
    
    valid_urls, invalid_urls = await check_urls(urls)

    if valid_urls:
        source = WebUrlSource(urls=valid_urls)
        background_tasks.add_task(process_in_background, source)

    if invalid_urls:
        if not valid_urls:
             raise HTTPException(
                status_code=400,
                detail=f"Could not scrape any provided links. Please ensure they are public and accessible."
            )
        return {
            "status": "processing_started_partially",
            "message": f"Processing {len(valid_urls)} valid link(s). The following {len(invalid_urls)} link(s) were ignored as they may be private or inaccessible.",
            "failed_urls": invalid_urls
        }

    return {"status": "processing_started", "message": f"All {len(valid_urls)} link(s) submitted for processing."}

