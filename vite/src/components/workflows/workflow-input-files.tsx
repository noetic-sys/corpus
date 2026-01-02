import { Upload, Trash2, FileText } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { useRef, useState } from 'react'

interface WorkflowInputFilesProps {
  onFilesChange: (files: File[]) => void
}

export function WorkflowInputFiles({ onFilesChange }: WorkflowInputFilesProps) {
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [selectedFiles, setSelectedFiles] = useState<File[]>([])

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || [])
    const newFiles = [...selectedFiles, ...files]
    setSelectedFiles(newFiles)
    onFilesChange(newFiles)

    // Reset input so same file can be selected again
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  const handleRemoveFile = (index: number) => {
    const newFiles = selectedFiles.filter((_, i) => i !== index)
    setSelectedFiles(newFiles)
    onFilesChange(newFiles)
  }

  return (
    <div className="grid gap-2">
      <Label>Input Files (Templates, Data)</Label>
      <div className="text-sm text-muted-foreground mb-2">
        Upload Excel templates or data files that the workflow agent can use
      </div>

      <div className="space-y-2">
        {selectedFiles.length === 0 ? (
          <div className="text-sm text-muted-foreground">No files selected</div>
        ) : (
          <div className="space-y-2">
            {selectedFiles.map((file, index) => (
              <div
                key={index}
                className="flex items-center justify-between rounded-md border p-2"
              >
                <div className="flex items-center gap-2">
                  <FileText className="h-4 w-4 text-muted-foreground" />
                  <div>
                    <p className="text-sm font-medium">{file.name}</p>
                    <p className="text-xs text-muted-foreground">
                      {(file.size / 1024).toFixed(1)} KB
                    </p>
                  </div>
                </div>
                <Button
                  size="sm"
                  variant="ghost"
                  type="button"
                  onClick={() => handleRemoveFile(index)}
                  style="blocky"
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
            ))}
          </div>
        )}

        <div>
          <input
            ref={fileInputRef}
            type="file"
            onChange={handleFileSelect}
            className="hidden"
            id="workflow-file-upload"
            multiple
          />
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => fileInputRef.current?.click()}
            style="blocky"
          >
            <Upload className="h-4 w-4 mr-2" />
            Select Files
          </Button>
        </div>
      </div>
    </div>
  )
}
