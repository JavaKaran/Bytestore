import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"
import { 
    File as FileIcon, 
    Image, 
    Video, 
    Music, 
    FileText, 
    Code, 
    Archive, 
    Table, 
    Presentation,
    FileCode
} from "lucide-react"
import type { LucideIcon } from "lucide-react"

export function cn(...inputs: ClassValue[]) {
    return twMerge(clsx(inputs))
}

/**
 * Format file size in bytes to human-readable format
 * - KB for sizes up to 1023 KB
 * - MB for sizes up to 1023 MB
 * - GB for sizes 1024 MB and above
 * 
 * @param bytes - File size in bytes
 * @returns Formatted string (e.g., "512 KB", "1.5 MB", "2.3 GB")
 */
export function formatFileSize(bytes: number): string {
    const KB = 1024
    const MB = KB * 1024
    const GB = MB * 1024

    if (bytes < KB) {
        return `${bytes} B`
    } else if (bytes < MB) {
        // Show KB for sizes up to 1023 KB
        return `${(bytes / KB).toFixed(2)} KB`
    } else if (bytes < GB) {
        // Show MB for sizes up to 1023 MB
        return `${(bytes / MB).toFixed(2)} MB`
    } else {
        // Show GB for sizes 1024 MB and above
        return `${(bytes / GB).toFixed(2)} GB`
    }
}

/**
 * Get file extension from filename
 */
function getFileExtension(filename: string): string {
    const parts = filename.split('.')
    return parts.length > 1 ? parts[parts.length - 1].toLowerCase() : ''
}

/**
 * Get appropriate icon for file type based on MIME type or file extension
 * Falls back to FileIcon if no specific icon is available
 * 
 * @param filename - File name (used to extract extension)
 * @param mimeType - MIME type of the file (optional)
 * @returns Lucide icon component
 */
export function getFileIcon(filename: string, mimeType: string | null = null): LucideIcon {
    const extension = getFileExtension(filename)
    
    // Check MIME type first (more reliable)
    if (mimeType) {
        if (mimeType.startsWith('image/')) {
            return Image
        }
        if (mimeType.startsWith('video/')) {
            return Video
        }
        if (mimeType.startsWith('audio/')) {
            return Music
        }
        if (mimeType === 'application/pdf') {
            return FileText
        }
        if (mimeType.includes('spreadsheet') || mimeType.includes('excel') || 
            mimeType === 'text/csv' || mimeType === 'application/vnd.ms-excel' ||
            mimeType === 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet') {
            return Table
        }
        if (mimeType.includes('presentation') || mimeType.includes('powerpoint') ||
            mimeType === 'application/vnd.ms-powerpoint' ||
            mimeType === 'application/vnd.openxmlformats-officedocument.presentationml.presentation') {
            return Presentation
        }
        if (mimeType.includes('word') || mimeType.includes('document') ||
            mimeType === 'application/msword' ||
            mimeType === 'application/vnd.openxmlformats-officedocument.wordprocessingml.document') {
            return FileText
        }
        if (mimeType.includes('json') || mimeType.includes('javascript') ||
            mimeType.includes('typescript') || mimeType.includes('xml')) {
            return FileCode
        }
        if (mimeType.includes('zip') || mimeType.includes('rar') ||
            mimeType.includes('tar') || mimeType.includes('archive') ||
            mimeType.includes('compressed')) {
            return Archive
        }
        if (mimeType.startsWith('text/')) {
            return FileText
        }
        if (mimeType.includes('code') || mimeType.includes('source')) {
            return Code
        }
    }
    
    // Fallback to extension-based detection
    const extensionMap: Record<string, LucideIcon> = {
        // Images
        'jpg': Image,
        'jpeg': Image,
        'png': Image,
        'gif': Image,
        'svg': Image,
        'webp': Image,
        'bmp': Image,
        'ico': Image,
        'tiff': Image,
        
        // Videos
        'mp4': Video,
        'avi': Video,
        'mov': Video,
        'wmv': Video,
        'flv': Video,
        'webm': Video,
        'mkv': Video,
        'm4v': Video,
        
        // Audio
        'mp3': Music,
        'wav': Music,
        'flac': Music,
        'aac': Music,
        'ogg': Music,
        'wma': Music,
        'm4a': Music,
        
        // Documents
        'pdf': FileText,
        'doc': FileText,
        'docx': FileText,
        'txt': FileText,
        'rtf': FileText,
        
        // Spreadsheets
        'xls': Table,
        'xlsx': Table,
        'csv': Table,
        
        // Presentations
        'ppt': Presentation,
        'pptx': Presentation,
        
        // Archives
        'zip': Archive,
        'rar': Archive,
        '7z': Archive,
        'tar': Archive,
        'gz': Archive,
        'bz2': Archive,
        
        // Code
        'js': Code,
        'jsx': Code,
        'ts': Code,
        'tsx': Code,
        'py': Code,
        'java': Code,
        'cpp': Code,
        'c': Code,
        'cs': Code,
        'php': Code,
        'rb': Code,
        'go': Code,
        'rs': Code,
        'swift': Code,
        'kt': Code,
        'html': FileCode,
        'css': FileCode,
        'scss': FileCode,
        'sass': FileCode,
        'json': FileCode,
        'xml': FileCode,
        'yaml': FileCode,
        'yml': FileCode,
        'md': FileText,
        'sh': FileCode,
        'bash': FileCode,
        'zsh': FileCode,
    }
    
    return extensionMap[extension] || FileIcon
}

