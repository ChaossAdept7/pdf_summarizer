"""
API routes for PDF summarizer.

Endpoints:
- POST /upload - Upload PDF for processing
- GET /status/{task_id} - Check processing status
- GET /history - Get processing history
"""

import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, UploadFile, Depends, Path as PathParam

from app.config import Settings, get_settings
from app.models import (
    UploadResponse,
    TaskStatusResponse,
    HistoryResponse,
    ProcessingResult,
    TaskData,
    TaskStatusEnum,
)
from app.storage.memory_store import get_memory_store
from app.storage.file_storage import save_upload_file, get_file_size
from app.services.pdf_processor import (
    convert_pdf_to_images,
    cleanup_temp_images,
    PDFProcessingError,
)
from app.services.ai_service import process_pdf_complete, AIServiceError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["pdf-processing"])


# ========================================
# Background Task Orchestration
# ========================================


async def process_pdf_task(
    task_id: str,
    file_path: str,
    filename: str,
    file_size: int,
) -> None:
    """
    Background task for processing PDF.

    This function orchestrates the entire PDF processing pipeline:
    1. Convert PDF to images (30% progress)
    2. Extract text from images using Vision API (70% progress)
    3. Generate summary (90% progress)
    4. Save result and add to history (100% progress)

    Args:
        task_id: Unique task identifier
        file_path: Path to uploaded PDF file
        filename: Original filename
        file_size: File size in bytes
    """
    store = get_memory_store()
    settings = get_settings()
    image_paths = []

    try:
        log_msg = f"[TASK {task_id}] Starting PDF processing: {filename} ({file_size} bytes)"
        logger.info(log_msg)
        print(log_msg, flush=True)

        # ========================================
        # Step 1: Convert PDF to Images (0-30%)
        # ========================================
        await store.update_task_progress(task_id, progress=10)

        image_paths, page_count = await convert_pdf_to_images(
            pdf_path=file_path,
            output_dir=str(settings.temp_dir),
            dpi=settings.image_dpi,
            image_format=settings.image_format,
        )

        log_msg = f"[TASK {task_id}] Converted {page_count} pages to images"
        logger.info(log_msg)
        print(log_msg, flush=True)
        await store.update_task_progress(task_id, progress=30)

        # ========================================
        # Step 2: Process with AI (30-90%)
        # ========================================

        def progress_callback(current_page: int, total_pages: int):
            """Update progress during AI processing."""
            # Map pages to 30-90% progress range
            page_progress = int(30 + (current_page / total_pages) * 60)
            # Don't await here as it's called from synchronous context
            # We'll update in batches instead
            pass

        log_msg = f"[TASK {task_id}] Starting AI processing for {len(image_paths)} images..."
        logger.info(log_msg)
        print(log_msg, flush=True)

        ai_result = await process_pdf_complete(
            image_paths=image_paths, progress_callback=progress_callback
        )

        summary = ai_result["summary"]

        log_msg = f"[TASK {task_id}] AI processing complete. Summary length: {len(summary)} chars"
        logger.info(log_msg)
        print(log_msg, flush=True)
        await store.update_task_progress(task_id, progress=90)

        # ========================================
        # Step 3: Save Result (90-100%)
        # ========================================

        result = ProcessingResult(
            filename=filename,
            summary=summary,
            page_count=page_count,
            processed_at=datetime.utcnow(),
            file_size=file_size,
        )

        # Mark task as completed and add to history
        await store.complete_task(task_id, result)

        log_msg = f"[TASK {task_id}] ✅ Processing completed successfully!"
        logger.info(log_msg)
        print(log_msg, flush=True)

    except PDFProcessingError as e:
        log_msg = f"[TASK {task_id}] ❌ PDF processing error: {e}"
        logger.error(log_msg)
        print(log_msg, flush=True)
        await store.fail_task(task_id, f"PDF processing error: {str(e)}")

    except AIServiceError as e:
        log_msg = f"[TASK {task_id}] ❌ AI service error: {e}"
        logger.error(log_msg)
        print(log_msg, flush=True)
        await store.fail_task(task_id, f"AI service error: {str(e)}")

    except Exception as e:
        log_msg = f"[TASK {task_id}] ❌ Unexpected error: {e}"
        logger.error(log_msg, exc_info=True)
        print(log_msg, flush=True)
        await store.fail_task(task_id, f"Processing failed: {str(e)}")

    finally:
        # ========================================
        # Cleanup: Delete temporary images
        # ========================================
        if image_paths:
            try:
                await cleanup_temp_images(image_paths)
                log_msg = f"[TASK {task_id}] 🧹 Cleaned up {len(image_paths)} temp files"
                logger.info(log_msg)
                print(log_msg, flush=True)
            except Exception as e:
                log_msg = f"[TASK {task_id}] ⚠️  Cleanup error: {e}"
                logger.warning(log_msg)
                print(log_msg, flush=True)


# ========================================
# API Endpoints
# ========================================


