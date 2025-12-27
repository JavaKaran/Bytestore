import { useState } from 'react'
import { Popover, PopoverTrigger, PopoverContent } from '@/components/ui/popover'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Button } from '@/components/ui/button'
import { MoreVertical, Pencil, FolderInput, Trash2 } from 'lucide-react'
import type { File, Folder } from '@/lib/types'

interface ItemCardMenuProps {
    item: File | Folder
    onRename?: (item: File | Folder, newName: string) => void
    onMove?: (item: File | Folder) => void,
    onDelete?: (item: File | Folder) => void
}

export function ItemCardMenu({ item, onRename, onMove, onDelete }: ItemCardMenuProps) {
    const [popoverOpen, setPopoverOpen] = useState(false)
    const [renameDialogOpen, setRenameDialogOpen] = useState(false)
    const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
    const [newName, setNewName] = useState('')

    const isFolder = 'path' in item
    const currentName = isFolder ? (item as Folder).name : (item as File).name

    const handleRenameClick = (e: React.MouseEvent) => {
        e.stopPropagation()
        setNewName(currentName)
        setRenameDialogOpen(true)
        setPopoverOpen(false)
    }

    const handleMoveClick = (e: React.MouseEvent) => {
        e.stopPropagation()
        setPopoverOpen(false)
        if (onMove) {
            onMove(item)
        }
    }

    const handleDeleteClick = (e: React.MouseEvent) => {
        e.stopPropagation()
        setDeleteDialogOpen(true)
        setPopoverOpen(false)
    }

    const handleDeleteConfirm = () => {
        if (onDelete) {
            onDelete(item)
        }
        setDeleteDialogOpen(false)
    }

    const handleRenameSubmit = () => {
        if (newName.trim() && newName.trim() !== currentName && onRename) {
            onRename(item, newName.trim())
            setRenameDialogOpen(false)
            setNewName('')
        }
    }

    if (!onRename && !onMove && !onDelete) {
        return null
    }

    return (
        <>
            <Popover open={popoverOpen} onOpenChange={setPopoverOpen}>
                <PopoverTrigger asChild>
                    <button
                        className="p-1 rounded transition-colors"
                        onClick={(e) => {
                            e.stopPropagation()
                            setPopoverOpen(true)
                        }}
                    >
                        <MoreVertical className="h-4 w-4 text-muted-foreground hover:text-foreground transition-colors" />
                    </button>
                </PopoverTrigger>
                <PopoverContent className="w-40 p-1" align="end" onClick={(e) => e.stopPropagation()}>
                    <div className="space-y-1">
                        {onRename && (
                            <button
                                className="w-full flex items-center gap-2 px-3 py-2 text-sm rounded-sm hover:bg-accent transition-colors"
                                onClick={handleRenameClick}
                            >
                                <Pencil className="h-4 w-4" />
                                Rename
                            </button>
                        )}
                        {onMove && (
                            <button
                                className="w-full flex items-center gap-2 px-3 py-2 text-sm rounded-sm hover:bg-accent transition-colors"
                                onClick={handleMoveClick}
                            >
                                <FolderInput className="h-4 w-4" />
                                Move
                            </button>
                        )}
                        {onDelete && (
                            <>
                                <div className="border-t border-border my-1" />
                                <button
                                    className="w-full flex items-center gap-2 px-3 py-2 text-sm rounded-sm text-destructive hover:bg-destructive/10 transition-colors"
                                    onClick={handleDeleteClick}
                                >
                                    <Trash2 className="h-4 w-4" />
                                    Delete
                                </button>
                            </>
                        )}
                    </div>
                </PopoverContent>
            </Popover>

            <Dialog open={renameDialogOpen} onOpenChange={setRenameDialogOpen}>
                <DialogContent onClick={(e) => e.stopPropagation()}>
                    <DialogHeader>
                        <DialogTitle>Rename {isFolder ? 'Folder' : 'File'}</DialogTitle>
                    </DialogHeader>
                    <div className="space-y-4 py-4">
                        <div className="space-y-2">
                            <Label htmlFor="rename-input">Name</Label>
                            <Input
                                id="rename-input"
                                value={newName}
                                onChange={(e) => setNewName(e.target.value)}
                                onKeyDown={(e) => {
                                    if (e.key === 'Enter' && newName.trim() && newName.trim() !== currentName) {
                                        handleRenameSubmit()
                                    }
                                }}
                                autoFocus
                            />
                        </div>
                    </div>
                    <DialogFooter>
                        <Button
                            variant="outline"
                            onClick={() => {
                                setRenameDialogOpen(false)
                                setNewName('')
                            }}
                        >
                            Cancel
                        </Button>
                        <Button
                            onClick={handleRenameSubmit}
                            disabled={!newName.trim() || newName.trim() === currentName}
                        >
                            Rename
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* Delete Confirmation Dialog */}
            <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
                <DialogContent onClick={(e) => e.stopPropagation()}>
                    <DialogHeader>
                        <DialogTitle>Delete {isFolder ? 'Folder' : 'File'}</DialogTitle>
                        <DialogDescription>
                            Are you sure you want to delete <span className="font-medium text-foreground">"{currentName}"</span>?
                            {isFolder && ' This will also delete all files and folders inside it.'}
                            {' '}This action cannot be undone.
                        </DialogDescription>
                    </DialogHeader>
                    <DialogFooter>
                        <Button
                            variant="outline"
                            onClick={() => setDeleteDialogOpen(false)}
                        >
                            Cancel
                        </Button>
                        <Button
                            variant="destructive"
                            onClick={handleDeleteConfirm}
                        >
                            Delete
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </>
    )
}

