'use client';

import { X, CheckCircle, AlertCircle, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import type { UploadProgress as UploadProgressType } from '@/lib/types';

interface UploadProgressProps {
    progress: UploadProgressType;
    onCancel: () => Promise<void>;
    onDismiss?: () => void;
}

function formatBytes(bytes: number): string {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
}

export function UploadProgress({ progress, onCancel, onDismiss }: UploadProgressProps) {
    const isCompleted = progress.status === 'completed';
    const isError = progress.status === 'error';
    const isActive = progress.status === 'uploading' || progress.status === 'initiating' || progress.status === 'completing';

    const handleDismiss = () => {
        onDismiss?.();
    };

    return (
        <div className="fixed bottom-4 right-4 w-80 bg-card rounded-lg shadow-lg border border-border p-4 z-50">
            {/* Header */}
            <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                    {isCompleted && <CheckCircle className="h-4 w-4 text-primary" />}
                    {isError && <AlertCircle className="h-4 w-4 text-destructive" />}
                    {isActive && <Loader2 className="h-4 w-4 text-primary animate-spin" />}
                    <span className="text-sm font-medium text-card-foreground truncate max-w-[180px]">
                        {progress.filename}
                    </span>
                </div>
                <Button
                    variant="ghost"
                    size="sm"
                    className="h-6 w-6 p-0"
                    onClick={isCompleted || isError ? handleDismiss : onCancel}
                >
                    <X className="h-4 w-4" />
                </Button>
            </div>

            <div className="mb-2">
                <div className="h-2 bg-muted rounded-full overflow-hidden">
                    <div
                        className={`h-full transition-all duration-300 ${
                            isCompleted
                                ? 'bg-primary'
                                : isError
                                ? 'bg-destructive'
                                : 'bg-primary'
                        }`}
                        style={{ width: `${progress.progress}%` }}
                    />
                </div>
            </div>

            <div className="flex items-center justify-between text-xs text-muted-foreground mb-3">
                <span>
                    {formatBytes(progress.uploadedBytes)} / {formatBytes(progress.totalSize)}
                </span>
                <span>
                    {isCompleted
                        ? 'Complete'
                        : isError
                        ? 'Failed'
                        : progress.status === 'initiating'
                        ? 'Starting...'
                        : progress.status === 'completing'
                        ? 'Finishing...'
                        : `${progress.progress}%`}
                </span>
            </div>

            {isError && progress.error && (
                <div className="text-xs text-destructive mb-3 bg-destructive/10 p-2 rounded">
                    {progress.error}
                </div>
            )}

            {!isCompleted && !isError && (
                <div className="flex gap-2">
                    <Button
                        variant="destructive"
                        size="sm"
                        className="flex-1"
                        onClick={onCancel}
                    >
                        <X className="h-4 w-4 mr-1" />
                        Cancel
                    </Button>
                </div>
            )}

            {(isCompleted || isError) && (
                <Button
                    variant="outline"
                    size="sm"
                    className="w-full"
                    onClick={handleDismiss}
                >
                    Dismiss
                </Button>
            )}
        </div>
    );
}

