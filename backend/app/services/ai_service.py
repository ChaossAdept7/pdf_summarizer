"""
OpenAI Vision API integration service for PDF text extraction and summarization.

This module handles:
- Converting images to base64
- Extracting text from PDF page images using Vision API
- Generating summaries from extracted text
"""

import asyncio
import base64
import logging
from pathlib import Path
from typing import List, Optional

from openai import AsyncOpenAI, OpenAIError, RateLimitError

from app.config import get_settings

logger = logging.getLogger(__name__)


class AIServiceError(Exception):
    """Exception raised for AI service errors."""
    pass


def encode_image_to_base64(image_path: str) -> str:
    """
    Encode image file to base64 string.

    Args:
        image_path: Path to the image file

    Returns:
        Base64 encoded string of the image

    Raises:
        AIServiceError: If image cannot be encoded
    """
    try:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode("utf-8")
    except Exception as e:
        logger.error(f"Failed to encode image {image_path}: {e}")
        raise AIServiceError(f"Failed to encode image: {str(e)}")


async def extract_text_from_image(
    client: AsyncOpenAI,
    image_path: str,
    page_number: int,
    max_retries: int = 3
) -> str:
    """
    Extract text from a single PDF page image using OpenAI Vision API.

    Args:
        client: OpenAI async client
        image_path: Path to the image file
        page_number: Page number (for logging)
        max_retries: Maximum number of retry attempts for rate limits

    Returns:
        Extracted text from the image

    Raises:
        AIServiceError: If text extraction fails
    """
    settings = get_settings()

    try:
        logger.info(f"Extracting text from page {page_number}...")

        # Encode image to base64
        base64_image = encode_image_to_base64(image_path)

        # Get image format from file extension
        image_format = Path(image_path).suffix.lstrip(".")
        if image_format == "jpg":
            image_format = "jpeg"

        # Prepare vision API request
        prompt = (
            "You are analyzing a page from a document. Please read and transcribe ALL the text content you can see in this image. "
            "Do not provide advice about OCR tools or text extraction methods. "
            "Simply read the content and provide the actual text that appears on this page. "
            "Include headings, paragraphs, bullet points, tables, captions, and any other visible text. "
            "Organize the output to maintain the document's structure. "
            "If you cannot read some text clearly, indicate this but still provide what you can see."
        )

        # Retry logic for rate limits
        for attempt in range(max_retries):
            try:
                response = await client.chat.completions.create(
                    model=settings.openai_model,
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt},
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/{image_format};base64,{base64_image}",
                                        "detail": settings.vision_detail_level
                                    }
                                }
                            ]
                        }
                    ],
                    max_tokens=settings.openai_max_tokens,
                    temperature=settings.openai_temperature,
                )

                extracted_text = response.choices[0].message.content
                logger.info(f"Successfully extracted text from page {page_number}")

                return extracted_text or ""

            except RateLimitError as e:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                    logger.warning(
                        f"Rate limit hit on page {page_number}, "
                        f"retrying in {wait_time}s (attempt {attempt + 1}/{max_retries})"
                    )
                    await asyncio.sleep(wait_time)
                else:
                    raise AIServiceError(f"Rate limit exceeded after {max_retries} retries: {str(e)}")

    except AIServiceError:
        raise

    except OpenAIError as e:
        logger.error(f"OpenAI API error on page {page_number}: {e}")
        raise AIServiceError(f"OpenAI API error: {str(e)}")

    except Exception as e:
        logger.error(f"Failed to extract text from page {page_number}: {e}")
        raise AIServiceError(f"Failed to extract text: {str(e)}")


async def process_all_pages(
    image_paths: List[str],
    progress_callback: Optional[callable] = None
) -> str:
    """
    Extract text from all PDF page images.

    Args:
        image_paths: List of image file paths
        progress_callback: Optional callback function to report progress
                          (called with current page number and total pages)

    Returns:
        Combined text from all pages

    Raises:
        AIServiceError: If processing fails
    """
    settings = get_settings()
    client = AsyncOpenAI(api_key=settings.openai_api_key)

    try:
        logger.info(f"Processing {len(image_paths)} pages with Vision API...")

        all_text = []

        # Process pages sequentially to avoid rate limits
        # (Can be changed to parallel processing with concurrency limit if needed)
        for idx, image_path in enumerate(image_paths):
            page_number = idx + 1

            # Extract text from page
            text = await extract_text_from_image(
                client=client,
                image_path=image_path,
                page_number=page_number
            )

            all_text.append(f"--- Page {page_number} ---\n{text}\n")

            # Report progress if callback provided
            if progress_callback:
                progress_callback(page_number, len(image_paths))

        # Combine all text
        combined_text = "\n\n".join(all_text)

        logger.info(f"Successfully extracted text from {len(image_paths)} pages")
        logger.info(f"Total extracted text length: {len(combined_text)} characters")

        return combined_text

    except Exception as e:
        logger.error(f"Failed to process all pages: {e}")
        raise AIServiceError(f"Failed to process pages: {str(e)}")


async def generate_summary(full_text: str) -> str:
    """
    Generate a summary of the extracted text using OpenAI.

    Args:
        full_text: Complete extracted text from all pages

    Returns:
        AI-generated summary

    Raises:
        AIServiceError: If summary generation fails
    """
    settings = get_settings()
    client = AsyncOpenAI(api_key=settings.openai_api_key)

    try:
        logger.info("Generating summary from extracted text...")

        # Check if text is too short
        if len(full_text.strip()) < 50:
            logger.warning("Extracted text is very short, returning as-is")
            return full_text.strip() or "No text could be extracted from the PDF."

        prompt = (
            "Please provide a comprehensive summary of the following document. "
            "Focus on:\n"
            "1. Main topics and key points\n"
            "2. Important findings or conclusions\n"
            "3. Significant data or statistics if present\n"
            "4. Overall purpose and context of the document\n\n"
            "Make the summary clear, concise, and well-structured.\n\n"
            f"Document content:\n\n{full_text}"
        )

        response = await client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a helpful assistant that creates clear, "
                        "comprehensive summaries of documents. "
                        "Focus on extracting the most important information "
                        "and presenting it in an organized way."
                    )
                },
                {"role": "user", "content": prompt}
            ],
            max_tokens=settings.openai_max_tokens,
            temperature=settings.openai_temperature,
        )

        summary = response.choices[0].message.content

        logger.info(f"Successfully generated summary ({len(summary)} characters)")

        return summary or "Failed to generate summary."

    except OpenAIError as e:
        logger.error(f"OpenAI API error during summary generation: {e}")
        raise AIServiceError(f"Failed to generate summary: {str(e)}")

    except Exception as e:
        logger.error(f"Failed to generate summary: {e}")
        raise AIServiceError(f"Failed to generate summary: {str(e)}")


async def process_pdf_complete(
    image_paths: List[str],
    progress_callback: Optional[callable] = None
) -> dict:
    """
    Complete PDF processing: extract text and generate summary.

    Args:
        image_paths: List of image file paths
        progress_callback: Optional callback for progress updates

    Returns:
        dict with keys:
            - full_text: Complete extracted text
            - summary: AI-generated summary

    Raises:
        AIServiceError: If processing fails
    """
    try:
        # Extract text from all pages
        full_text = await process_all_pages(image_paths, progress_callback)

        # Generate summary
        summary = await generate_summary(full_text)

        return {
            "full_text": full_text,
            "summary": summary
        }

    except Exception as e:
        logger.error(f"Complete PDF processing failed: {e}")
        raise AIServiceError(f"PDF processing failed: {str(e)}")