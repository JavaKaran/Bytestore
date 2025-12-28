import { useState, useCallback, useRef, useEffect } from 'react';
import { resumableUploadService } from '@/services/resumableUpload';
import type {
    UploadProgress,
    CompletedPart,
    File,
} from '@/lib/types';

interface UseResumableUploadOptions {
    onSuccess?: (file: File) => void;
    onError?: (error: string) => void;
    onProgress?: (progress: UploadProgress) => void;
}

interface UseResumableUploadReturn {
    uploadFile: (file: globalThis.File, folderId?: string) => Promise<void>;
    cancelUpload: () => Promise<void>;
    dismissProgress: () => void;
    progress: UploadProgress | null;
    isUploading: boolean;
}

const initialProgress: UploadProgress = {
    fileId: '',
    filename: '',
    totalSize: 0,
    uploadedBytes: 0,
    progress: 0,
    status: 'idle',
    completedParts: [],
    totalParts: 0,
    currentPart: 0,
};

export function useResumableUpload(options: UseResumableUploadOptions = {}): UseResumableUploadReturn {
    const { onSuccess, onError, onProgress } = options;

    const [progress, setProgress] = useState<UploadProgress | null>(null);
    const [isUploading, setIsUploading] = useState(false);

    const abortControllerRef = useRef<AbortController | null>(null);
    const currentFileIdRef = useRef<string | null>(null);

    const generateFingerprint = useCallback(async (file: globalThis.File): Promise<string> => {
        const buffer = await file.arrayBuffer();
        const hashBuffer = await crypto.subtle.digest("SHA-256", buffer);
        const hashArray = Array.from(new Uint8Array(hashBuffer));

        return hashArray
            .map(b => b.toString(16).padStart(2, "0"))
            .join("");
    }, []);

    const updateProgress = useCallback((update: Partial<UploadProgress>) => {
        setProgress(prev => {
            if (!prev) return null;
            const newProgress = { ...prev, ...update };
            onProgress?.(newProgress);
            return newProgress;
        });
    }, [onProgress]);

    const uploadFile = useCallback(async (file: globalThis.File, folderId?: string) => {
        setIsUploading(true);
        abortControllerRef.current = new AbortController();

        try {
            setProgress({
                ...initialProgress,
                filename: file.name,
                totalSize: file.size,
                status: 'initiating',
            });

            const fingerprint = await generateFingerprint(file);

            const initResponse = await resumableUploadService.initiateUpload(
                file.name,
                file.size,
                fingerprint,
                file.type || undefined,
                folderId
            );

            currentFileIdRef.current = initResponse.file_id;
            const uploadedParts = initResponse.uploaded_parts || [];

            setProgress(prev => prev ? {
                ...prev,
                fileId: initResponse.file_id,
                totalParts: initResponse.total_parts,
                status: 'uploading',
            } : null);

            const chunks = resumableUploadService.getChunks(file, initResponse.part_size);
            const completedParts: CompletedPart[] = [];
            let uploadedBytes = 0;

            for (let i = 0; i < chunks.length; i++) {
                if (abortControllerRef.current?.signal.aborted) {
                    throw new Error('Upload cancelled');
                }

                const partNumber = i + 1;
                const chunk = chunks[i];

                const uploadedPart = uploadedParts.find(part => part.part_number === partNumber);

                if (uploadedPart) {
                    completedParts.push({ part_number: uploadedPart.part_number, etag: uploadedPart.etag });
                    uploadedBytes += chunk.size;

                    updateProgress({
                        completedParts: [...completedParts],
                        uploadedBytes,
                        progress: Math.round((uploadedBytes / file.size) * 100),
                    });

                    continue;
                }

                updateProgress({
                    currentPart: partNumber,
                    status: 'uploading',
                });

                const presignedUrl = await resumableUploadService.getPresignedUrl(
                    initResponse.file_id,
                    partNumber
                );

                const etag = await resumableUploadService.uploadChunkWithRetry(
                    presignedUrl.url,
                    chunk,
                    (loaded) => {
                        const newUploadedBytes = uploadedBytes + loaded;
                        updateProgress({
                            uploadedBytes: newUploadedBytes,
                            progress: Math.round((newUploadedBytes / file.size) * 100),
                        });
                    },
                    abortControllerRef.current?.signal
                );

                await resumableUploadService.markPartUploaded(
                    initResponse.file_id,
                    partNumber,
                    etag
                );

                completedParts.push({ part_number: partNumber, etag });
                uploadedBytes += chunk.size;

                updateProgress({
                    completedParts: [...completedParts],
                    uploadedBytes,
                    progress: Math.round((uploadedBytes / file.size) * 100),
                });
            }

            updateProgress({ status: 'completing' });

            const completedFile = await resumableUploadService.completeUpload(
                initResponse.file_id,
                completedParts
            );

            updateProgress({
                status: 'completed',
                progress: 100,
            });

            onSuccess?.(completedFile);

        } catch (error) {
            const errorMessage = error instanceof Error ? error.message : 'Upload failed';

            console.warn('Upload failed:', errorMessage);

            updateProgress({ status: 'error', error: errorMessage });
            onError?.(errorMessage);
        } finally {
            setIsUploading(false);
            currentFileIdRef.current = null;
        }
    }, [updateProgress, onSuccess, onError]);

    const cancelUpload = useCallback(async () => {
        abortControllerRef.current?.abort();

        const fileId = currentFileIdRef.current;
        if (fileId) {
            try {
                await resumableUploadService.abortUpload(fileId);
            } catch (error) {
                console.warn('Failed to abort upload on server:', error);
            }
        }

        setProgress(null);
        setIsUploading(false);
        currentFileIdRef.current = null;
    }, []);

    const dismissProgress = useCallback(() => {
        setProgress(null);
    }, []);

    useEffect(() => {
        if (progress && progress.status === 'completed') {
            setTimeout(() => {
                dismissProgress();
            }, 2000);
        }
    }, [progress, dismissProgress]);

    return {
        uploadFile,
        cancelUpload,
        dismissProgress,
        progress,
        isUploading,
    };
}

