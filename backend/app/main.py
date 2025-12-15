"""
PDF Summarizer API - Main Application

FastAPI application for processing PDFs and generating AI summaries.
"""

import logging
import shutil
import sys
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import get_settings
from app.models import HealthResponse, ErrorResponse


# ========================================
# Logging Configuration
# ========================================

def configure_logging():
    """
    Configure Python logging to output to stdout for Docker.

    This ensures all logger.info/warning/error calls are visible in Docker logs.
    """
    settings = get_settings()

    # Create formatter
    log_format = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"
    formatter = logging.Formatter(log_format, date_format)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.log_level.upper()))

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Add stdout handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Set level for app loggers
    logging.getLogger("app").setLevel(getattr(logging, settings.log_level.upper()))

    # Silence noisy libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)

    root_logger.info("Logging configured successfully")


# Configure logging at module load time
configure_logging()


# ========================================
# Cleanup Functions
# ========================================

def cleanup_directory(directory: Path, directory_name: str) -> None:
    """
    Clean up all files in a directory.
    
    Args:
        directory: Path to the directory to clean
        directory_name: Name of the directory (for logging)
    """
    try:
        if directory.exists():
            # Remove all files and subdirectories
            for item in directory.iterdir():
                if item.is_file():
                    item.unlink()
                    print(f"🗑️  Deleted file: {item}")
                elif item.is_dir():
                    shutil.rmtree(item)
                    print(f"🗑️  Deleted directory: {item}")
            print(f"✅ Cleaned up {directory_name} directory: {directory}")
        else:
            print(f"⚠️  {directory_name} directory does not exist: {directory}")
    except Exception as e:
        print(f"❌ Error cleaning up {directory_name} directory {directory}: {e}")


# ========================================
# Application Lifespan
# ========================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.

    Handles startup and shutdown events.
    """
    # Startup
    settings = get_settings()
    print(f"🚀 Starting {settings.app_name} v{settings.app_version}")
    print(f"📁 Upload directory: {settings.upload_dir}")
    print(f"📁 Temp directory: {settings.temp_dir}")
    print(f"🔧 Debug mode: {settings.debug}")

    yield

    # Shutdown
    print("👋 Shutting down application")
    print("🧹 Cleaning up files...")
    
    # Clean up uploads and temp directories
    cleanup_directory(settings.upload_dir, "uploads")
    cleanup_directory(settings.temp_dir, "temp")
    
    print("✅ Cleanup completed")


# ========================================
# FastAPI Application
# ========================================

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="A FastAPI application for processing PDFs and generating AI-powered summaries using OpenAI Vision API.",
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,  # Disable docs in production
    redoc_url="/redoc" if settings.debug else None,
)

# ========================================
# Middleware
# ========================================

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ========================================
# Exception Handlers
# ========================================

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            detail=exc.detail,
            error_code=f"HTTP_{exc.status_code}"
        ).dict()
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle request validation errors."""
    errors = exc.errors()
    error_details = []

    for error in errors:
        field = " -> ".join(str(loc) for loc in error["loc"])
        error_details.append(f"{field}: {error['msg']}")

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=ErrorResponse(
            detail="; ".join(error_details),
            error_code="VALIDATION_ERROR"
        ).dict()
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle all other exceptions."""
    # Log the error (in production, use proper logging)
    if settings.debug:
        error_detail = f"{type(exc).__name__}: {str(exc)}"
    else:
        error_detail = "An internal error occurred. Please try again later."

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            detail=error_detail,
            error_code="INTERNAL_ERROR"
        ).dict()
    )


# ========================================
# Root Endpoints
# ========================================

@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with API information."""
    return {
        "message": "PDF Summarizer API",
        "version": settings.app_version,
        "docs": "/docs" if settings.debug else "Documentation disabled in production",
        "health": "/health"
    }


@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["Health"],
    summary="Health check endpoint"
)
async def health_check():
    """
    Check if the API is healthy and running.

    Returns service status and version information.
    """
    return HealthResponse(
        status="healthy",
        version=settings.app_version,
        timestamp=datetime.utcnow()
    )


# ========================================
# API Routes
# ========================================

# Import and include API routes
from app.api.routes import router as api_router
app.include_router(api_router)


# ========================================
# Application Entry Point
# ========================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )
