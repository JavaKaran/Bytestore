import { api } from '@/lib/config';
import type { File } from '@/lib/types';

/**
 * File service
 * Handles all file-related API calls
 */
export const fileService = {
    /**
     * Get root files (files with no folder)
     */
    getRootFiles: async (): Promise<File[]> => {
        // Omit folder_id parameter - FastAPI defaults to None, which returns root files
        const response = await api.get<File[]>('/files/');
        return response.data;
    },

    /**
     * Get files by folder ID
     */
    getFilesByFolder: async (folderId: string): Promise<File[]> => {
        const response = await api.get<File[]>('/files/', {
            params: {
                folder_id: folderId,
            },
        });
        return response.data;
    },

    /**
     * Upload a file to Cloudflare R2
     */
    uploadFile: async (file: globalThis.File, folderId?: string): Promise<File> => {
        const formData = new FormData();
        formData.append('file', file);
        if (folderId) {
            formData.append('folder_id', folderId);
        }

        const response = await api.post<File>('/files/upload', formData, {
            headers: {
                'Content-Type': 'multipart/form-data',
            },
        });
        return response.data;
    },

    /**
     * Get presigned download URL for a file
     */
    getDownloadUrl: async (fileId: string, expiresIn: number = 3600): Promise<string> => {
        const response = await api.get<{ download_url: string; expires_in: number }>(
            `/files/${fileId}/download-url`,
            {
                params: {
                    expires_in: expiresIn,
                },
            }
        );
        return response.data.download_url;
    },

    /**
     * Update file (rename or move)
     */
    updateFile: async (fileId: string, name?: string, folderId?: string): Promise<File> => {
        const response = await api.put<File>(`/files/${fileId}`, {
            name,
            folder_id: folderId || null,
        });
        return response.data;
    },

    /**
     * Move file to a different folder
     */
    moveFile: async (fileId: string, folderId: string | null): Promise<File> => {
        const response = await api.put<File>(`/files/${fileId}/move`, {
            folder_id: folderId,
        });
        return response.data;
    },

    /**
     * Delete file
     */
    deleteFile: async (fileId: string): Promise<void> => {
        await api.delete(`/files/${fileId}`);
    },
};

