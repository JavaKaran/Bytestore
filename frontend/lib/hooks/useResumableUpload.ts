import { useState, useCallback, useRef, useEffect } from 'react';
import { resumableUploadService } from '@/services/resumableUpload';
import type {
    UploadProgress,
    UploadStatus,
    CompletedPart,
    StoredUploadState,
    File,
} from '@/lib/types';

interface UseResumableUploadOptions {
    onSuccess?: (file: File) => void;
    onError?: (error: string) => void;
    onProgress?: (progress: UploadProgress) => void;
}

interface UseResumableUploadReturn {
    uploadFile: (file: globalThis.File, folderId?: string) => Promise<void>;
    resumeUpload: (file: globalThis.File, savedState: StoredUploadState) => Promise<void>;
    pauseUpload: () => void;
    cancelUpload: () => Promise<void>;
    dismissProgress: () => void;
    progress: UploadProgress | null;
    isUploading: boolean;
    isPaused: boolean;
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
    const [isPaused, setIsPaused] = useState(false);

    // Refs for abort control and state persistence
    const abortControllerRef = useRef<AbortController | null>(null);
    const currentFileIdRef = useRef<string | null>(null);
    const pausedRef = useRef(false);

    const updateProgress = useCallback((update: Partial<UploadProgress>) => {
        setProgress(prev => {
            if (!prev) return null;
            const newProgress = { ...prev, ...update };
            onProgress?.(newProgress);
            return newProgress;
        });
    }, [onProgress]);

    const uploadFile = useCallback(async (file: globalThis.File, folderId?: string) => {
        // Reset state
        setIsUploading(true);
        setIsPaused(false);
        pausedRef.current = false;
        abortControllerRef.current = new AbortController();

        try {
            // Initialize progress
            setProgress({
                ...initialProgress,
                filename: file.name,
                totalSize: file.size,
                status: 'initiating',
            });

            // Initiate multipart upload
            const initResponse = await resumableUploadService.initiateUpload(
                file.name,
                file.size,
                file.type || undefined,
                folderId
            );

            currentFileIdRef.current = initResponse.file_id;

            // Save initial state to localStorage
            const storedState: StoredUploadState = {
                fileId: initResponse.file_id,
                uploadId: initResponse.upload_id,
                filename: file.name,
                totalSize: file.size,
                totalParts: initResponse.total_parts,
                partSize: initResponse.part_size,
                completedParts: [],
                folderId,
            };
            resumableUploadService.saveUploadState(storedState);

            // Update progress
            setProgress(prev => prev ? {
                ...prev,
                fileId: initResponse.file_id,
                totalParts: initResponse.total_parts,
                status: 'uploading',
            } : null);

            // Get file chunks
            const chunks = resumableUploadService.getChunks(file, initResponse.part_size);
            const completedParts: CompletedPart[] = [];
            let uploadedBytes = 0;

            // Upload each chunk
            for (let i = 0; i < chunks.length; i++) {
                // Check if paused
                if (pausedRef.current) {
                    setProgress(prev => prev ? { ...prev, status: 'paused' } : null);
                    return;
                }

                // Check if aborted
                if (abortControllerRef.current?.signal.aborted) {
                    throw new Error('Upload cancelled');
                }

                const partNumber = i + 1;
                const chunk = chunks[i];

                updateProgress({
                    currentPart: partNumber,
                    status: 'uploading',
                });

                // Get presigned URL for this part
                const presignedUrl = await resumableUploadService.getPresignedUrl(
                    initResponse.file_id,
                    partNumber
                );

                // Upload chunk with retry
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

                // Mark part as uploaded on backend
                await resumableUploadService.markPartUploaded(
                    initResponse.file_id,
                    partNumber,
                    etag
                );

                // Track completed part
                completedParts.push({ part_number: partNumber, etag });
                uploadedBytes += chunk.size;

                // Update localStorage
                resumableUploadService.updateStoredParts(initResponse.file_id, completedParts);

                updateProgress({
                    completedParts: [...completedParts],
                    uploadedBytes,
                    progress: Math.round((uploadedBytes / file.size) * 100),
                });
            }

            // Complete the upload
            updateProgress({ status: 'completing' });

            const completedFile = await resumableUploadService.completeUpload(
                initResponse.file_id,
                completedParts
            );

            // Clear localStorage
            resumableUploadService.clearUploadState(initResponse.file_id);

            updateProgress({
                status: 'completed',
                progress: 100,
            });

            onSuccess?.(completedFile);

        } catch (error) {
            const errorMessage = error instanceof Error ? error.message : 'Upload failed';
            
            // Don't report error if paused or cancelled intentionally
            if (!pausedRef.current && errorMessage !== 'Upload cancelled') {
                updateProgress({ status: 'error', error: errorMessage });
                onError?.(errorMessage);

                // Clean up failed upload - abort on backend and clear localStorage
                const fileId = currentFileIdRef.current;
                if (fileId) {
                    try {
                        await resumableUploadService.abortUpload(fileId);
                    } catch (abortError) {
                        console.warn('Failed to abort upload on server:', abortError);
                    }
                    resumableUploadService.clearUploadState(fileId);
                }
            }
        } finally {
            setIsUploading(false);
            currentFileIdRef.current = null;
        }
    }, [updateProgress, onSuccess, onError]);

