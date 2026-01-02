import { Upload } from "lucide-react"
import { Progress } from "@/components/ui/progress"

interface DropZoneOverlayProps {
  isDragging: boolean
  isUploading: boolean
  uploadProgress?: {
    current: number
    total: number
  }
}

export function DropZoneOverlay({ isDragging, isUploading, uploadProgress }: DropZoneOverlayProps) {
  if (!isDragging && !isUploading) return null

  return (
    <div
      className="fixed inset-0 z-50 pointer-events-none"
      style={{ backgroundColor: isDragging ? 'rgba(0, 0, 0, 0.5)' : 'rgba(0, 0, 0, 0.3)' }}
    >
      <div className="h-full flex items-center justify-center">
        <div className="bg-background border-2 border-dashed border-primary rounded-lg p-8 text-center">
          <Upload className={`h-16 w-16 mx-auto mb-4 ${isUploading ? 'animate-pulse' : 'animate-bounce'}`} />

          {isDragging && (
            <>
              <h3 className="text-xl font-semibold mb-2">Drop files here</h3>
              <p className="text-muted-foreground">
                Drop one or more documents to upload them to this matrix
              </p>
            </>
          )}

          {isUploading && uploadProgress && (
            <>
              <h3 className="text-xl font-semibold mb-2">Uploading documents...</h3>
              <p className="text-muted-foreground">
                Uploading {uploadProgress.current} of {uploadProgress.total} files
              </p>
              <div className="mt-4 w-64">
                <Progress
                  value={(uploadProgress.current / uploadProgress.total) * 100}
                  className="h-2"
                />
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}