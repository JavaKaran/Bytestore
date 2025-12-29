import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { toast } from 'sonner'
import Cookies from 'js-cookie'
import { AxiosError } from 'axios'
import { authService } from '@/services/auth'
import { folderService } from '@/services/folder'
import { fileService } from '@/services/file'
import type { User, Folder, File } from '@/lib/types'

interface UseDriveDataOptions {
    folderId?: string
}

export function useDriveData(options: UseDriveDataOptions = {}) {
    const router = useRouter()
    const { folderId } = options

    const [user, setUser] = useState<User | null>(null)
    const [currentFolder, setCurrentFolder] = useState<Folder | null>(null)
    const [folders, setFolders] = useState<Folder[]>([])
    const [files, setFiles] = useState<File[]>([])
    const [loading, setLoading] = useState(true)
    const [itemsLoading, setItemsLoading] = useState(true)
    const [storageUsed, setStorageUsed] = useState(0)
    const [storageLimit, setStorageLimit] = useState(0)

    useEffect(() => {
        const token = Cookies.get('access_token')
        if (!token) {
            router.push('/login')
            return
        }

        const fetchData = async () => {
            try {
                const userData = await authService.getCurrentUser()
                setUser(userData)

                if (folderId) {
                    // Fetch folder-specific data
                    const [folderData, folderFolders, folderFiles] = await Promise.all([
                        folderService.getFolderById(folderId),
                        folderService.getFoldersByParent(folderId),
                        fileService.getFilesByFolder(folderId),
                    ])
                    
                    setCurrentFolder(folderData)
                    setFolders(folderFolders)
                    setFiles(folderFiles?.files || [])

                    setStorageUsed(folderFiles?.storage_used || 0)
                    setStorageLimit(folderFiles?.storage_limit || 0)
                } else {
                    // Fetch root data
                    const [rootFolders, rootFiles] = await Promise.all([
                        folderService.getRootFolders(),
                        fileService.getRootFiles(),
                    ])
                    setFolders(rootFolders)
                    setFiles(rootFiles?.files || [])

                    setStorageUsed(rootFiles?.storage_used || 0)
                    setStorageLimit(rootFiles?.storage_limit || 0)
                }
            } catch (error) {
                const axiosError = error as AxiosError<{ detail?: string }>
                const errorMessage = axiosError.response?.data?.detail || axiosError.message || 'Failed to load data'
                toast.error('Error', {
                    description: errorMessage,
                })
                if (folderId) {
                    router.push('/dashboard')
                }
            } finally {
                setLoading(false)
                setItemsLoading(false)
            }
        }

        fetchData()
    }, [router, folderId])

    const refreshFolders = async () => {
        if (folderId) {
            const folderFolders = await folderService.getFoldersByParent(folderId)
            setFolders(folderFolders)
        } else {
            const rootFolders = await folderService.getRootFolders()
            setFolders(rootFolders)
        }
    }

    const refreshFiles = async () => {
        if (folderId) {
            const folderFiles = await fileService.getFilesByFolder(folderId)
            setFiles(folderFiles?.files || [])

            setStorageUsed(folderFiles?.storage_used || 0)
            setStorageLimit(folderFiles?.storage_limit || 0)
        } else {
            const rootFiles = await fileService.getRootFiles()
            setFiles(rootFiles?.files || [])

            setStorageUsed(rootFiles?.storage_used || 0)
            setStorageLimit(rootFiles?.storage_limit || 0)
        }
    }

    const refreshCurrentFolder = async () => {
        if (folderId) {
            const folderData = await folderService.getFolderById(folderId)
            setCurrentFolder(folderData)
        }
    }

    return {
        user,
        currentFolder,
        folders,
        files,
        storageUsed,
        storageLimit,
        loading,
        itemsLoading,
        refreshFolders,
        refreshFiles,
        refreshCurrentFolder,
    }
}

