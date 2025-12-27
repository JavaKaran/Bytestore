import { api } from '@/lib/config';
import type { Folder } from '@/lib/types';

/**
 * Folder service
 * Handles all folder-related API calls
 */
export const folderService = {
    /**
     * Get root folders (folders with no parent)
     */
    getRootFolders: async (): Promise<Folder[]> => {
        // Omit parent_folder_id parameter - FastAPI defaults to None, which returns root folders
        const response = await api.get<Folder[]>('/folders/');
        return response.data;
    },

    /**
     * Get folders by parent folder ID
     */
    getFoldersByParent: async (parentFolderId: string): Promise<Folder[]> => {
        const response = await api.get<Folder[]>('/folders/', {
            params: {
                parent_folder_id: parentFolderId,
            },
        });
        return response.data;
    },

    /**
     * Create a new folder
     */
    createFolder: async (name: string, parentFolderId?: string): Promise<Folder> => {
        const response = await api.post<Folder>('/folders/', {
            name,
            parent_folder_id: parentFolderId || null,
        });
        return response.data;
    },

    /**
     * Get folder by ID
     */
    getFolderById: async (folderId: string): Promise<Folder> => {
        const response = await api.get<Folder>(`/folders/${folderId}`);
        return response.data;
    },

    /**
     * Update folder (rename or move)
     */
    updateFolder: async (folderId: string, name?: string, parentFolderId?: string): Promise<Folder> => {
        const response = await api.put<Folder>(`/folders/${folderId}`, {
            name,
            parent_folder_id: parentFolderId || null,
        });
        return response.data;
    },

    /**
     * Move folder to a different parent folder
     */
    moveFolder: async (folderId: string, parentFolderId: string | null): Promise<Folder> => {
        const response = await api.put<Folder>(`/folders/${folderId}/move`, {
            parent_folder_id: parentFolderId,
        });
        return response.data;
    },

    /**
     * Get all folders for a user
     */
    getAllFolders: async (): Promise<Folder[]> => {
        const response = await api.get<Folder[]>('/folders/all');
        return response.data;
    },

    /**
     * Delete folder
     */
    deleteFolder: async (folderId: string): Promise<void> => {
        await api.delete(`/folders/${folderId}?force=true`);
    },
};

