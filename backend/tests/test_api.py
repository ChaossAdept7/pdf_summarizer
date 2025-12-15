"""
Integration tests for API endpoints.

Tests cover:
- POST /api/v1/upload - Upload endpoint
- GET /api/v1/status/{task_id} - Status endpoint
- GET /api/v1/history - History endpoint
- File validation and error handling
"""

import pytest
import io
from pathlib import Path
from unittest.mock import patch, AsyncMock, MagicMock
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.storage.memory_store import get_memory_store


@pytest.fixture
def sample_pdf_bytes():
    """Create a minimal valid PDF for testing."""
    # Minimal PDF structure
    pdf_content = b"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj
2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj
3 0 obj
<<
/Type /Page
/Parent 2 0 R
/Resources <<
/Font <<
/F1 <<
/Type /Font
/Subtype /Type1
/BaseFont /Times-Roman
>>
>>
>>
/MediaBox [0 0 612 792]
/Contents 4 0 R
>>
endobj
4 0 obj
<<
/Length 44
>>
stream
BT
/F1 12 Tf
100 700 Td
(Test PDF) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000315 00000 n
trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
408
%%EOF
"""
    return pdf_content


@pytest.fixture
async def client():
    """Create an async HTTP client for testing."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest.fixture(autouse=True)
async def clear_memory_store():
    """Clear memory store before each test."""
    store = get_memory_store()
    store._tasks = {}
    store._history = []
    yield
    # Clean up after test
    store._tasks = {}
    store._history = []


# ========================================
# Health and Root Endpoint Tests
# ========================================


@pytest.mark.asyncio
async def test_health_endpoint(client):
    """Test health check endpoint."""
    response = await client.get("/health")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert "timestamp" in data


@pytest.mark.asyncio
async def test_root_endpoint(client):
    """Test root endpoint."""
    response = await client.get("/")
    assert response.status_code == 200

    data = response.json()
    assert data["message"] == "PDF Summarizer API"
    assert "version" in data
    assert data["docs"] == "/docs"


# ========================================
# Upload Endpoint Tests
# ========================================


@pytest.mark.asyncio
async def test_upload_pdf_success(client, sample_pdf_bytes, tmp_path):
    """Test successful PDF upload."""
    # Mock the background processing functions
    with patch("app.api.routes.convert_pdf_to_images") as mock_convert:
        with patch("app.api.routes.process_pdf_complete") as mock_process:
            mock_convert.return_value = (["/tmp/page1.png"], 1)
            mock_process.return_value = {"summary": "Test summary"}

            # Upload file
            files = {"file": ("test.pdf", io.BytesIO(sample_pdf_bytes), "application/pdf")}
            response = await client.post("/api/v1/upload", files=files)

            assert response.status_code == 200

            data = response.json()
            assert "task_id" in data
            assert data["status"] == "processing"
            assert data["message"] == "PDF uploaded successfully. Processing started."


@pytest.mark.asyncio
async def test_upload_invalid_file_type(client):
    """Test upload with invalid file type."""
    # Try to upload a non-PDF file
    files = {"file": ("test.txt", io.BytesIO(b"Not a PDF"), "text/plain")}
    response = await client.post("/api/v1/upload", files=files)

    assert response.status_code == 400
    assert "Invalid file type" in response.json()["detail"]


@pytest.mark.asyncio
async def test_upload_file_too_large(client, tmp_path):
    """Test upload with file exceeding size limit."""
    # Create a large file (>50MB)
    large_content = b"%PDF-1.4\n" + (b"x" * (51 * 1024 * 1024))

    files = {"file": ("large.pdf", io.BytesIO(large_content), "application/pdf")}
    response = await client.post("/api/v1/upload", files=files)

    assert response.status_code == 413
    assert "File too large" in response.json()["detail"]


@pytest.mark.asyncio
async def test_upload_no_file(client):
    """Test upload without providing a file."""
    response = await client.post("/api/v1/upload")

    assert response.status_code == 422  # Validation error


# ========================================
# Status Endpoint Tests
# ========================================


@pytest.mark.asyncio
async def test_status_processing(client):
    """Test status endpoint for processing task."""
    store = get_memory_store()

    # Create a task manually
    from app.models import TaskData, TaskStatusEnum

    task = TaskData(
        task_id="test-task-1",
        filename="test.pdf",
        file_path="/uploads/test.pdf",
        file_size=1024,
        status=TaskStatusEnum.PROCESSING,
        progress=50,
    )
    await store.create_task(task)

    response = await client.get("/api/v1/status/test-task-1")

    assert response.status_code == 200

    data = response.json()
    assert data["task_id"] == "test-task-1"
    assert data["status"] == "processing"
    assert data["progress"] == 50
    assert data["result"] is None
    assert data["error"] is None


@pytest.mark.asyncio
async def test_status_completed(client):
    """Test status endpoint for completed task."""
    store = get_memory_store()

    from app.models import TaskData, TaskStatusEnum, ProcessingResult
    from datetime import datetime

    # Create and complete a task
    task = TaskData(
        task_id="test-task-2",
        filename="test.pdf",
        file_path="/uploads/test.pdf",
        file_size=1024,
        status=TaskStatusEnum.PROCESSING,
        progress=0,
    )
    await store.create_task(task)

    result = ProcessingResult(
        filename="test.pdf",
        summary="This is a test summary",
        page_count=5,
        file_size=1024,
        processed_at=datetime.utcnow(),
    )
    await store.complete_task("test-task-2", result)

    response = await client.get("/api/v1/status/test-task-2")

    assert response.status_code == 200

    data = response.json()
    assert data["task_id"] == "test-task-2"
    assert data["status"] == "completed"
    assert data["progress"] == 100
    assert data["result"] is not None
    assert data["result"]["summary"] == "This is a test summary"
    assert data["result"]["page_count"] == 5


