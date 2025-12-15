"""
In-memory storage for task status and document history.

Thread-safe storage using asyncio locks for concurrent access.
"""

import asyncio
from typing import Dict, List, Optional
from datetime import datetime

from app.models import TaskData, ProcessingResult, DocumentHistory
from app.config import get_settings


class MemoryStore:
    """Thread-safe in-memory storage for tasks and history."""

    def __init__(self):
        """Initialize storage with empty dictionaries."""
        self._tasks: Dict[str, TaskData] = {}
        self._history: List[DocumentHistory] = []
        self._lock = asyncio.Lock()
        self._settings = get_settings()

    async def create_task(self, task_data: TaskData) -> None:
        """
        Create a new task in storage.

        Args:
            task_data: Task data to store
        """
        async with self._lock:
            self._tasks[task_data.task_id] = task_data

    async def get_task(self, task_id: str) -> Optional[TaskData]:
        """
        Retrieve task by ID.

        Args:
            task_id: Task identifier

        Returns:
            TaskData if found, None otherwise
        """
        async with self._lock:
            return self._tasks.get(task_id)

    async def update_task(self, task_id: str, **updates) -> bool:
        """
        Update task fields.

        Args:
            task_id: Task identifier
            **updates: Fields to update

        Returns:
            True if task was updated, False if not found
        """
        async with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return False

            for key, value in updates.items():
                if hasattr(task, key):
                    setattr(task, key, value)

            task.updated_at = datetime.utcnow()
            return True

    async def update_task_progress(
        self,
        task_id: str,
        progress: int,
        status: Optional[str] = None
    ) -> bool:
        """
        Update task progress and optionally status.

        Args:
            task_id: Task identifier
            progress: Progress percentage (0-100)
            status: Optional status update

        Returns:
            True if updated, False if task not found
        """
        async with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return False

            task.update_progress(progress, status)
            return True

    async def complete_task(
        self,
        task_id: str,
        result: ProcessingResult
    ) -> bool:
        """
        Mark task as completed and add to history.

        Args:
            task_id: Task identifier
            result: Processing result

        Returns:
            True if task was completed, False if not found
        """
        async with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return False

            # Update task
            task.complete(result)

            # Add to history
            history_item = DocumentHistory(
                task_id=task_id,
                filename=result.filename,
                summary=result.summary,
                page_count=result.page_count,
                processed_at=result.processed_at
            )

            self._history.insert(0, history_item)  # Add to beginning

            # Trim history to max size
            max_size = self._settings.max_history_size
            if len(self._history) > max_size:
                self._history = self._history[:max_size]

            return True

    async def fail_task(self, task_id: str, error: str) -> bool:
        """
        Mark task as failed.

        Args:
            task_id: Task identifier
            error: Error message

        Returns:
            True if task was failed, False if not found
        """
        async with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return False

            task.fail(error)
            return True

    async def get_history(self, limit: Optional[int] = None) -> List[DocumentHistory]:
        """
        Get document history.

        Args:
            limit: Optional limit on number of documents to return

        Returns:
            List of historical documents
        """
        async with self._lock:
            if limit:
                return self._history[:limit]
            return self._history.copy()

    async def get_all_tasks(self) -> Dict[str, TaskData]:
        """
        Get all tasks (for debugging/monitoring).

        Returns:
            Dictionary of all tasks
        """
        async with self._lock:
            return self._tasks.copy()

    async def clear_completed_tasks(self, max_age_hours: int = 24) -> int:
        """
        Clear completed tasks older than specified age.

        Args:
            max_age_hours: Maximum age in hours for completed tasks

        Returns:
            Number of tasks cleared
        """
        async with self._lock:
            now = datetime.utcnow()
            tasks_to_remove = []

            for task_id, task in self._tasks.items():
                if task.status in ["completed", "failed"]:
                    age_hours = (now - task.updated_at).total_seconds() / 3600
                    if age_hours > max_age_hours:
                        tasks_to_remove.append(task_id)

            for task_id in tasks_to_remove:
                del self._tasks[task_id]

            return len(tasks_to_remove)

    async def get_stats(self) -> Dict:
        """
        Get storage statistics.

        Returns:
            Dictionary with storage stats
        """
        async with self._lock:
            stats = {
                "total_tasks": len(self._tasks),
                "processing_tasks": sum(
                    1 for t in self._tasks.values()
                    if t.status == "processing"
                ),
                "completed_tasks": sum(
                    1 for t in self._tasks.values()
                    if t.status == "completed"
                ),
                "failed_tasks": sum(
                    1 for t in self._tasks.values()
                    if t.status == "failed"
                ),
                "history_size": len(self._history),
                "max_history_size": self._settings.max_history_size
            }
            return stats


# Global singleton instance
_store: Optional[MemoryStore] = None


def get_memory_store() -> MemoryStore:
    """
    Get or create the global memory store instance.

    Returns:
        MemoryStore singleton instance
    """
    global _store
    if _store is None:
        _store = MemoryStore()
    return _store
