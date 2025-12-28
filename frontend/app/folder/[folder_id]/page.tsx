'use client'

import { useRouter, useParams } from 'next/navigation'
import { useDriveData } from '@/lib/hooks/useDriveData'
import { useDriveActions } from '@/lib/hooks/useDriveActions'
import { DriveLayout } from '@/components/layout/DriveLayout'

export default function FolderPage() {
    const router = useRouter()
    const params = useParams()
    const folderId = params.folder_id as string
    
    const {
        user,
        currentFolder,
        folders,
        files,
        loading,
        itemsLoading,
        refreshFolders,
        refreshFiles,
        refreshCurrentFolder,
    } = useDriveData({ folderId })

    const {
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
        handleDelete,
    } = useDriveActions({
        folderId,
        onFileUploaded: refreshFiles,
        onFolderCreated: refreshFolders,
        onFolderRenamed: refreshFolders,
        onFileRenamed: refreshFiles,
        onCurrentFolderRenamed: refreshCurrentFolder,
        onItemMoved: async () => {
            await Promise.all([refreshFolders(), refreshFiles()])
        },
        onItemDeleted: async () => {
            await Promise.all([refreshFolders(), refreshFiles()])
        },
    })

    // Placeholder for resume - actual file would need to be re-selected
    const handleResumeUpload = () => {
        console.log('Resume functionality requires file re-selection')
    }

    const handleBackClick = () => {
        if (currentFolder?.parent_folder_id) {
            router.push(`/folder/${currentFolder.parent_folder_id}`)
        } else {
            router.push('/dashboard')
        }
    }

    if (loading) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-background">
                <div className="text-muted-foreground">Loading...</div>
            </div>
        )
    }

    return (
        <DriveLayout
            user={user}
            title={currentFolder ? currentFolder.name : 'Folder'}
            showBackButton
            onBackClick={handleBackClick}
            uploading={uploading}
            uploadProgress={uploadProgress}
            onCancelUpload={cancelUpload}
            onDismissProgress={dismissProgress}
            popoverOpen={popoverOpen}
            setPopoverOpen={setPopoverOpen}
            folderDialogOpen={folderDialogOpen}
            setFolderDialogOpen={setFolderDialogOpen}
            folderName={folderName}
            setFolderName={setFolderName}
            creatingFolder={creatingFolder}
            moveDialogOpen={moveDialogOpen}
            setMoveDialogOpen={setMoveDialogOpen}
            itemToMove={itemToMove}
            handleLogout={handleLogout}
            handleFileUpload={handleFileUpload}
            handleCreateFolder={handleCreateFolder}
            itemsLoading={itemsLoading}
            folders={folders}
            files={files}
            loadingFileIds={loadingFileIds}
            onFolderClick={handleFolderClick}
            onFileClick={handleFileClick}
            onRename={handleRename}
            onMoveClick={handleMoveClick}
            onMove={handleMove}
            onDelete={handleDelete}
        />
    )
}
