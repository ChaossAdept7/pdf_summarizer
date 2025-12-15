"""
File storage utilities for handling PDF uploads and temporary files.

Provides secure file handling with validation and sanitization.
"""

import os
import uuid
import aiofiles
from pathlib import Path
from typing import Tuple
from fastapi import UploadFile, HTTPException

from app.config import get_settings


class FileStorage:
    """Secure file storage handler."""

    def __init__(self):
        """Initialize file storage with settings."""
        self._settings = get_settings()

    def _sanitize_filename(self, filename: str) -> str:
        """
        Sanitize filename to prevent directory traversal attacks.

        Args:
            filename: Original filename

        Returns:
            Sanitized filename
        """
        # Remove directory components
        filename = os.path.basename(filename)

        # Remove any non-alphanumeric characters except dots, hyphens, underscores
        safe_chars = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-_")
        filename = ''.join(c if c in safe_chars else '_' for c in filename)

        # Ensure filename is not empty
        if not filename or filename == '.':
            filename = "unnamed.pdf"

        return filename

    def _generate_unique_filename(self, original_filename: str) -> str:
        """
        Generate unique filename to prevent collisions.

        Args:
            original_filename: Original filename

        Returns:
            Unique filename with UUID prefix
        """
        sanitized = self._sanitize_filename(original_filename)
        unique_id = uuid.uuid4().hex[:8]
        name, ext = os.path.splitext(sanitized)
        return f"{unique_id}_{name}{ext}"

    def validate_file(self, file: UploadFile) -> None:
        """
        Validate uploaded file.

        Args:
            file: Uploaded file

        Raises:
            HTTPException: If file is invalid
        """
        # Check if file exists
        if not file:
            raise HTTPException(status_code=400, detail="No file uploaded")

        # Check if filename exists
        if not file.filename:
            raise HTTPException(status_code=400, detail="Filename is required")

        # Check file extension
        if not self._settings.is_file_allowed(file.filename):
            allowed = ", ".join(self._settings.allowed_extensions)
            raise HTTPException(
                status_code=400,
                detail=f"File type not allowed. Allowed types: {allowed}"
            )

        # Check content type (optional, can be spoofed)
        if file.content_type and not file.content_type.startswith("application/pdf"):
            raise HTTPException(
                status_code=400,
                detail="Invalid content type. Expected application/pdf"
            )

    async def save_upload(
        self,
        file: UploadFile,
        directory: Path
    ) -> Tuple[str, str, int]:
        """
        Save uploaded file to disk.

        Args:
            file: Uploaded file
            directory: Target directory

        Returns:
            Tuple of (file_path, sanitized_filename, file_size)

        Raises:
            HTTPException: If file is too large or save fails
        """
        # Validate file
        self.validate_file(file)

        # Generate unique filename
        unique_filename = self._generate_unique_filename(file.filename)
        file_path = directory / unique_filename

        # Save file and track size
        file_size = 0
        chunk_size = 8192  # 8KB chunks

        try:
            async with aiofiles.open(file_path, 'wb') as f:
                while chunk := await file.read(chunk_size):
                    file_size += len(chunk)

                    # Check file size limit
                    if file_size > self._settings.max_file_size:
                        # Delete partially written file
                        await self.delete_file(file_path)
                        max_mb = self._settings.max_file_size / (1024 * 1024)
                        raise HTTPException(
                            status_code=413,
                            detail=f"File too large. Maximum size is {max_mb:.0f}MB"
                        )

                    await f.write(chunk)

        except HTTPException:
            raise
        except Exception as e:
            # Clean up on error
            if file_path.exists():
                await self.delete_file(file_path)
            raise HTTPException(
                status_code=500,
                detail=f"Failed to save file: {str(e)}"
            )

        return str(file_path), unique_filename, file_size

    async def delete_file(self, file_path: Path | str) -> bool:
        """
        Delete a file from disk.

        Args:
            file_path: Path to file

        Returns:
            True if deleted, False if file didn't exist
        """
        try:
            path = Path(file_path)
            if path.exists() and path.is_file():
                path.unlink()
                return True
            return False
        except Exception:
            return False

    async def delete_files(self, file_paths: list[Path | str]) -> int:
        """
        Delete multiple files.

        Args:
            file_paths: List of file paths

        Returns:
            Number of files deleted
        """
        count = 0
        for file_path in file_paths:
            if await self.delete_file(file_path):
                count += 1
        return count

    async def cleanup_temp_files(self, pattern: str = "*") -> int:
        """
        Clean up temporary files matching pattern.

        Args:
            pattern: Glob pattern for files to delete

        Returns:
            Number of files deleted
        """
        temp_dir = Path(self._settings.temp_dir)
        files_deleted = 0

        try:
            for file_path in temp_dir.glob(pattern):
                if file_path.is_file():
                    if await self.delete_file(file_path):
                        files_deleted += 1
        except Exception:
            pass

        return files_deleted

    def get_file_size(self, file_path: Path | str) -> int:
        """
        Get file size in bytes.

        Args:
            file_path: Path to file

        Returns:
            File size in bytes, 0 if file doesn't exist
        """
        try:
            path = Path(file_path)
            if path.exists() and path.is_file():
                return path.stat().st_size
            return 0
        except Exception:
            return 0

    def file_exists(self, file_path: Path | str) -> bool:
        """
        Check if file exists.

        Args:
            file_path: Path to file

        Returns:
            True if file exists, False otherwise
        """
        try:
            path = Path(file_path)
            return path.exists() and path.is_file()
        except Exception:
            return False


# Global singleton instance
_file_storage: FileStorage | None = None


def get_file_storage() -> FileStorage:
    """
    Get or create the global file storage instance.

    Returns:
        FileStorage singleton instance
    """
    global _file_storage
    if _file_storage is None:
        _file_storage = FileStorage()
    return _file_storage


# ========================================
# Convenience Functions
# ========================================


async def save_upload_file(
    file: UploadFile,
    upload_dir: str,
    task_id: str
) -> str:
    """
    Save uploaded file to upload directory.

    Args:
        file: Uploaded file
        upload_dir: Upload directory path
        task_id: Task ID (for logging)

    Returns:
        Path to saved file

    Raises:
        HTTPException: If save fails
    """
    storage = get_file_storage()
    directory = Path(upload_dir)
    directory.mkdir(parents=True, exist_ok=True)

    file_path, _, file_size = await storage.save_upload(file, directory)
    return file_path


def get_file_size(file_path: str) -> int:
    """
    Get file size in bytes.

    Args:
        file_path: Path to file

    Returns:
        File size in bytes
    """
    storage = get_file_storage()
    return storage.get_file_size(file_path)
