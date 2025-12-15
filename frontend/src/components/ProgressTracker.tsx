import { useEffect, useState } from 'react';
import { getTaskStatus } from '@/api/client';
import type { TaskStatusResponse } from '@/api/types';
import { Card } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';

interface ProgressTrackerProps {
  taskId: string | null;
  onComplete: () => void;
}

export default function ProgressTracker({ taskId, onComplete }: ProgressTrackerProps) {
  const [taskData, setTaskData] = useState<TaskStatusResponse | null>(null);
  const [error, setError] = useState<string>('');

  useEffect(() => {
    if (!taskId) {
      setTaskData(null);
      setError('');
      return;
    }

    let isMounted = true;
    let shouldPoll = true;

    const pollStatus = async () => {
      if (!isMounted || !shouldPoll) return;

      try {
        const data = await getTaskStatus(taskId);
        if (!isMounted) return;

        setTaskData(data);
        setError('');

        // Stop polling if task is done
        if (data.status === 'completed' || data.status === 'failed') {
          shouldPoll = false;
          if (data.status === 'completed') {
            onComplete();
          }
          return; // Don't schedule next poll
        }

        // Only continue polling if still processing
        if (shouldPoll && data.status === 'processing') {
          setTimeout(pollStatus, 3000);
        }
      } catch (err) {
        if (!isMounted) return;
        setError(err instanceof Error ? err.message : 'Failed to fetch status');
        // Retry on error after delay
        if (shouldPoll) {
          setTimeout(pollStatus, 3000);
        }
      }
    };

    // Start polling
    pollStatus();

    return () => {
      isMounted = false;
      shouldPoll = false;
    };
  }, [taskId, onComplete]);

  if (!taskId || !taskData) {
    return null;
  }

  const getStatusBadge = () => {
    switch (taskData.status) {
      case 'processing':
        return <Badge className="bg-blue-600">Processing</Badge>;
      case 'completed':
        return <Badge className="bg-green-600">Completed</Badge>;
      case 'failed':
        return <Badge variant="destructive">Failed</Badge>;
      default:
        return <Badge variant="secondary">{taskData.status}</Badge>;
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  return (
    <Card className="p-6">
      <div className="space-y-4">
        {/* Status Header */}
        <div className="flex items-center justify-between">
          <h2 className="text-2xl font-bold">Processing Status</h2>
          {getStatusBadge()}
        </div>

        {/* Progress Bar */}
        {taskData.status === 'processing' && (
          <div className="space-y-2">
            <Progress value={taskData.progress} className="h-2" />
            <p className="text-sm text-muted-foreground text-center">
              {taskData.progress}% complete
            </p>
          </div>
        )}

        {/* Error Message */}
        {(taskData.status === 'failed' || error) && (
          <div className="p-3 bg-destructive/10 border border-destructive/20 rounded-md">
            <p className="text-sm text-destructive">
              {taskData.error || error || 'Processing failed'}
            </p>
          </div>
        )}

        {/* Summary Display */}
        {taskData.status === 'completed' && taskData.result && (
          <div className="space-y-4">
            {/* Metadata */}
            <div className="grid grid-cols-2 gap-4 p-4 bg-muted rounded-md">
              <div>
                <p className="text-xs text-muted-foreground">Filename</p>
                <p className="text-sm font-medium truncate">
                  {taskData.result.filename}
                </p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Pages</p>
                <p className="text-sm font-medium">{taskData.result.page_count}</p>
              </div>
              {taskData.result.file_size && (
                <div>
                  <p className="text-xs text-muted-foreground">Size</p>
                  <p className="text-sm font-medium">
                    {(taskData.result.file_size / 1024 / 1024).toFixed(2)} MB
                  </p>
                </div>
              )}
              <div>
                <p className="text-xs text-muted-foreground">Processed</p>
                <p className="text-sm font-medium">
                  {new Date(taskData.result.processed_at).toLocaleString()}
                </p>
              </div>
            </div>

            {/* Summary */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-lg font-semibold">Summary</h3>
                <button
                  onClick={() => copyToClipboard(taskData.result!.summary)}
                  className="text-xs text-primary hover:underline"
                >
                  Copy
                </button>
              </div>
              <div className="p-4 bg-muted rounded-md max-h-64 overflow-y-auto">
                <p className="text-sm whitespace-pre-wrap">
                  {taskData.result.summary}
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Processing Indicator */}
        {taskData.status === 'processing' && (
          <div className="flex items-center justify-center py-4">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
          </div>
        )}
      </div>
    </Card>
  );
}
