import { Card, CardContent } from '@/components/ui/card'
import { Folder as FolderIcon } from 'lucide-react'
import { getFileIcon, formatFileSize } from '@/lib/utils'
import { ItemCardMenu } from './ItemCardMenu'
import type { File, Folder } from '@/lib/types'
import type { LucideIcon } from 'lucide-react'

interface ItemCardProps {
    item: File | Folder
    isLoading?: boolean
    onClick?: () => void
    onRename?: (item: File | Folder, newName: string) => void
    onMove?: (item: File | Folder) => void
    onDelete?: (item: File | Folder) => void
}

export function ItemCard({ item, isLoading = false, onClick, onRename, onMove, onDelete }: ItemCardProps) {
    const isFile = 'size' in item && 'mime' in item
    const isFolder = 'path' in item

    let Icon: LucideIcon
    let iconBgClass: string
    let iconColorClass: string
    let title: string
    let subtitle: string | React.ReactNode

    if (isFolder) {
        const folder = item as Folder
        Icon = FolderIcon
        iconBgClass = 'bg-primary/10'
        iconColorClass = 'text-primary'
        title = folder.name
        subtitle = 'Folder'
    } else {
        const file = item as File
        Icon = getFileIcon(file.name, file.mime)
        iconBgClass = 'bg-secondary/10'
        iconColorClass = 'text-secondary-foreground'
        title = file.name
        subtitle = isLoading ? 'Loading...' : formatFileSize(file.size)
    }

    return (
        <Card
            className="cursor-pointer hover:bg-accent transition-colors relative group"
            onClick={onClick}
        >
            <CardContent className="p-4">
                <div className="flex items-center gap-3">
                    <div className={`rounded-lg ${iconBgClass} p-2`}>
                        <Icon className={`h-5 w-5 ${iconColorClass}`} />
                    </div>
                    <div className="flex-1 min-w-0">
                        <p className="font-medium truncate" title={title}>{title}</p>
                        <p className="text-xs text-muted-foreground">{subtitle}</p>
                    </div>
                    <ItemCardMenu item={item} onRename={onRename} onMove={onMove} onDelete={onDelete} />
                </div>
            </CardContent>
        </Card>
    )
}

