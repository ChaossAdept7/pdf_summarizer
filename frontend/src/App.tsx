import { useState } from 'react';
import FileUpload from '@/components/FileUpload';
import ProgressTracker from '@/components/ProgressTracker';
import HistoryList from '@/components/HistoryList';

function App() {
  const [currentTaskId, setCurrentTaskId] = useState<string | null>(null);
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  const handleUploadSuccess = (taskId: string) => {
    setCurrentTaskId(taskId);
  };

  const handleProcessingComplete = () => {
    // Refresh history when a document is processed
    setRefreshTrigger((prev) => prev + 1);

    // Clear current task to stop polling and unmount ProgressTracker
    setCurrentTaskId(null);
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b">
        <div className="container mx-auto px-4 py-6">
          <h1 className="text-3xl font-bold">PDF Summarizer</h1>
          <p className="text-muted-foreground mt-1">
            Upload PDFs and get AI-generated summaries
          </p>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Left Column: Upload & Progress */}
          <div className="space-y-6">
            <FileUpload onUploadSuccess={handleUploadSuccess} />
            {currentTaskId && (
              <ProgressTracker
                taskId={currentTaskId}
                onComplete={handleProcessingComplete}
              />
            )}
          </div>

          {/* Right Column: History */}
          <div>
            <HistoryList refreshTrigger={refreshTrigger} />
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t mt-12">
        <div className="container mx-auto px-4 py-6 text-center text-sm text-muted-foreground">
          PDF Summarizer - Powered by AI
        </div>
      </footer>
    </div>
  );
}

export default App;
