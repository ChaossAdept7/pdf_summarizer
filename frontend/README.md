# PDF Summarizer - Frontend

A React-based frontend application for uploading PDFs and receiving AI-generated summaries.

## Features

- 📄 Upload PDF files (up to 50MB)
- ⏱️ Real-time progress tracking (0-100%)
- 📝 Display AI-generated summaries
- 📚 View history of last 5 processed documents
- 📱 Responsive design (mobile, tablet, desktop)
- 🎨 Modern UI with Tailwind CSS and Shadcn/ui

## Tech Stack

- **Framework:** React 18 + TypeScript
- **Build Tool:** Vite 5
- **Styling:** Tailwind CSS v4
- **UI Components:** Shadcn/ui (Radix UI primitives)
- **HTTP Client:** Axios
- **State Management:** React useState/useEffect

## Prerequisites

- Node.js 18.x or higher
- npm 10.x or higher
- Backend server running on `http://0.0.0.0:8000` (or configure via `.env`)

## Docker Setup Instructions

### 1. Configure Environment Variables

Copy the Docker environment template:

```bash
cp .env.docker .env
```

The `.env.docker` file contains Docker-specific configuration:

```bash
# API URL for backend connection
# For Docker Desktop (Windows/Mac)
VITE_API_URL=http://host.docker.internal:8000

# For Linux Docker (use this instead)
# VITE_API_URL=http://172.17.0.1:8000

# Port for frontend container (default 3000)
FRONTEND_PORT=3000
```

**Note:** `host.docker.internal` allows the container to access services running on your host machine (Docker Desktop). On Linux, use `172.17.0.1` or your host IP address instead.

### 2. Start with Docker Compose

```bash
docker-compose up --build
```

The application will be available at: **http://localhost:3000**

### 3. Run in Detached Mode

```bash
docker-compose up -d
```

### 4. Stop the Container

```bash
docker-compose down
```

### 5. View Logs

```bash
docker-compose logs -f frontend
```

## Local Setup Instructions

### 1. Install Dependencies

```bash
npm install
```

### 2. Configure Environment Variables

Copy the example environment file:

```bash
cp .env.example .env
```

The `.env.example` file contains local development configuration:

```bash
# Backend API URL
VITE_API_URL=http://localhost:8000
```

If your backend is running on a different URL or port, update the `.env` file accordingly.

### 3. Start Development Server

```bash
npm run dev
```

The application will be available at: **http://localhost:5173**