@router.post(
    "/upload",
    response_model=UploadResponse,
    status_code=200,
    summary="Upload PDF for Processing",
    description="""
    Upload a PDF file and start asynchronous processing.

    The file is validated for size and type, then queued for background processing.
    You'll receive a task_id immediately which can be used to poll processing status.

    **Validation:**
    - Max file size: 50MB (52,428,800 bytes)
    - Max pages: 100
    - Allowed format: PDF only

    **Processing steps:**
    1. PDF is converted to images
    2. Each page is analyzed using OpenAI Vision API
    3. Text is extracted from all pages
    4. AI generates a comprehensive summary
    5. Result is stored in history (last 5 documents)
    """,
    responses={
        200: {
            "description": "PDF uploaded successfully",
            "content": {
                "application/json": {
                    "example": {
                        "task_id": "550e8400-e29b-41d4-a716-446655440000",
                        "status": "processing",
                        "message": "PDF uploaded successfully. Processing started."
                    }
                }
            }
        },
        400: {
            "description": "Invalid file type",
            "content": {
                "application/json": {
                    "example": {"detail": "Invalid file type. Allowed extensions: ['.pdf']"}
                }
            }
        },
        413: {
            "description": "File too large",
            "content": {
                "application/json": {
                    "example": {"detail": "File too large (60000000 bytes). Maximum size is 52428800 bytes (50.0 MB)."}
                }
            }
        }
    }
)
async def upload_pdf(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="PDF file to process (max 50MB, 100 pages)"),
    settings: Settings = Depends(get_settings),
) -> UploadResponse:
    """Upload a PDF file for AI-powered summarization."""
    store = get_memory_store()

    # ========================================
    # Validation
    # ========================================

    # Check file extension
    if not settings.is_file_allowed(file.filename):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed extensions: {settings.allowed_extensions}",
        )

    # Check file size
    # Note: file.size might not be available, so we'll check during save
    file_path = None

    try:
        # ========================================
        # Save File
        # ========================================

        task_id = str(uuid.uuid4())

        file_path = await save_upload_file(
            file=file, upload_dir=str(settings.upload_dir), task_id=task_id
        )

        file_size = get_file_size(file_path)

        # Check size after saving
        if file_size > settings.max_file_size:
            # Delete the file
            Path(file_path).unlink(missing_ok=True)
            raise HTTPException(
                status_code=413,
                detail=f"File too large ({file_size} bytes). "
                f"Maximum size is {settings.max_file_size} bytes ({settings.max_file_size / 1024 / 1024:.1f} MB).",
            )

        logger.info(f"File uploaded: {file.filename} ({file_size} bytes) -> {file_path}")

        # ========================================
        # Create Task
        # ========================================

        task_data = TaskData(
            task_id=task_id,
            filename=file.filename,
            file_path=file_path,
            file_size=file_size,
            status=TaskStatusEnum.PROCESSING,
            progress=0,
        )

        await store.create_task(task_data)

        # ========================================
        # Add Background Task
        # ========================================

        background_tasks.add_task(
            process_pdf_task,
            task_id=task_id,
            file_path=file_path,
            filename=file.filename,
            file_size=file_size,
        )

        log_msg = f"📤 Background task queued for {task_id}"
        logger.info(log_msg)
        print(log_msg, flush=True)

        return UploadResponse(
            task_id=task_id,
            status=TaskStatusEnum.PROCESSING,
            message="PDF uploaded successfully. Processing started.",
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Upload error: {e}", exc_info=True)
        # Clean up file if it was saved
        if file_path:
            try:
                Path(file_path).unlink(missing_ok=True)
            except Exception:
                pass
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.get(
    "/status/{task_id}",
    response_model=TaskStatusResponse,
    summary="Check Processing Status",
    description="""
    Poll the processing status of a task using its task_id.

    **Status values:**
    - `processing` - Task is being processed (includes progress 0-100%)
    - `completed` - Task completed successfully (result available)
    - `failed` - Task failed (error message available)

    **Polling recommendation:**
    Poll every 5-10 seconds until status changes to `completed` or `failed`.
    For large PDFs (50+ pages), processing can take several minutes.
    """,
    responses={
        200: {
            "description": "Task status retrieved successfully",
            "content": {
                "application/json": {
                    "examples": {
                        "processing": {
                            "summary": "Task in progress",
                            "value": {
                                "task_id": "550e8400-e29b-41d4-a716-446655440000",
                                "status": "processing",
                                "progress": 45,
                                "result": None,
                                "error": None
                            }
                        },
                        "completed": {
                            "summary": "Task completed",
                            "value": {
                                "task_id": "550e8400-e29b-41d4-a716-446655440000",
                                "status": "completed",
                                "progress": 100,
                                "result": {
                                    "filename": "document.pdf",
                                    "summary": "This document discusses...",
                                    "page_count": 25,
                                    "file_size": 5242880,
                                    "processed_at": "2025-12-15T14:30:00Z"
                                },
                                "error": None
                            }
                        },
                        "failed": {
                            "summary": "Task failed",
                            "value": {
                                "task_id": "550e8400-e29b-41d4-a716-446655440000",
                                "status": "failed",
                                "progress": 30,
                                "result": None,
                                "error": "PDF processing error: Corrupted file"
                            }
                        }
                    }
                }
            }
        },
        404: {
            "description": "Task not found",
            "content": {
                "application/json": {
                    "example": {"detail": "Task 550e8400-e29b-41d4-a716-446655440000 not found"}
                }
            }
        }
    }
)
async def get_task_status(
    task_id: str = PathParam(..., description="Task ID returned from upload endpoint")
) -> TaskStatusResponse:
    """Get the current processing status and result of a task."""
    store = get_memory_store()

    task = await store.get_task(task_id)

    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    return TaskStatusResponse(
        task_id=task.task_id,
        status=task.status,
        progress=task.progress,
        result=task.result,
        error=task.error,
    )


@router.get("/history", response_model=HistoryResponse)
async def get_history() -> HistoryResponse:
    """
    Get the history of processed documents.

    Returns last 5 processed documents, sorted by most recent first.

    Returns:
        HistoryResponse with list of documents and total count
    """
    store = get_memory_store()

    history = await store.get_history()

    return HistoryResponse(documents=history, total=len(history))


@router.get("/stats")
async def get_stats():
    """
    Get storage statistics (for monitoring/debugging).

    Returns:
        Dictionary with task and history statistics
    """
    store = get_memory_store()
    stats = await store.get_stats()
    return stats