@pytest.mark.asyncio
async def test_status_failed(client):
    """Test status endpoint for failed task."""
    store = get_memory_store()

    from app.models import TaskData, TaskStatusEnum

    task = TaskData(
        task_id="test-task-3",
        filename="test.pdf",
        file_path="/uploads/test.pdf",
        file_size=1024,
        status=TaskStatusEnum.PROCESSING,
        progress=0,
    )
    await store.create_task(task)
    await store.fail_task("test-task-3", error="Processing failed")

    response = await client.get("/api/v1/status/test-task-3")

    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "failed"
    assert data["error"] == "Processing failed"


@pytest.mark.asyncio
async def test_status_not_found(client):
    """Test status endpoint for non-existent task."""
    response = await client.get("/api/v1/status/nonexistent-task-id")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


# ========================================
# History Endpoint Tests
# ========================================


@pytest.mark.asyncio
async def test_history_empty(client):
    """Test history endpoint with no documents."""
    response = await client.get("/api/v1/history")

    assert response.status_code == 200

    data = response.json()
    assert data["documents"] == []
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_history_with_documents(client):
    """Test history endpoint with processed documents."""
    store = get_memory_store()

    from app.models import TaskData, TaskStatusEnum, ProcessingResult
    from datetime import datetime

    # Create and complete multiple tasks
    for i in range(3):
        task = TaskData(
            task_id=f"test-task-{i}",
            filename=f"test{i}.pdf",
            file_path=f"/uploads/test{i}.pdf",
            file_size=1024 * (i + 1),
            status=TaskStatusEnum.PROCESSING,
            progress=0,
        )
        await store.create_task(task)

        result = ProcessingResult(
            filename=f"test{i}.pdf",
            summary=f"Summary for document {i}",
            page_count=5 + i,
            file_size=1024 * (i + 1),
            processed_at=datetime.utcnow(),
        )
        await store.complete_task(f"test-task-{i}", result)

    response = await client.get("/api/v1/history")

    assert response.status_code == 200

    data = response.json()
    assert len(data["documents"]) == 3
    assert data["total"] == 3

    # Verify first document (most recent)
    assert data["documents"][0]["filename"] == "test2.pdf"
    assert data["documents"][0]["page_count"] == 7


@pytest.mark.asyncio
async def test_history_max_size(client):
    """Test that history respects maximum size limit."""
    store = get_memory_store()

    from app.models import TaskData, TaskStatusEnum, ProcessingResult
    from datetime import datetime

    # Create and complete 10 tasks (should only keep last 5)
    for i in range(10):
        task = TaskData(
            task_id=f"test-task-{i}",
            filename=f"test{i}.pdf",
            file_path=f"/uploads/test{i}.pdf",
            file_size=1024,
            status=TaskStatusEnum.PROCESSING,
            progress=0,
        )
        await store.create_task(task)

        result = ProcessingResult(
            filename=f"test{i}.pdf",
            summary=f"Summary {i}",
            page_count=5,
            file_size=1024,
            processed_at=datetime.utcnow(),
        )
        await store.complete_task(f"test-task-{i}", result)

    response = await client.get("/api/v1/history")

    assert response.status_code == 200

    data = response.json()
    # Should only have last 5 documents
    assert len(data["documents"]) == 5
    assert data["total"] == 5

    # Should have most recent documents (test9, test8, test7, test6, test5)
    assert data["documents"][0]["filename"] == "test9.pdf"
    assert data["documents"][4]["filename"] == "test5.pdf"


# ========================================
# Stats Endpoint Tests
# ========================================


@pytest.mark.asyncio
async def test_stats_endpoint(client):
    """Test stats endpoint."""
    store = get_memory_store()

    from app.models import TaskData, TaskStatusEnum

    # Create some tasks
    for i in range(3):
        task = TaskData(
            task_id=f"test-task-{i}",
            filename=f"test{i}.pdf",
            file_path=f"/uploads/test{i}.pdf",
            file_size=1024,
            status=TaskStatusEnum.PROCESSING,
            progress=0,
        )
        await store.create_task(task)

    response = await client.get("/api/v1/stats")

    assert response.status_code == 200

    data = response.json()
    assert data["total_tasks"] == 3
    assert "history_size" in data  # Changed from history_count to history_size


# ========================================
# End-to-End Workflow Test
# ========================================


@pytest.mark.asyncio
async def test_complete_workflow(client, sample_pdf_bytes):
    """Test complete workflow: upload -> check status -> view history."""
    with patch("app.api.routes.convert_pdf_to_images") as mock_convert:
        with patch("app.api.routes.process_pdf_complete") as mock_process:
            with patch("app.api.routes.cleanup_temp_images") as mock_cleanup:
                # Mock the processing functions
                mock_convert.return_value = (["/tmp/page1.png"], 1)
                mock_process.return_value = {"summary": "Complete workflow test summary"}
                mock_cleanup.return_value = None

                # Step 1: Upload PDF
                files = {"file": ("workflow.pdf", io.BytesIO(sample_pdf_bytes), "application/pdf")}
                upload_response = await client.post("/api/v1/upload", files=files)

                assert upload_response.status_code == 200
                task_id = upload_response.json()["task_id"]

                # Step 2: Check status (should be processing initially)
                status_response = await client.get(f"/api/v1/status/{task_id}")
                assert status_response.status_code == 200

                # Note: In real scenario, we'd need to wait for background task
                # For this test, we can verify the task exists
                status_data = status_response.json()
                assert status_data["task_id"] == task_id

                # Step 3: Check history
                history_response = await client.get("/api/v1/history")
                assert history_response.status_code == 200
