interface DocumentHeaderProps {
  filename: string
  label?: string | null
  className?: string
}

export function DocumentHeader({ 
  filename, 
  label,
  className = '' 
}: DocumentHeaderProps) {
  return (
    <div className={`p-2 min-h-[60px] h-full flex flex-col justify-start gap-1 ${className}`}>
      <span className="text-xs font-medium line-clamp-3">
        {label || filename}
      </span>
      {label && (
        <span className="text-xs text-muted-foreground line-clamp-2">
          {filename}
        </span>
      )}
    </div>
  )
}