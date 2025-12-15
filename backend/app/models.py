"""
Pydantic models for request/response validation and data structures.
"""

from datetime import datetime
from enum import Enum
from typing import Optional, List

from pydantic import BaseModel, Field, field_validator


class TaskStatusEnum(str, Enum):
    """Task processing status."""
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class UploadResponse(BaseModel):
    """Response model for PDF upload endpoint."""
    task_id: str = Field(..., description="Unique task identifier for tracking")
    status: TaskStatusEnum = Field(..., description="Current task status")
    message: str = Field(..., description="Human-readable status message")

    class Config:
        json_schema_extra = {
            "example": {
                "task_id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "processing",
                "message": "PDF uploaded successfully. Processing started."
            }
        }


class ProcessingResult(BaseModel):
    """Result of PDF processing."""
    filename: str = Field(..., description="Original filename")
    summary: str = Field(..., description="AI-generated summary")
    page_count: int = Field(..., description="Number of pages in PDF")
    processed_at: datetime = Field(..., description="Processing completion timestamp")
    file_size: Optional[int] = Field(None, description="File size in bytes")

    class Config:
        json_schema_extra = {
            "example": {
                "filename": "document.pdf",
                "summary": "This document discusses the quarterly financial results...",
                "page_count": 25,
                "processed_at": "2025-12-14T10:30:00Z",
                "file_size": 2048576
            }
        }


class TaskStatusResponse(BaseModel):
    """Response model for task status endpoint."""
    task_id: str = Field(..., description="Task identifier")
    status: TaskStatusEnum = Field(..., description="Current processing status")
    progress: int = Field(..., ge=0, le=100, description="Progress percentage (0-100)")
    result: Optional[ProcessingResult] = Field(None, description="Processing result if completed")
    error: Optional[str] = Field(None, description="Error message if failed")

    @field_validator("progress")
    @classmethod
    def validate_progress(cls, v: int) -> int:
        """Ensure progress is between 0 and 100."""
        return max(0, min(100, v))

    class Config:
        json_schema_extra = {
            "example": {
                "task_id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "completed",
                "progress": 100,
                "result": {
                    "filename": "document.pdf",
                    "summary": "This document discusses...",
                    "page_count": 25,
                    "processed_at": "2025-12-14T10:30:00Z",
                    "file_size": 2048576
                },
                "error": None
            }
        }


class DocumentHistory(BaseModel):
    """Single document in history."""
    task_id: str = Field(..., description="Task identifier")
    filename: str = Field(..., description="Original filename")
    summary: str = Field(..., description="AI-generated summary")
    page_count: int = Field(..., description="Number of pages")
    processed_at: datetime = Field(..., description="Processing timestamp")


class HistoryResponse(BaseModel):
    """Response model for history endpoint."""
    documents: List[DocumentHistory] = Field(..., description="List of processed documents")
    total: int = Field(..., description="Total number of documents in history")

    class Config:
        json_schema_extra = {
            "example": {
                "documents": [
                    {
                        "task_id": "550e8400-e29b-41d4-a716-446655440000",
                        "filename": "report.pdf",
                        "summary": "Quarterly financial report showing...",
                        "page_count": 10,
                        "processed_at": "2025-12-14T10:30:00Z"
                    }
                ],
                "total": 1
            }
        }


class HealthResponse(BaseModel):
    """Response model for health check endpoint."""
    status: str = Field(..., description="Service health status")
    version: str = Field(..., description="Application version")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Current server time")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "version": "1.0.0",
                "timestamp": "2025-12-14T10:30:00Z"
            }
        }


class ErrorResponse(BaseModel):
    """Standard error response model."""
    detail: str = Field(..., description="Error description")
    error_code: Optional[str] = Field(None, description="Machine-readable error code")

    class Config:
        json_schema_extra = {
            "example": {
                "detail": "File too large. Maximum size is 50MB.",
                "error_code": "FILE_TOO_LARGE"
            }
        }


# ========================================
# Internal Models (not exposed in API)
# ========================================

class TaskData(BaseModel):
    """Internal model for task storage."""
    task_id: str
    filename: str
    file_path: str
    file_size: int
    status: TaskStatusEnum
    progress: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    result: Optional[ProcessingResult] = None
    error: Optional[str] = None

    def update_progress(self, progress: int, status: Optional[TaskStatusEnum] = None):
        """Update task progress and optionally status."""
        self.progress = max(0, min(100, progress))
        if status:
            self.status = status
        self.updated_at = datetime.utcnow()

    def complete(self, result: ProcessingResult):
        """Mark task as completed with result."""
        self.status = TaskStatusEnum.COMPLETED
        self.progress = 100
        self.result = result
        self.updated_at = datetime.utcnow()

    def fail(self, error: str):
        """Mark task as failed with error message."""
        self.status = TaskStatusEnum.FAILED
        self.error = error
        self.updated_at = datetime.utcnow()
