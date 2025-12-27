'use client'

import { useDriveData } from '@/lib/hooks/useDriveData'
import { useDriveActions } from '@/lib/hooks/useDriveActions'
import { DriveLayout } from '@/components/layout/DriveLayout'

export default function DashboardPage() {
    const {
        user,
        folders,
        files,
        loading,
        itemsLoading,
        refreshFolders,
        refreshFiles,
    } = useDriveData()

    const {
        uploading,
        uploadProgress,
        uploadPaused,
        pauseUpload,
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
        onFileUploaded: refreshFiles,
        onFolderCreated: refreshFolders,
        onFolderRenamed: refreshFolders,
        onFileRenamed: refreshFiles,
        onItemMoved: async () => {
            await Promise.all([refreshFolders(), refreshFiles()])
        },
        onItemDeleted: async () => {
            await Promise.all([refreshFolders(), refreshFiles()])
        },
    })

    // Placeholder for resume - actual file would need to be re-selected
    const handleResumeUpload = () => {
        // In a real implementation, you'd prompt the user to re-select the file
        // or store the file reference. For now, just log a message.
        console.log('Resume functionality requires file re-selection')
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
            title={`Welcome back, ${user?.username}!`}
            uploading={uploading}
            uploadProgress={uploadProgress}
            uploadPaused={uploadPaused}
            onPauseUpload={pauseUpload}
            onResumeUpload={handleResumeUpload}
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