    const resumeUpload = useCallback(async (file: globalThis.File, savedState: StoredUploadState) => {
        // Reset state
        setIsUploading(true);
        setIsPaused(false);
        pausedRef.current = false;
        abortControllerRef.current = new AbortController();
        currentFileIdRef.current = savedState.fileId;

        try {
            // Verify upload still exists on backend
            const status = await resumableUploadService.getUploadStatus(savedState.fileId);

            if (status.status !== 'uploading') {
                throw new Error('Upload is no longer in progress');
            }

            // Calculate already uploaded bytes
            const completedPartNumbers = new Set(status.uploaded_parts);
            let uploadedBytes = 0;
            const completedParts: CompletedPart[] = savedState.completedParts.filter(
                part => completedPartNumbers.has(part.part_number)
            );

            // Calculate uploaded bytes from completed parts
            const chunks = resumableUploadService.getChunks(file, savedState.partSize);
            for (const partNum of completedPartNumbers) {
                if (partNum <= chunks.length) {
                    uploadedBytes += chunks[partNum - 1].size;
                }
            }

            // Initialize progress
            setProgress({
                fileId: savedState.fileId,
                filename: savedState.filename,
                totalSize: savedState.totalSize,
                uploadedBytes,
                progress: Math.round((uploadedBytes / savedState.totalSize) * 100),
                status: 'uploading',
                completedParts,
                totalParts: savedState.totalParts,
                currentPart: completedPartNumbers.size,
            });

            // Upload remaining chunks
            for (let i = 0; i < chunks.length; i++) {
                const partNumber = i + 1;

                // Skip already completed parts
                if (completedPartNumbers.has(partNumber)) {
                    continue;
                }

                // Check if paused
                if (pausedRef.current) {
                    setProgress(prev => prev ? { ...prev, status: 'paused' } : null);
                    return;
                }

                // Check if aborted
                if (abortControllerRef.current?.signal.aborted) {
                    throw new Error('Upload cancelled');
                }

                const chunk = chunks[i];

                updateProgress({
                    currentPart: partNumber,
                    status: 'uploading',
                });

                // Get presigned URL for this part
                const presignedUrl = await resumableUploadService.getPresignedUrl(
                    savedState.fileId,
                    partNumber
                );

                // Upload chunk with retry
                const etag = await resumableUploadService.uploadChunkWithRetry(
                    presignedUrl.url,
                    chunk,
                    (loaded) => {
                        const newUploadedBytes = uploadedBytes + loaded;
                        updateProgress({
                            uploadedBytes: newUploadedBytes,
                            progress: Math.round((newUploadedBytes / savedState.totalSize) * 100),
                        });
                    },
                    abortControllerRef.current?.signal
                );

                // Mark part as uploaded on backend
                await resumableUploadService.markPartUploaded(
                    savedState.fileId,
                    partNumber,
                    etag
                );

                // Track completed part
                completedParts.push({ part_number: partNumber, etag });
                uploadedBytes += chunk.size;

                // Update localStorage
                resumableUploadService.updateStoredParts(savedState.fileId, completedParts);

                updateProgress({
                    completedParts: [...completedParts],
                    uploadedBytes,
                    progress: Math.round((uploadedBytes / savedState.totalSize) * 100),
                });
            }

            // Complete the upload
            updateProgress({ status: 'completing' });

            const completedFile = await resumableUploadService.completeUpload(
                savedState.fileId,
                completedParts
            );

            // Clear localStorage
            resumableUploadService.clearUploadState(savedState.fileId);

            updateProgress({
                status: 'completed',
                progress: 100,
            });

            onSuccess?.(completedFile);

        } catch (error) {
            const errorMessage = error instanceof Error ? error.message : 'Resume failed';
            
            if (!pausedRef.current && errorMessage !== 'Upload cancelled') {
                updateProgress({ status: 'error', error: errorMessage });
                onError?.(errorMessage);

                // Clean up failed upload - abort on backend and clear localStorage
                const fileId = currentFileIdRef.current;
                if (fileId) {
                    try {
                        await resumableUploadService.abortUpload(fileId);
                    } catch (abortError) {
                        console.warn('Failed to abort upload on server:', abortError);
                    }
                    resumableUploadService.clearUploadState(fileId);
                }
            }
        } finally {
            setIsUploading(false);
            currentFileIdRef.current = null;
        }
    }, [updateProgress, onSuccess, onError]);

    const pauseUpload = useCallback(() => {
        pausedRef.current = true;
        setIsPaused(true);
        abortControllerRef.current?.abort();
    }, []);

    const cancelUpload = useCallback(async () => {
        abortControllerRef.current?.abort();
        
        const fileId = currentFileIdRef.current;
        if (fileId) {
            try {
                await resumableUploadService.abortUpload(fileId);
                resumableUploadService.clearUploadState(fileId);
            } catch (error) {
                console.warn('Failed to abort upload on server:', error);
            }
        }

        setProgress(null);
        setIsUploading(false);
        setIsPaused(false);
        pausedRef.current = false;
        currentFileIdRef.current = null;
    }, []);

    const dismissProgress = useCallback(() => {
        setProgress(null);
    }, []);

    useEffect(() => {
        if(progress && progress.status === 'completed') {
            setTimeout(() => {
                dismissProgress();
            }, 2000);
        }
    }, [progress, dismissProgress]);

    return {
        uploadFile,
        resumeUpload,
        pauseUpload,
        cancelUpload,
        dismissProgress,
        progress,
        isUploading,
        isPaused,
    };
}

