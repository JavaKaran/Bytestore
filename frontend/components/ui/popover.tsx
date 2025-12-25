"use client"

import * as React from "react"
import { cn } from "@/lib/utils"

interface PopoverProps {
    children: React.ReactNode
    open?: boolean
    onOpenChange?: (open: boolean) => void
}

interface PopoverContextValue {
    open: boolean
    setOpen: (open: boolean) => void
}

const PopoverContext = React.createContext<PopoverContextValue | undefined>(undefined)

function usePopover() {
    const context = React.useContext(PopoverContext)
    if (!context) {
        throw new Error("Popover components must be used within a Popover")
    }
    return context
}

const Popover = React.forwardRef<
    HTMLDivElement,
    PopoverProps
>(({ children, open: openProp, onOpenChange }, ref) => {
    const [open, setOpen] = React.useState(openProp ?? false)

    React.useEffect(() => {
        if (openProp !== undefined) {
            setOpen(openProp)
        }
    }, [openProp])

    const handleOpenChange = React.useCallback((newOpen: boolean) => {
        setOpen(newOpen)
        onOpenChange?.(newOpen)
    }, [onOpenChange])

    const value = React.useMemo(() => ({
        open,
        setOpen: handleOpenChange,
    }), [open, handleOpenChange])

    return (
        <PopoverContext.Provider value={value}>
            <div ref={ref} className="relative">
                {children}
            </div>
        </PopoverContext.Provider>
    )
})
Popover.displayName = "Popover"

interface PopoverTriggerProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  asChild?: boolean
}

const PopoverTrigger = React.forwardRef<
  HTMLButtonElement,
  PopoverTriggerProps
>(({ className, children, asChild, ...props }, ref) => {
  const { open, setOpen } = usePopover()

  if (asChild && React.isValidElement(children)) {
    return React.cloneElement(children as React.ReactElement<any>, {
      ref,
      onClick: (e: React.MouseEvent) => {
        setOpen(!open)
        if (children.props.onClick) {
          children.props.onClick(e)
        }
      },
      ...props,
    })
  }

  return (
    <button
      ref={ref}
      type="button"
      className={className}
      onClick={() => setOpen(!open)}
      {...props}
    >
      {children}
    </button>
  )
})
PopoverTrigger.displayName = "PopoverTrigger"

const PopoverContent = React.forwardRef<
    HTMLDivElement,
    React.HTMLAttributes<HTMLDivElement> & {
        align?: "start" | "center" | "end"
        side?: "top" | "bottom" | "left" | "right"
    }
>(({ className, align = "end", side = "bottom", children, ...props }, ref) => {
    const { open, setOpen } = usePopover()
    const contentRef = React.useRef<HTMLDivElement>(null)

    // Combine refs
    React.useImperativeHandle(ref, () => contentRef.current as HTMLDivElement)

    React.useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            const target = event.target as Node
            // Check if click is inside the popover content
            const isClickInsideContent = contentRef.current?.contains(target)
            
            // Check if click is inside the popover container (which includes the trigger)
            let isClickInsidePopover = false
            if (contentRef.current) {
                const popoverContainer = contentRef.current.closest('.relative')
                if (popoverContainer) {
                    isClickInsidePopover = popoverContainer.contains(target)
                }
            }
            
            // Close if click is outside both content and popover container
            if (!isClickInsidePopover) {
                setOpen(false)
            }
        }

        if (open) {
            // Use a small delay to avoid immediate closing when opening
            const timeoutId = setTimeout(() => {
                document.addEventListener("mousedown", handleClickOutside)
            }, 100)
            
            return () => {
                clearTimeout(timeoutId)
                document.removeEventListener("mousedown", handleClickOutside)
            }
        }
    }, [open, setOpen])

    if (!open) return null

    return (
        <div
            ref={contentRef}
            className={cn(
                "absolute z-50 min-w-[8rem] overflow-hidden rounded-md border bg-popover p-1 text-popover-foreground shadow-md",
                side === "top" && "bottom-full mb-2",
                side === "bottom" && "top-full mt-2",
                side === "left" && "right-full mr-2",
                side === "right" && "left-full ml-2",
                align === "start" && side === "bottom" && "left-0",
                align === "end" && side === "bottom" && "right-0",
                align === "center" && side === "bottom" && "left-1/2 -translate-x-1/2",
                className
            )}
            {...props}
        >
            {children}
        </div>
    )
})
PopoverContent.displayName = "PopoverContent"

export { Popover, PopoverTrigger, PopoverContent }

