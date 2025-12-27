import { useEffect, useRef } from 'react';
import { resumableUploadService } from '@/services/resumableUpload';

export function useUploadCleanup() {
    const hasRun = useRef(false);

    useEffect(() => {
        // Only run once on mount
        if (hasRun.current) return;

        const cleanupPendingUploads = async () => {
            try {
                hasRun.current = true;

                const pendingUploads = resumableUploadService.getAllPendingUploads();
                
                if (pendingUploads.length === 0) {
                    return;
                }

                for (const upload of pendingUploads) {
                    try {
                        // Check if upload still exists and is in progress on backend
                        const status = await resumableUploadService.getUploadStatus(upload.fileId);

                        if (status.status === 'uploading') {
                            try {
                                await resumableUploadService.abortUpload(upload.fileId);
                            } catch (abortError) {
                                console.warn(`[Upload Cleanup] Failed to abort upload on server:`, abortError);
                            }
                        } else {
                            // Upload is completed, failed, or deleted - just clean localStorage
                            console.log(`[Upload Cleanup] Cleaning up ${status.status} upload: ${upload.filename}`);
                        }

                        // Clear from localStorage
                        resumableUploadService.clearUploadState(upload.fileId);
                        
                    } catch (error) {
                        // Upload doesn't exist on backend (404) or other error
                        // Clean up localStorage entry
                        console.log(`[Upload Cleanup] Removing invalid upload state: ${upload.filename}`);
                        resumableUploadService.clearUploadState(upload.fileId);
                    }
                }

                console.log('[Upload Cleanup] Cleanup complete');
            } catch (error) {
                console.error('[Upload Cleanup] Error during cleanup:', error);
            }
        };

        // Run cleanup after a short delay to let the app initialize
        const timeoutId = setTimeout(cleanupPendingUploads, 1000);

        return () => clearTimeout(timeoutId);
    }, []);
}

