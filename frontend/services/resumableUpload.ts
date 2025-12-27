import { api } from '@/lib/config';
import type {
    MultipartInitiateRequest,
    MultipartInitiateResponse,
    PresignedUrlResponse,
    CompletedPart,
    UploadStatusResponse,
    StoredUploadState,
    File,
} from '@/lib/types';

const STORAGE_KEY_PREFIX = 'resumable_upload_';
const MAX_RETRIES = 3;
const RETRY_DELAYS = [1000, 2000, 4000];

/**
 * Sleep utility for retry delays
 */
const sleep = (ms: number): Promise<void> => new Promise(resolve => setTimeout(resolve, ms));

/**
 * Resumable upload service
 * Handles multipart uploads with chunk-level resumability and retry
 */
export const resumableUploadService = {
    /**
     * Initiate a multipart upload
     */
    initiateUpload: async (
        filename: string,
        size: number,
        mimeType?: string,
        folderId?: string
    ): Promise<MultipartInitiateResponse> => {
        const request: MultipartInitiateRequest = {
            filename,
            size,
            mime_type: mimeType,
            folder_id: folderId,
        };
        const response = await api.post<MultipartInitiateResponse>('/files/upload/initiate', request);
        return response.data;
    },

    /**
     * Get presigned URL for a specific part
     */
    getPresignedUrl: async (fileId: string, partNumber: number): Promise<PresignedUrlResponse> => {
        const response = await api.get<PresignedUrlResponse>(
            `/files/${fileId}/presigned-url`,
            { params: { part_number: partNumber } }
        );
        return response.data;
    },

    /**
     * Mark a part as uploaded on the backend
     */
    markPartUploaded: async (fileId: string, partNumber: number, etag: string): Promise<void> => {
        await api.post(`/files/${fileId}/part-uploaded`, {
            part_number: partNumber,
            etag,
        });
    },

    /**
     * Complete the multipart upload
     */
    completeUpload: async (fileId: string, parts: CompletedPart[]): Promise<File> => {
        const response = await api.post<File>(`/files/${fileId}/complete`, { parts });
        return response.data;
    },

    /**
     * Abort a multipart upload
     */
    abortUpload: async (fileId: string): Promise<void> => {
        await api.post(`/files/${fileId}/abort`);
    },

    /**
     * Get upload status for resume
     */
    getUploadStatus: async (fileId: string): Promise<UploadStatusResponse> => {
        const response = await api.get<UploadStatusResponse>(`/files/${fileId}/upload-status`);
        return response.data;
    },

    /**
     * Upload a single chunk with retry logic
     */
    uploadChunkWithRetry: async (
        url: string,
        chunk: Blob,
        onProgress?: (loaded: number) => void,
        abortSignal?: AbortSignal
    ): Promise<string> => {
        let lastError: Error | null = null;

        for (let attempt = 0; attempt <= MAX_RETRIES; attempt++) {
            try {
                // Check if aborted
                if (abortSignal?.aborted) {
                    throw new Error('Upload aborted');
                }

                const response = await fetch(url, {
                    method: 'PUT',
                    body: chunk,
                    headers: {
                        'Content-Type': 'application/octet-stream',
                    },
                    signal: abortSignal,
                });

                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }

                // Get ETag from response headers
                const etag = response.headers.get('ETag') || response.headers.get('etag');
                if (!etag) {
                    throw new Error('No ETag in response');
                }

                // Report progress
                onProgress?.(chunk.size);

                return etag;
            } catch (error) {
                lastError = error as Error;

                // Don't retry if aborted
                if (abortSignal?.aborted || (error as Error).message === 'Upload aborted') {
                    throw error;
                }

                // Don't retry on last attempt
                if (attempt === MAX_RETRIES) {
                    break;
                }

                // Wait before retry
                console.warn(`Chunk upload failed (attempt ${attempt + 1}/${MAX_RETRIES + 1}), retrying...`, error);
                await sleep(RETRY_DELAYS[attempt]);
            }
        }

        throw new Error(`Failed to upload file`);
    },

    /**
     * Split a file into chunks
     */
    getChunks: (file: globalThis.File, partSize: number): Blob[] => {
        const chunks: Blob[] = [];
        let offset = 0;

        while (offset < file.size) {
            const end = Math.min(offset + partSize, file.size);
            chunks.push(file.slice(offset, end));
            offset = end;
        }

        return chunks;
    },

    /**
     * Save upload state to localStorage
     */
    saveUploadState: (state: StoredUploadState): void => {
        try {
            localStorage.setItem(
                `${STORAGE_KEY_PREFIX}${state.fileId}`,
                JSON.stringify(state)
            );
        } catch (error) {
            console.warn('Failed to save upload state to localStorage:', error);
        }
    },

    /**
     * Load upload state from localStorage
     */
    loadUploadState: (fileId: string): StoredUploadState | null => {
        try {
            const stored = localStorage.getItem(`${STORAGE_KEY_PREFIX}${fileId}`);
            if (stored) {
                return JSON.parse(stored) as StoredUploadState;
            }
        } catch (error) {
            console.warn('Failed to load upload state from localStorage:', error);
        }
        return null;
    },

    /**
     * Clear upload state from localStorage
     */
    clearUploadState: (fileId: string): void => {
        try {
            localStorage.removeItem(`${STORAGE_KEY_PREFIX}${fileId}`);
        } catch (error) {
            console.warn('Failed to clear upload state from localStorage:', error);
        }
    },

    /**
     * Get all pending uploads from localStorage
     */
    getAllPendingUploads: (): StoredUploadState[] => {
        const uploads: StoredUploadState[] = [];
        try {
            for (let i = 0; i < localStorage.length; i++) {
                const key = localStorage.key(i);
                if (key?.startsWith(STORAGE_KEY_PREFIX)) {
                    const stored = localStorage.getItem(key);
                    if (stored) {
                        uploads.push(JSON.parse(stored) as StoredUploadState);
                    }
                }
            }
        } catch (error) {
            console.warn('Failed to get pending uploads from localStorage:', error);
        }
        return uploads;
    },

    /**
     * Update completed parts in stored state
     */
    updateStoredParts: (fileId: string, completedParts: CompletedPart[]): void => {
        const state = resumableUploadService.loadUploadState(fileId);
        if (state) {
            state.completedParts = completedParts;
            resumableUploadService.saveUploadState(state);
        }
    },

    /**
     * Clean up stale/failed uploads from localStorage and backend.
     * Call this on app initialization to clean up any leftover uploads.
     * 
     * @param abortStale - If true, also abort uploads on the backend
     * @returns Array of cleaned up file IDs
     */
    cleanupStaleUploads: async (abortStale: boolean = true): Promise<string[]> => {
        const cleanedUp: string[] = [];
        const pendingUploads = resumableUploadService.getAllPendingUploads();

        for (const upload of pendingUploads) {
            try {
                // Check status on backend
                const status = await resumableUploadService.getUploadStatus(upload.fileId);

                // If upload is no longer in progress, clean up localStorage
                if (status.status !== 'uploading') {
                    resumableUploadService.clearUploadState(upload.fileId);
                    cleanedUp.push(upload.fileId);
                    console.log(`Cleaned up completed/failed upload: ${upload.filename}`);
                }
            } catch (error) {
                // If we can't get status (e.g., 404), the upload doesn't exist on backend
                // Clean up localStorage and optionally try to abort
                console.warn(`Upload ${upload.filename} not found on backend, cleaning up...`);
                
                if (abortStale) {
                    try {
                        await resumableUploadService.abortUpload(upload.fileId);
                    } catch {
                        // Ignore abort errors - upload might already be cleaned up
                    }
                }
                
                resumableUploadService.clearUploadState(upload.fileId);
                cleanedUp.push(upload.fileId);
            }
        }

        return cleanedUp;
    },

    /**
     * Force clear a specific upload from localStorage and abort on backend
     */
    forceCleanupUpload: async (fileId: string): Promise<void> => {
        try {
            await resumableUploadService.abortUpload(fileId);
        } catch (error) {
            console.warn('Failed to abort upload on server:', error);
        }
        resumableUploadService.clearUploadState(fileId);
    },

    /**
     * Clear all pending uploads from localStorage (without backend cleanup)
     */
    clearAllPendingUploads: (): void => {
        const pendingUploads = resumableUploadService.getAllPendingUploads();
        for (const upload of pendingUploads) {
            resumableUploadService.clearUploadState(upload.fileId);
        }
    },
};

