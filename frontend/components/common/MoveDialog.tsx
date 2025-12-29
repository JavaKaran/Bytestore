import { useState, useEffect } from 'react'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Folder as FolderIcon, Home } from 'lucide-react'
import { folderService } from '@/services/folder'
import { toast } from 'sonner'
import { AxiosError } from 'axios'
import type { File, Folder } from '@/lib/types'

interface MoveDialogProps {
    open: boolean
    onOpenChange: (open: boolean) => void
    item: File | Folder | null
    onMove: (item: File | Folder, destinationFolderId: string | null) => void
}

export function MoveDialog({ open, onOpenChange, item, onMove }: MoveDialogProps) {
    const [folders, setFolders] = useState<Folder[]>([])
    const [loading, setLoading] = useState(false)
    const [selectedFolderId, setSelectedFolderId] = useState<string | null | undefined>(undefined)

    const isFolder = item && 'path' in item
    const currentItemId = item?.id
    const currentParentId = item ? (isFolder ? (item as Folder).parent_folder_id : (item as File).folder_id) : undefined

    useEffect(() => {
        if (open) {
            loadFolders()
            setSelectedFolderId(undefined)
        }
    }, [open])

    const loadFolders = async () => {
        setLoading(true)
        try {
            const allFolders = await folderService.getAllFolders()
            setFolders(allFolders)
        } catch (error) {
            const axiosError = error as AxiosError<{ detail?: string }>
            const errorMessage = axiosError.response?.data?.detail || axiosError.message || 'Failed to load folders'
            toast.error('Error', {
                description: errorMessage,
            })
        } finally {
            setLoading(false)
        }
    }

    const handleMove = () => {
        if (item && selectedFolderId !== undefined) {
            onMove(item, selectedFolderId)
            onOpenChange(false)
        }
    }

    const isFolderDisabled = (folderId: string) => {
        if (isFolder && currentItemId === folderId) {
            return true
        }

        if (currentParentId === folderId) {
            return true
        }

        if (isFolder && item) {
            const currentFolder = item as Folder
            const folder = folders.find(f => f.id === folderId)
            if (folder && folder.path.startsWith(currentFolder.path + '/')) {
                return true
            }
        }

        return false
    }

    const isRootDisabled = currentParentId === null || currentParentId === undefined

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-[600px]">
                <DialogHeader>
                    <DialogTitle>Move {isFolder ? 'Folder' : 'File'}</DialogTitle>
                </DialogHeader>
                <div className="py-4">
                    {loading ? (
                        <div className="text-center py-8 text-muted-foreground">
                            Loading folders...
                        </div>
                    ) : (
                        <div className="space-y-1 max-h-[400px] overflow-y-auto">
                            {/* Root option */}
                            <button
                                className={`w-full flex items-center gap-3 px-3 py-2 text-sm rounded-sm transition-colors ${isRootDisabled
                                        ? 'opacity-50 cursor-not-allowed'
                                        : 'hover:bg-primary/10'
                                    } ${selectedFolderId === null ? 'bg-primary/10' : ''
                                    }`}
                                onClick={() => !isRootDisabled && setSelectedFolderId(null)}
                                disabled={isRootDisabled}
                            >
                                <Home className="h-4 w-4 text-primary" />
                                <span>ByteStore</span>
                            </button>

                            {/* Folder list */}
                            {folders.map((folder) => {
                                const disabled = isFolderDisabled(folder.id)
                                return (
                                    <button
                                        key={folder.id}
                                        className={`w-full flex items-center gap-3 px-3 py-2 text-sm rounded-sm transition-colors ${disabled
                                                ? 'opacity-50 cursor-not-allowed'
                                                : 'hover:bg-primary/10'
                                            } ${selectedFolderId === folder.id ? 'bg-primary/10' : ''
                                            }`}
                                        onClick={() => !disabled && setSelectedFolderId(folder.id)}
                                        disabled={disabled}
                                    >
                                        <FolderIcon className="h-4 w-4 text-primary" />
                                        <span className="truncate">
                                            {folder.name}
                                        </span>
                                    </button>
                                )
                            })}
                        </div>
                    )}
                </div>
                <DialogFooter>
                    <Button
                        variant="outline"
                        onClick={() => onOpenChange(false)}
                    >
                        Cancel
                    </Button>
                    <Button
                        onClick={handleMove}
                        disabled={loading || selectedFolderId === undefined}
                    >
                        Move
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    )
}

