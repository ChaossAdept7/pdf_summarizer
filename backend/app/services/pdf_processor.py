"""
PDF processing service for converting PDFs to images.

This module handles PDF to image conversion using pdf2image and
extracts metadata using PyPDF2.
"""

import asyncio
import logging
from pathlib import Path
from typing import List, Tuple
import uuid

from pdf2image import convert_from_path
from PyPDF2 import PdfReader

from app.config import get_settings

logger = logging.getLogger(__name__)


class PDFProcessingError(Exception):
    """Exception raised for PDF processing errors."""
    pass


async def get_pdf_metadata(pdf_path: str) -> dict:
    """
    Extract metadata from PDF file.

    Args:
        pdf_path: Path to the PDF file

    Returns:
        dict: PDF metadata including page count

    Raises:
        PDFProcessingError: If PDF cannot be read
    """
    try:
        # Run synchronous PDF reading in thread pool
        def read_pdf():
            reader = PdfReader(pdf_path)
            return {
                "page_count": len(reader.pages),
                "metadata": reader.metadata,
            }

        return await asyncio.to_thread(read_pdf)

    except Exception as e:
        logger.error(f"Failed to read PDF metadata: {e}")
        raise PDFProcessingError(f"Failed to read PDF metadata: {str(e)}")


async def convert_pdf_to_images(
    pdf_path: str,
    output_dir: str,
    dpi: int = 200,
    image_format: str = "png"
) -> Tuple[List[str], int]:
    """
    Convert PDF pages to images.

    Args:
        pdf_path: Path to the PDF file
        output_dir: Directory to save images
        dpi: Image resolution (default: 200)
        image_format: Image format - 'png' or 'jpg' (default: 'png')

    Returns:
        Tuple of (list of image paths, page count)

    Raises:
        PDFProcessingError: If PDF cannot be converted
    """
    settings = get_settings()

    try:
        logger.info(f"Starting PDF to image conversion: {pdf_path}")

        # Create output directory if it doesn't exist
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Get page count first
        metadata = await get_pdf_metadata(pdf_path)
        page_count = metadata["page_count"]

        logger.info(f"Converting {page_count} pages to images...")

        # Validate page count
        if page_count > settings.max_pages:
            raise PDFProcessingError(
                f"PDF has {page_count} pages, exceeds maximum of {settings.max_pages}"
            )

        # Convert PDF to images (run in thread pool as it's CPU-intensive)
        def convert_pages():
            return convert_from_path(
                pdf_path,
                dpi=dpi,
                fmt=image_format,
                output_folder=output_dir,
                paths_only=False  # Return PIL images
            )

        images = await asyncio.to_thread(convert_pages)

        # Save images and collect paths
        image_paths = []
        task_id = uuid.uuid4().hex[:8]  # Short unique ID for this conversion

        def save_image(idx, image):
            image_filename = f"page_{task_id}_{idx + 1}.{image_format}"
            image_path = output_path / image_filename
            image.save(image_path, image_format.upper())
            return str(image_path)

        # Save all images in thread pool
        save_tasks = [
            asyncio.to_thread(save_image, idx, img)
            for idx, img in enumerate(images)
        ]
        image_paths = await asyncio.gather(*save_tasks)

        logger.info(f"Successfully converted {len(image_paths)} pages to images")

        return image_paths, page_count

    except PDFProcessingError:
        raise

    except FileNotFoundError as e:
        logger.error(f"PDF file not found: {pdf_path}")
        raise PDFProcessingError(f"PDF file not found: {str(e)}")

    except Exception as e:
        logger.error(f"Failed to convert PDF to images: {e}")
        # Check if poppler is missing
        if "poppler" in str(e).lower():
            raise PDFProcessingError(
                "poppler-utils not installed. "
                "Install with: brew install poppler (macOS) or "
                "apt-get install poppler-utils (Ubuntu)"
            )
        raise PDFProcessingError(f"Failed to convert PDF to images: {str(e)}")


async def cleanup_temp_images(image_paths: List[str]) -> None:
    """
    Delete temporary image files.

    Args:
        image_paths: List of image file paths to delete
    """
    try:
        def delete_file(path: str):
            try:
                Path(path).unlink(missing_ok=True)
            except Exception as e:
                logger.warning(f"Failed to delete temp file {path}: {e}")

        # Delete files in parallel
        delete_tasks = [asyncio.to_thread(delete_file, path) for path in image_paths]
        await asyncio.gather(*delete_tasks, return_exceptions=True)

        logger.info(f"Cleaned up {len(image_paths)} temporary image files")

    except Exception as e:
        logger.error(f"Error during cleanup: {e}")