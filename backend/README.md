# PDF Summarizer API

A FastAPI-based REST API for processing PDF documents and generating AI-powered summaries using OpenAI's Vision API.

## 🎯 Features

- ✅ PDF upload support (up to 50MB, 100 pages)
- ✅ Async processing with task status tracking
- ✅ AI-powered summarization using OpenAI Vision API
- ✅ Document history (last 5 processed documents)
- ✅ Auto-generated API documentation (Swagger/OpenAPI)
- ✅ Docker support for easy deployment

---

## 📋 Prerequisites

- **Python 3.11+**
- **OpenAI API Key** ([Get one here](https://platform.openai.com/api-keys))
- **poppler-utils** (for PDF processing)

### Install poppler-utils

```bash
# macOS
brew install poppler

# Ubuntu/Debian
sudo apt-get update && sudo apt-get install -y poppler-utils

# Alpine Linux (Docker)
apk add poppler-utils
```

---

## 🐳 Docker Setup

### Prerequisites

- **Docker** and **Docker Compose** installed ([Get Docker](https://docs.docker.com/get-docker/))
- **OpenAI API Key**

### Quick Start with Docker Compose (Recommended)

#### 1. Configure Environment

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env and add your OpenAI API key
# OPENAI_API_KEY=sk-proj-your-actual-key-here
```

#### 2. Build and Start the Container

```bash
# Build and start in foreground (see logs in terminal)
docker-compose up --build

# OR build and start in background (detached mode)
docker-compose up -d --build
```

#### 3. Verify the Application is Running

```bash
# Check container status
docker-compose ps

# Test the health endpoint
curl http://localhost:8000/health

# View API documentation
# Open browser: http://localhost:8000/docs
```

#### 4. View Logs

```bash
# Follow logs in real-time
docker-compose logs -f

# View last 100 lines
docker-compose logs --tail=100
```

#### 5. Stop the Container

```bash
# Stop and remove containers
docker-compose down

# Stop, remove containers, and remove volumes
docker-compose down -v
```

### Using Docker Directly (Without Compose)

```bash
# 1. Build the image
docker build -t pdf-summarizer:latest .

# 2. Run the container
docker run -d \
  --name pdf-summarizer-api \
  -p 8000:8000 \
  -e OPENAI_API_KEY=your-key-here \
  -v $(pwd)/uploads:/app/uploads \
  -v $(pwd)/temp:/app/temp \
  pdf-summarizer:latest

# 3. View logs
docker logs -f pdf-summarizer-api

# 4. Stop and remove
docker stop pdf-summarizer-api
docker rm pdf-summarizer-api
```

### Docker Troubleshooting

**Port already in use:**
```bash
# Use a different port (e.g., 8080)
# Edit docker-compose.yml and change ports to "8080:8000"
```

**View container details:**
```bash
docker-compose exec api bash  # Enter container shell
docker-compose top            # View running processes
```

**Rebuild after code changes:**
```bash
docker-compose up --build --force-recreate
```

---

## 🚀 Quick Start (Local Development)

### 1. Clone the Repository

```bash
git clone <your-repo-url>
cd backend
```

### 2. Set Up Virtual Environment

```bash
# Create virtual environment
python3.11 -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate

# On Windows:
venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Secrets

```bash
# Copy the example file
cp .env.example .env

# Edit .env and add your OpenAI API key
# OPENAI_API_KEY=sk-proj-your-actual-key-here
```

**Important:** Never commit your `.env` file to version control!

### 5. Run the Application

```bash
# Start the development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at:
- **API:** http://localhost:8000
- **Interactive Docs:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

---

## 📡 API Endpoints

### Upload PDF for Processing
```bash
curl -X POST http://localhost:8000/api/v1/upload \
  -F "file=@/path/to/your/document.pdf"
```
Returns a task ID for tracking. Max file size: 50MB, 100 pages, PDF only.

### Check Processing Status
```bash
curl http://localhost:8000/api/v1/status/{task_id}
```
Returns status: `processing`, `completed`, or `failed` with progress percentage.

### Get Processing History
```bash
curl http://localhost:8000/api/v1/history
```
Returns the last 5 processed documents.

### Health Check
```bash
curl http://localhost:8000/health
```

---

## 🔧 Configuration

### Environment Variables (Secrets)

Create a `.env` file with your secrets:

```bash
# Required: OpenAI API Key
OPENAI_API_KEY=sk-proj-your-actual-key-here

# Optional: Override default model
OPENAI_MODEL=gpt-4o-mini
```

### Application Configuration

All non-secret configuration is defined in `app/config.py` with sensible defaults:

- **File Uploads:** Max 50MB, 100 pages, PDF only
- **Storage:** `./uploads` for PDFs, `./temp` for temporary files
- **History:** Last 5 documents
- **Server:** Host `0.0.0.0`, Port `8000`

You can override these defaults by setting environment variables if needed.

---

## 🧪 Testing

### Run All Tests

```bash
pytest
```

### Run with Coverage

```bash
pytest --cov=app tests/
```

### Run Specific Test File

```bash
pytest tests/test_api.py -v
```

---

## 📁 Project Structure

```
backend/
├── app/
│   ├── __init__.py           # Package initialization
│   ├── main.py               # FastAPI application
│   ├── config.py             # Configuration management
│   ├── models.py             # Pydantic data models
│   ├── api/                  # API endpoints (to be implemented)
│   ├── services/             # Business logic (to be implemented)
│   └── storage/
│       ├── memory_store.py   # In-memory task storage
│       └── file_storage.py   # File operations
├── tests/                    # Test suite
├── uploads/                  # Uploaded PDFs
├── temp/                     # Temporary files
├── .env                      # Secrets (gitignored)
├── .env.example              # Secrets template
├── requirements.txt          # Python dependencies
├── Dockerfile                # Docker configuration
├── docker-compose.yml        # Docker Compose setup
├── CLAUDE.md                 # Project documentation
├── PLAN.md                   # Implementation plan
└── README.md                 # This file
```

---

## 🔒 Security Best Practices

1. **Never commit secrets** - `.env` is in `.gitignore`
2. **Rotate API keys regularly** - Update your OpenAI API key periodically
3. **Use environment-specific configs** - Different keys for dev/staging/prod
4. **Validate file uploads** - Built-in size and type validation
5. **Sanitize filenames** - Automatic sanitization prevents path traversal

---