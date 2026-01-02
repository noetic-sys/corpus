'use client'

import * as React from "react"
import { createPortal } from "react-dom"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/lib/utils"

interface DialogProps {
  children: React.ReactNode
  open: boolean
  onOpenChange: (open: boolean) => void
  withoutPortal?: boolean
}

function Dialog({ children, open, onOpenChange, withoutPortal = false }: DialogProps) {
  React.useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onOpenChange(false)
      }
    }

    if (open) {
      document.addEventListener('keydown', handleEscape)
      document.body.style.overflow = 'hidden'
    }

    return () => {
      document.removeEventListener('keydown', handleEscape)
      document.body.style.overflow = 'unset'
    }
  }, [open, onOpenChange])

  if (!open) return null

  const dialogContent = (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div
        className="fixed inset-0 bg-black/50"
        onClick={(e) => {
          e.stopPropagation()
          onOpenChange(false)
        }}
      />
      <div className="relative z-10">
        {children}
      </div>
    </div>
  )

  if (withoutPortal) {
    return dialogContent
  }

  return createPortal(dialogContent, document.body)
}

const dialogContentVariants = cva(
  "bg-background border border-border max-h-[90vh] overflow-auto",
  {
    variants: {
      variant: {
        default: "rounded-lg shadow-lg",
        blocky: "rounded-none border-2 shadow-none",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
)

interface DialogContentProps extends React.HTMLAttributes<HTMLDivElement>, VariantProps<typeof dialogContentVariants> {
  children: React.ReactNode
}

function DialogContent({ children, className, variant, ...props }: DialogContentProps) {
  return (
    <div
      className={cn(dialogContentVariants({ variant }), className)}
      {...props}
    >
      {children}
    </div>
  )
}

interface DialogHeaderProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode
}

function DialogHeader({ children, className, ...props }: DialogHeaderProps) {
  return (
    <div
      className={cn("p-6 pb-0", className)}
      {...props}
    >
      {children}
    </div>
  )
}

interface DialogTitleProps extends React.HTMLAttributes<HTMLHeadingElement> {
  children: React.ReactNode
}

function DialogTitle({ children, className, ...props }: DialogTitleProps) {
  return (
    <h2
      className={cn("text-lg font-semibold", className)}
      {...props}
    >
      {children}
    </h2>
  )
}

interface DialogDescriptionProps extends React.HTMLAttributes<HTMLParagraphElement> {
  children: React.ReactNode
}

function DialogDescription({ children, className, ...props }: DialogDescriptionProps) {
  return (
    <p
      className={cn("text-sm text-text-tertiary mt-2", className)}
      {...props}
    >
      {children}
    </p>
  )
}

interface DialogFooterProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode
}

function DialogFooter({ children, className, ...props }: DialogFooterProps) {
  return (
    <div
      className={cn("p-6 pt-0 flex justify-end gap-2", className)}
      {...props}
    >
      {children}
    </div>
  )
}

export {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
}