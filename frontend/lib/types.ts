// Authentication Types
export interface RegisterData {
    email: string;
    username: string;
    password: string;
}

export interface LoginData {
    username: string;
    password: string;
}

export interface User {
    id: number;
    email: string;
    username: string;
    is_active: boolean;
    created_at: string;
}

export interface TokenResponse {
    access_token: string;
    token_type: string;
}

// Folder Types
export interface Folder {
    id: string;
    user_id: string;
    name: string;
    parent_folder_id: string | null;
    path: string;
    created_at: string;
    updated_at: string;
}

// File Types
export enum FileStatus {
    UPLOADING = 'uploading',
    COMPLETED = 'completed',
    FAILED = 'failed',
    DELETED = 'deleted',
}

export interface File {
    id: string;
    user_id: string;
    name: string;
    size: number;
    mime: string | null;
    storage_key: string;
    status: FileStatus;
    folder_id: string | null;
    created_at: string;
    updated_at: string;
}

// Multipart Upload Types
export interface MultipartInitiateRequest {
    filename: string;
    size: number;
    fingerprint: string;
    mime_type?: string;
    folder_id?: string;
}

export interface MultipartInitiateResponse {
    file_id: string;
    upload_id: string;
    part_size: number;
    total_parts: number;
    uploaded_parts?: [
        {
            part_number: number;
            etag: string;
        }
    ]
}

export interface PresignedUrlResponse {
    url: string;
    part_number: number;
    expires_in: number;
}

export interface CompletedPart {
    part_number: number;
    etag: string;
}

export interface MultipartCompleteRequest {
    parts: CompletedPart[];
}

export interface UploadStatusResponse {
    file_id: string;
    upload_id: string | null;
    filename: string;
    total_size: number;
    total_parts: number;
    uploaded_parts: number[];
    status: FileStatus;
}

// Upload State Types
export type UploadStatus = 'idle' | 'initiating' | 'uploading' | 'paused' | 'completing' | 'completed' | 'error';

export interface UploadProgress {
    fileId: string;
    filename: string;
    totalSize: number;
    uploadedBytes: number;
    progress: number; // 0-100
    status: UploadStatus;
    error?: string;
    completedParts: CompletedPart[];
    totalParts: number;
    currentPart: number;
}

export interface StoredUploadState {
    fileId: string;
    uploadId: string;
    filename: string;
    totalSize: number;
    totalParts: number;
    partSize: number;
    completedParts: CompletedPart[];
    folderId?: string;
}

