import { useEffect, useState } from 'react';
import { getHistory } from '@/api/client';
import type { HistoryItem } from '@/api/types';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

interface HistoryListProps {
  refreshTrigger: number;
}

export default function HistoryList({ refreshTrigger }: HistoryListProps) {
  const [documents, setDocuments] = useState<HistoryItem[]>([]);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string>('');

  const fetchHistory = async () => {
    setIsLoading(true);
    setError('');

    try {
      const data = await getHistory();
      setDocuments(data.documents);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch history');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchHistory();
  }, [refreshTrigger]);

  const toggleExpand = (taskId: string) => {
    setExpandedId(expandedId === taskId ? null : taskId);
  };

  const formatRelativeTime = (dateString: string): string => {
    // Append 'Z' if no timezone info to treat as UTC
    const dateStr = dateString.includes('Z') || dateString.includes('+') ? dateString : dateString + 'Z';
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins} minute${diffMins > 1 ? 's' : ''} ago`;
    if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
    if (diffDays < 7) return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;
    return date.toLocaleDateString();
  };

  const truncateSummary = (summary: string, maxLength: number = 100): string => {
    if (summary.length <= maxLength) return summary;
    return summary.substring(0, maxLength) + '...';
  };

  return (
    <Card className="p-6">
      <div className="space-y-4">
        {/* Header */}
        <div className="flex items-center justify-between">
          <h2 className="text-2xl font-bold">Recent Documents</h2>
          <Button
            variant="outline"
            size="sm"
            onClick={fetchHistory}
            disabled={isLoading}
          >
            {isLoading ? 'Refreshing...' : 'Refresh'}
          </Button>
        </div>

        {/* Error Message */}
        {error && (
          <div className="p-3 bg-destructive/10 border border-destructive/20 rounded-md">
            <p className="text-sm text-destructive">{error}</p>
          </div>
        )}

        {/* Loading State */}
        {isLoading && documents.length === 0 && (
          <div className="flex items-center justify-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
          </div>
        )}

        {/* Empty State */}
        {!isLoading && documents.length === 0 && (
          <div className="text-center py-8">
            <p className="text-muted-foreground">No documents processed yet</p>
            <p className="text-sm text-muted-foreground mt-2">
              Upload a PDF to get started
            </p>
          </div>
        )}

        {/* Documents List */}
        {documents.length > 0 && (
          <div className="space-y-3">
            {documents.map((doc) => (
              <Card key={doc.task_id} className="p-4">
                <div className="space-y-2">
                  {/* Document Header */}
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex-1 min-w-0">
                      <h3 className="font-semibold truncate">{doc.filename}</h3>
                      <div className="flex items-center gap-2 mt-1">
                        <Badge variant="outline" className="text-xs">
                          {doc.page_count} pages
                        </Badge>
                        <span className="text-xs text-muted-foreground">
                          {formatRelativeTime(doc.processed_at)}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Summary Preview/Full */}
                  <div className="text-sm text-muted-foreground">
                    {expandedId === doc.task_id ? (
                      <p className="whitespace-pre-wrap">{doc.summary}</p>
                    ) : (
                      <p>{truncateSummary(doc.summary)}</p>
                    )}
                  </div>

                  {/* Show More/Less Button */}
                  {doc.summary.length > 100 && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => toggleExpand(doc.task_id)}
                      className="text-xs h-auto py-1 px-2"
                    >
                      {expandedId === doc.task_id ? 'Show less' : 'Show more'}
                    </Button>
                  )}
                </div>
              </Card>
            ))}
          </div>
        )}

        {/* Document Count */}
        {documents.length > 0 && (
          <p className="text-xs text-muted-foreground text-center">
            Showing {documents.length} recent document{documents.length > 1 ? 's' : ''}
          </p>
        )}
      </div>
    </Card>
  );
}
