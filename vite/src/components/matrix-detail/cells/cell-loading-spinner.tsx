export function CellLoadingSpinner() {
  return (
    <div className="relative w-3 h-3">
      <div className="absolute inset-0 border border-muted/30 rounded-full"></div>
      <div className="absolute inset-0 border border-muted-foreground/40 border-t-transparent rounded-full animate-spin"></div>
    </div>
  )
}
