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
        fingerprint: string,
        mimeType?: string,
        folderId?: string
    ): Promise<MultipartInitiateResponse> => {
        const request: MultipartInitiateRequest = {
            filename,
            size,
            fingerprint,
            mime_type: mimeType,
            folder_id: folderId,
        };
        const response = await api.post<MultipartInitiateResponse>('/upload/initiate', request);
        return response.data;
    },

    /**
     * Get presigned URL for a specific part
     */
    getPresignedUrl: async (fileId: string, partNumber: number): Promise<PresignedUrlResponse> => {
        const response = await api.get<PresignedUrlResponse>(
            `/upload/${fileId}/presigned-url`,
            { params: { part_number: partNumber } }
        );
        return response.data;
    },

    /**
     * Mark a part as uploaded on the backend
     */
    markPartUploaded: async (fileId: string, partNumber: number, etag: string): Promise<void> => {
        await api.post(`/upload/${fileId}/part-uploaded`, {
            part_number: partNumber,
            etag,
        });
    },

    /**
     * Complete the multipart upload
     */
    completeUpload: async (fileId: string, parts: CompletedPart[]): Promise<File> => {
        const response = await api.post<File>(`/upload/${fileId}/complete`, { parts });
        return response.data;
    },

    /**
     * Abort a multipart upload
     */
    abortUpload: async (fileId: string): Promise<void> => {
        await api.post(`/upload/${fileId}/abort`);
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

                const etag = response.headers.get('ETag') || response.headers.get('etag');
                if (!etag) {
                    throw new Error('No ETag in response');
                }

                onProgress?.(chunk.size);

                return etag;
            } catch (error) {
                lastError = error as Error;

                if (abortSignal?.aborted || (error as Error).message === 'Upload aborted') {
                    throw error;
                }

                if (attempt === MAX_RETRIES) {
                    break;
                }

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
    }
};

