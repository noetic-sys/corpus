"use client"

import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

const Table = React.forwardRef<
  HTMLTableElement,
  React.HTMLAttributes<HTMLTableElement> & {
    noWrapper?: boolean;
    divClassname?: string;
  }
>(({ className, noWrapper, divClassname, ...props }, ref) => {
  if (noWrapper) {
    return (
      <table
        ref={ref}
        data-slot="table"
        className={cn("w-full caption-bottom text-sm", className)}
        {...props}
      />
    );
  }

  return (
    <div
      data-slot="table-container"
      className={cn("relative w-full overflow-x-auto", divClassname)}
    >
      <table
        ref={ref}
        data-slot="table"
        className={cn("w-full caption-bottom text-sm", className)}
        {...props}
      />
    </div>
  );
})
Table.displayName = "Table"

const tableHeaderVariants = cva(
  "[&_tr]:border-b",
  {
    variants: {
      variant: {
        default: "",
        blocky: "[&_tr]:border-b-2 [&_tr]:border-border",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
)

function TableHeader({ 
  className, 
  variant,
  ...props 
}: React.ComponentProps<"thead"> & VariantProps<typeof tableHeaderVariants>) {
  return (
    <thead
      data-slot="table-header"
      className={cn(tableHeaderVariants({ variant }), className)}
      {...props}
    />
  )
}

const tableBodyVariants = cva(
  "[&_tr:last-child]:border-0",
  {
    variants: {
      variant: {
        default: "",
        blocky: "[&_tr:last-child]:border-b [&_tr]:border-border",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
)

function TableBody({ 
  className, 
  variant,
  ...props 
}: React.ComponentProps<"tbody"> & VariantProps<typeof tableBodyVariants>) {
  return (
    <tbody
      data-slot="table-body"
      className={cn(tableBodyVariants({ variant }), className)}
      {...props}
    />
  )
}

function TableFooter({ className, ...props }: React.ComponentProps<"tfoot">) {
  return (
    <tfoot
      data-slot="table-footer"
      className={cn(
        "bg-muted/50 border-t font-medium [&>tr]:last:border-b-0",
        className
      )}
      {...props}
    />
  )
}

const tableRowVariants = cva(
  "border-b transition-colors",
  {
    variants: {
      variant: {
        default: "hover:bg-muted/50 data-[state=selected]:bg-muted",
        blocky: "hover:bg-muted/30 data-[state=selected]:bg-muted border-border",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
)

function TableRow({ 
  className, 
  variant,
  ...props 
}: React.ComponentProps<"tr"> & VariantProps<typeof tableRowVariants>) {
  return (
    <tr
      data-slot="table-row"
      className={cn(tableRowVariants({ variant }), className)}
      {...props}
    />
  )
}

const tableHeadVariants = cva(
  "text-foreground h-10 px-2 text-left align-middle font-medium whitespace-nowrap [&:has([role=checkbox])]:pr-0 [&>[role=checkbox]]:translate-y-[2px]",
  {
    variants: {
      variant: {
        default: "",
        blocky: "border-r border-border bg-muted/50",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
)

function TableHead({ 
  className, 
  variant,
  ...props 
}: React.ComponentProps<"th"> & VariantProps<typeof tableHeadVariants>) {
  return (
    <th
      data-slot="table-head"
      className={cn(tableHeadVariants({ variant }), className)}
      {...props}
    />
  )
}

const tableCellVariants = cva(
  "p-2 align-middle whitespace-nowrap [&:has([role=checkbox])]:pr-0 [&>[role=checkbox]]:translate-y-[2px]",
  {
    variants: {
      variant: {
        default: "",
        blocky: "border-r border-border",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
)

function TableCell({ 
  className, 
  variant,
  ...props 
}: React.ComponentProps<"td"> & VariantProps<typeof tableCellVariants>) {
  return (
    <td
      data-slot="table-cell"
      className={cn(tableCellVariants({ variant }), className)}
      {...props}
    />
  )
}

function TableCaption({
  className,
  ...props
}: React.ComponentProps<"caption">) {
  return (
    <caption
      data-slot="table-caption"
      className={cn("text-muted-foreground mt-4 text-sm", className)}
      {...props}
    />
  )
}

export {
  Table,
  TableHeader,
  TableBody,
  TableFooter,
  TableHead,
  TableRow,
  TableCell,
  TableCaption,
}
