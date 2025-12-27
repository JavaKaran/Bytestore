import { ReactNode } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { Popover, PopoverTrigger, PopoverContent } from '@/components/ui/popover'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { ItemCard } from '@/components/common/ItemCard'
import { MoveDialog } from '@/components/common/MoveDialog'
import { UploadProgress } from '@/components/common/UploadProgress'
import { LogOut, User as UserIcon, FolderPlus, FileUp, Plus, ArrowLeft } from 'lucide-react'
import type { User, Folder, File, UploadProgress as UploadProgressType } from '@/lib/types'

interface DriveLayoutProps {
    user: User | null
    title: string
    subtitle?: string
    showBackButton?: boolean
    onBackClick?: () => void
    uploading: boolean
    uploadProgress: UploadProgressType | null
    uploadPaused: boolean
    onPauseUpload: () => void
    onResumeUpload: () => void
    onCancelUpload: () => Promise<void>
    onDismissProgress: () => void
    popoverOpen: boolean
    setPopoverOpen: (open: boolean) => void
    folderDialogOpen: boolean
    setFolderDialogOpen: (open: boolean) => void
    folderName: string
    setFolderName: (name: string) => void
    creatingFolder: boolean
    moveDialogOpen: boolean
    setMoveDialogOpen: (open: boolean) => void
    itemToMove: File | Folder | null
    handleLogout: () => void
    handleFileUpload: (event: React.ChangeEvent<HTMLInputElement>) => void
    handleCreateFolder: () => void
    itemsLoading: boolean
    folders: Folder[]
    files: File[]
    loadingFileIds: Set<string>
    onFolderClick: (folderId: string) => void
    onFileClick: (file: File) => void
    onRename: (item: File | Folder, newName: string) => void
    onMoveClick: (item: File | Folder) => void
    onMove: (item: File | Folder, destinationFolderId: string | null) => void
    onDelete: (item: File | Folder) => void
}

