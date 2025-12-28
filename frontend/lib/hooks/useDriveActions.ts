import { useState, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { toast } from 'sonner'
import Cookies from 'js-cookie'
import { AxiosError } from 'axios'
import { authService } from '@/services/auth'
import { folderService } from '@/services/folder'
import { fileService } from '@/services/file'
import { useResumableUpload } from '@/lib/hooks/useResumableUpload'
import { FileStatus } from '@/lib/types'
import type { File, Folder, UploadProgress } from '@/lib/types'

interface UseDriveActionsOptions {
    folderId?: string
    onFileUploaded?: () => Promise<void>
    onFolderCreated?: () => Promise<void>
    onFolderRenamed?: () => Promise<void>
    onFileRenamed?: () => Promise<void>
    onCurrentFolderRenamed?: () => Promise<void>
    onItemMoved?: () => Promise<void>
    onItemDeleted?: () => Promise<void>
}

export function useDriveActions(options: UseDriveActionsOptions = {}) {
    const router = useRouter()
    const { folderId, onFileUploaded, onFolderCreated, onFolderRenamed, onFileRenamed, onCurrentFolderRenamed, onItemMoved, onItemDeleted } = options

    const [loadingFileIds, setLoadingFileIds] = useState<Set<string>>(new Set())
    const [popoverOpen, setPopoverOpen] = useState(false)
    const [folderDialogOpen, setFolderDialogOpen] = useState(false)
    const [folderName, setFolderName] = useState('')
    const [creatingFolder, setCreatingFolder] = useState(false)
    const [moveDialogOpen, setMoveDialogOpen] = useState(false)
    const [itemToMove, setItemToMove] = useState<File | Folder | null>(null)

    const {
        uploadFile: resumableUploadFile,
        cancelUpload,
        dismissProgress,
        progress: uploadProgress,
        isUploading: uploading
    } = useResumableUpload({
        onSuccess: async (file) => {
            if (onFileUploaded) {
                await onFileUploaded()
            }
        },
        onError: (error) => {
        },
    })

    const handleLogout = async () => {
        try {
            await authService.logout()
            router.push('/login')
        } catch (error) {
            Cookies.remove('access_token')
            router.push('/login')
        }
    }

    const handleFileUpload = useCallback(async (event: React.ChangeEvent<HTMLInputElement>) => {
        const selectedFile = event.target.files?.[0]
        if (!selectedFile) return

        setPopoverOpen(false)
        
        // Use resumable upload for files
        await resumableUploadFile(selectedFile, folderId)
        
        // Reset file input
        event.target.value = ''
    }, [folderId, resumableUploadFile])

    const handleCreateFolder = async () => {
        if (!folderName.trim()) {
            toast.error('Folder name required', {
                description: 'Please enter a folder name',
            })
            return
        }

        setCreatingFolder(true)
        try {
            await folderService.createFolder(folderName.trim(), folderId)
            toast.success('Folder created successfully', {
                description: `${folderName} has been created`,
            })
            
            setFolderName('')
            setFolderDialogOpen(false)
            
            if (onFolderCreated) {
                await onFolderCreated()
            }
        } catch (error) {
            const axiosError = error as AxiosError<{ detail?: string }>
            const errorMessage = axiosError.response?.data?.detail || axiosError.message || 'Failed to create folder'
            toast.error('Failed to create folder', {
                description: errorMessage,
            })
        } finally {
            setCreatingFolder(false)
        }
    }

    const handleFileClick = async (file: File) => {
        if (file.status !== FileStatus.COMPLETED) {
            toast.error('File not available', {
                description: 'This file is not ready for download',
            })
            return
        }

        setLoadingFileIds((prev) => new Set(prev).add(file.id))
        try {
            const downloadUrl = await fileService.getDownloadUrl(file.id)
            window.open(downloadUrl, '_blank')
        } catch (error) {
            const axiosError = error as AxiosError<{ detail?: string }>
            const errorMessage = axiosError.response?.data?.detail || axiosError.message || 'Failed to get download URL'
            toast.error('Error opening file', {
                description: errorMessage,
            })
        } finally {
            setLoadingFileIds((prev) => {
                const newSet = new Set(prev)
                newSet.delete(file.id)
                return newSet
            })
        }
    }

    const handleFolderClick = (folderId: string) => {
        router.push(`/folder/${folderId}`)
    }

    const handleRename = async (item: File | Folder, newName: string) => {
        const isFolder = 'path' in item

        if (isFolder) {
            try {
                await folderService.updateFolder(item.id, newName)
                toast.success('Folder renamed successfully', {
                    description: `Folder renamed to "${newName}"`,
                })

                // Refresh folders
                if (onFolderRenamed) await onFolderRenamed()
                if (onCurrentFolderRenamed) await onCurrentFolderRenamed()
            } catch (error) {
                const axiosError = error as AxiosError<{ detail?: string }>
                const errorMessage = axiosError.response?.data?.detail || axiosError.message || 'Failed to rename folder'
                toast.error('Failed to rename folder', {
                    description: errorMessage,
                })
            }
        } else {
            try {
                await fileService.updateFile(item.id, newName)
                toast.success('File renamed successfully', {
                    description: `File renamed to "${newName}"`,
                })

                // Refresh files
                if (onFileRenamed) await onFileRenamed()
            } catch (error) {
                const axiosError = error as AxiosError<{ detail?: string }>
                const errorMessage = axiosError.response?.data?.detail || axiosError.message || 'Failed to rename file'
                toast.error('Failed to rename file', {
                    description: errorMessage,
                })
            }
        }
    }

    const handleMoveClick = (item: File | Folder) => {
        setItemToMove(item)
        setMoveDialogOpen(true)
    }

    const handleMove = async (item: File | Folder, destinationFolderId: string | null) => {
        const isFolder = 'path' in item

        try {
            if (isFolder) {
                await folderService.moveFolder(item.id, destinationFolderId)
                toast.success('Folder moved successfully', {
                    description: `Folder moved to ${destinationFolderId ? 'selected location' : 'root'}`,
                })
            } else {
                await fileService.moveFile(item.id, destinationFolderId)
                toast.success('File moved successfully', {
                    description: `File moved to ${destinationFolderId ? 'selected location' : 'root'}`,
                })
            }

            // Refresh items
            if (onItemMoved) await onItemMoved()
        } catch (error) {
            const axiosError = error as AxiosError<{ detail?: string }>
            const errorMessage = axiosError.response?.data?.detail || axiosError.message || 'Failed to move item'
            toast.error('Failed to move item', {
                description: errorMessage,
            })
        }
    }

    const handleDelete = async (item: File | Folder) => {
        try {
            const isFolder = 'path' in item
    
            if (isFolder) {
                await folderService.deleteFolder(item.id)
                toast.success('Folder deleted successfully', {
                    description: `Folder deleted`,
                })
            } else {
                await fileService.deleteFile(item.id)
                toast.success('File deleted successfully', {
                    description: `File deleted`,
                })
            }

            if(onItemDeleted) {
                await onItemDeleted()
            }
        } catch (error) {
            const axiosError = error as AxiosError<{ detail?: string }>
            const errorMessage = axiosError.response?.data?.detail || axiosError.message || 'Failed to delete item'
            toast.error('Failed to delete item', {
                description: errorMessage,
            })
        }
    }

    return {
        uploading,
        uploadProgress,
        cancelUpload,
        dismissProgress,
        loadingFileIds,
        popoverOpen,
        setPopoverOpen,
        folderDialogOpen,
        setFolderDialogOpen,
        folderName,
        setFolderName,
        creatingFolder,
        moveDialogOpen,
        setMoveDialogOpen,
        itemToMove,
        handleLogout,
        handleFileUpload,
        handleCreateFolder,
        handleFileClick,
        handleFolderClick,
        handleRename,
        handleMoveClick,
        handleMove,
        handleDelete
    }
}

