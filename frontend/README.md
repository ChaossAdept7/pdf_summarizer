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

## Setup Instructions

### 1. Install Dependencies

```bash
npm install
```

### 2. Configure Environment Variables

The `.env` file is already configured with the default backend URL:

```
VITE_API_URL=http://0.0.0.0:8000
```

If your backend is running on a different URL, update this file.

### 3. Start Development Server

```bash
npm run dev
```

The application will be available at: **http://localhost:5173**

## Testing the Application

### Prerequisites for Testing

1. **Start the Backend Server** (if not already running):
   ```bash
   cd ../backend
   # Follow backend setup instructions
   ```

2. **Verify Backend is Running**:
   - Backend should be accessible at `http://0.0.0.0:8000`
   - Check health endpoint: `http://0.0.0.0:8000/health`
   - View API docs: `http://0.0.0.0:8000/docs`

### Testing Steps

1. **Open the frontend** at http://localhost:5173

2. **Upload a PDF**:
   - Click "Choose File" or use the file input
   - Select a PDF file (max 50MB)
   - Click "Upload and Process"

3. **Watch Progress**:
   - Progress bar will show 0-100%
   - Status updates every 2 seconds
   - Processing indicator (spinner) displays

4. **View Summary**:
   - Once completed (100%), summary appears
   - Shows: filename, page count, size, processed date
   - Summary text with "Copy" button

5. **Check History**:
   - Right column shows last 5 processed documents
   - Click "Show more" to expand full summary
   - Click "Refresh" to manually reload history

### Expected Behavior

✅ **Successful Upload:**
- Progress tracker appears
- Progress bar animates from 0-100%
- Green "Completed" badge shows
- Summary displays with metadata

❌ **Error Handling:**
- Invalid file type → "Only PDF files are supported"
- File too large → "File size must be less than 50MB"
- Backend error → Displays error message

## Available Scripts

### Development

```bash
npm run dev
```
Starts the Vite dev server with hot reload at http://localhost:5173

### Build

```bash
npm run build
```
Builds the application for production. Output in `dist/` folder.

### Preview

```bash
npm run preview
```
Preview the production build locally.

## Project Structure

```
frontend/
├── src/
│   ├── components/
│   │   ├── ui/                 # Shadcn UI components
│   │   │   ├── button.tsx
│   │   │   ├── card.tsx
│   │   │   ├── progress.tsx
│   │   │   └── badge.tsx
│   │   ├── FileUpload.tsx      # PDF upload component
│   │   ├── ProgressTracker.tsx # Real-time progress tracking
│   │   └── HistoryList.tsx     # Document history list
│   ├── api/
│   │   ├── client.ts           # Axios API client
│   │   └── types.ts            # TypeScript type definitions
│   ├── lib/
│   │   └── utils.ts            # Utility functions
│   ├── App.tsx                 # Main application component
│   ├── main.tsx                # Application entry point
│   └── index.css               # Tailwind CSS + theme
├── public/
├── .env                        # Environment variables
├── vite.config.ts              # Vite configuration
├── tsconfig.json               # TypeScript configuration
└── package.json
```

## API Integration

The frontend communicates with the backend via three endpoints:

### 1. Upload PDF
```typescript
POST /api/v1/upload
Content-Type: multipart/form-data

Response: { task_id, status, message }
```

### 2. Check Status
```typescript
GET /api/v1/status/{task_id}

Response: {
  task_id,
  status: 'processing' | 'completed' | 'failed',
  progress: 0-100,
  result?: { filename, summary, page_count, processed_at }
}
```

### 3. Get History
```typescript
GET /api/v1/history

Response: {
  documents: [...],
  total: number
}
```

## Troubleshooting

### Backend Connection Issues

**Problem:** "Failed to upload file" or network errors

**Solutions:**
1. Verify backend is running: `curl http://0.0.0.0:8000/health`
2. Check `.env` file has correct `VITE_API_URL`
3. Ensure no CORS issues (backend should allow frontend origin)

### Progress Not Updating

**Problem:** Progress stuck at 0% or not polling

**Solutions:**
1. Check browser console for errors
2. Verify backend `/api/v1/status/{task_id}` endpoint responds
3. Ensure task_id is valid

### Styling Issues

**Problem:** Components look unstyled or broken

**Solutions:**
1. Clear browser cache
2. Restart dev server: `npm run dev`
3. Check Tailwind CSS is configured: `src/index.css` has `@import "tailwindcss"`

## Development Notes

- **Polling Interval:** Progress updates every 2 seconds (configurable in `ProgressTracker.tsx`)
- **File Size Limit:** 50MB (client-side validation)
- **History Limit:** Shows last 5 documents (backend controlled)
- **Auto-refresh:** History refreshes automatically when processing completes

## Browser Support

- Chrome/Edge (latest)
- Firefox (latest)
- Safari (latest)

## License

ISC