export function DriveLayout({
    user,
    title,
    subtitle = 'Manage your files and folders from here',
    showBackButton = false,
    onBackClick,
    uploading,
    uploadProgress,
    uploadPaused,
    onPauseUpload,
    onResumeUpload,
    onDismissProgress,
    onCancelUpload,
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
    itemsLoading,
    folders,
    files,
    loadingFileIds,
    onFolderClick,
    onFileClick,
    onRename,
    onMoveClick,
    onMove,
    onDelete
}: DriveLayoutProps) {
    return (
        <div className="min-h-screen bg-background">
            <div className="border-b border-border">
                <div className="container mx-auto px-4 py-4 flex items-center justify-between">
                    <h1 className="text-2xl font-semibold">G-Drive</h1>
                    <div className="flex items-center gap-4">
                        {user && (
                            <div className="flex items-center gap-2 text-sm text-muted-foreground">
                                <UserIcon className="h-4 w-4" />
                                <span>{user.username}</span>
                            </div>
                        )}
                        <Button variant="outline" onClick={handleLogout}>
                            <LogOut className="h-4 w-4 mr-2" />
                            Logout
                        </Button>
                    </div>
                </div>
            </div>

            <div className="container mx-auto px-4 py-12">
                <div className="mb-8 flex items-center justify-between">
                    <div className="flex items-center gap-4">
                        {showBackButton && onBackClick && (
                            <Button
                                variant="outline"
                                size="sm"
                                onClick={onBackClick}
                            >
                                <ArrowLeft className="h-4 w-4 mr-2" />
                                Back
                            </Button>
                        )}
                        <div>
                            <h2 className="text-2xl font-semibold mb-2">{title}</h2>
                            <p className="text-muted-foreground">{subtitle}</p>
                        </div>
                    </div>
                    <Popover open={popoverOpen} onOpenChange={setPopoverOpen}>
                        <PopoverTrigger asChild>
                            <Button disabled={uploading}>
                                <Plus className="h-4 w-4 mr-2" />
                                New
                            </Button>
                        </PopoverTrigger>
                        <PopoverContent className="w-56 p-2" align="end">
                            <div className="space-y-1">
                                <input
                                    type="file"
                                    id="file-upload"
                                    className="hidden"
                                    onChange={handleFileUpload}
                                    disabled={uploading}
                                />
                                <button
                                    className="w-full flex items-center gap-2 px-3 py-2 text-sm rounded-sm hover:bg-accent transition-colors"
                                    onClick={() => document.getElementById('file-upload')?.click()}
                                    disabled={uploading}
                                >
                                    <FileUp className="h-4 w-4" />
                                    Upload File
                                </button>
                                <div className="border-t border-border my-1" />
                                <button
                                    className="w-full flex items-center gap-2 px-3 py-2 text-sm rounded-sm hover:bg-accent transition-colors"
                                    onClick={() => {
                                        setFolderDialogOpen(true)
                                        setPopoverOpen(false)
                                    }}
                                    disabled={uploading}
                                >
                                    <FolderPlus className="h-4 w-4" />
                                    Upload Folder
                                </button>
                            </div>
                        </PopoverContent>
                    </Popover>
                </div>

                <Dialog open={folderDialogOpen} onOpenChange={setFolderDialogOpen}>
                    <DialogContent>
                        <DialogHeader>
                            <DialogTitle>Create New Folder</DialogTitle>
                        </DialogHeader>
                        <div className="space-y-4 py-4">
                            <div className="space-y-2">
                                <Label htmlFor="folder-name">Folder Name</Label>
                                <Input
                                    id="folder-name"
                                    placeholder="Enter folder name"
                                    value={folderName}
                                    onChange={(e) => setFolderName(e.target.value)}
                                    onKeyDown={(e) => {
                                        if (e.key === 'Enter' && folderName.trim()) {
                                            handleCreateFolder()
                                        }
                                    }}
                                    disabled={creatingFolder}
                                    autoFocus
                                />
                            </div>
                        </div>
                        <DialogFooter>
                            <Button
                                variant="outline"
                                onClick={() => {
                                    setFolderDialogOpen(false)
                                    setFolderName('')
                                }}
                                disabled={creatingFolder}
                            >
                                Cancel
                            </Button>
                            <Button
                                onClick={handleCreateFolder}
                                disabled={creatingFolder || !folderName.trim()}
                            >
                                {creatingFolder ? 'Creating...' : 'Create Folder'}
                            </Button>
                        </DialogFooter>
                    </DialogContent>
                </Dialog>

                <Card>
                    <CardHeader>
                        <CardTitle>All Files and Folders</CardTitle>
                    </CardHeader>
                    <CardContent>
                        {itemsLoading ? (
                            <div className="text-center py-8 text-muted-foreground">
                                Loading items...
                            </div>
                        ) : folders.length === 0 && files.length === 0 ? (
                            <div className="text-center py-8 text-muted-foreground">
                                No folders or files yet. Start by creating a folder or uploading a file.
                            </div>
                        ) : (
                            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                                {/* Folders */}
                                {folders.map((folder) => (
                                    <ItemCard
                                        key={folder.id}
                                        item={folder}
                                        onClick={() => onFolderClick(folder.id)}
                                        onRename={onRename}
                                        onMove={onMoveClick}
                                        onDelete={onDelete}
                                    />
                                ))}

                                {/* Files */}
                                {files.map((file) => (
                                    <ItemCard
                                        key={file.id}
                                        item={file}
                                        isLoading={loadingFileIds.has(file.id)}
                                        onClick={() => onFileClick(file)}
                                        onRename={onRename}
                                        onMove={onMoveClick}
                                        onDelete={onDelete}
                                    />
                                ))}
                            </div>
                        )}
                    </CardContent>
                </Card>

                <MoveDialog
                    open={moveDialogOpen}
                    onOpenChange={setMoveDialogOpen}
                    item={itemToMove}
                    onMove={onMove}
                />

                {/* Upload Progress Indicator */}
                {uploadProgress && (
                    <UploadProgress
                        progress={uploadProgress}
                        isPaused={uploadPaused}
                        onPause={onPauseUpload}
                        onResume={onResumeUpload}
                        onCancel={onCancelUpload}
                        onDismiss={onDismissProgress}
                    />
                )}
            </div>
        </div>
    )
}

