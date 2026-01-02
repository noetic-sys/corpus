import { Button } from "@/components/ui/button"
import { Download, X } from "lucide-react"
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { ScrollArea } from "@/components/ui/scroll-area"
import { downloadTableAsCSV } from "@/lib/csv-utils"

interface TableExpandDialogProps {
  tableContent: React.ReactNode
  tableId: string
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function TableExpandDialog({ tableContent, tableId, open, onOpenChange }: TableExpandDialogProps) {
  const handleDownloadCSV = () => {
    downloadTableAsCSV(tableId)
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange} withoutPortal>
      <DialogContent className="max-w-6xl max-h-[90vh] w-[95vw]">
        <DialogHeader>
          <div className="flex items-center justify-between">
            <DialogTitle>Table View</DialogTitle>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={handleDownloadCSV}
                className="gap-2"
              >
                <Download className="h-4 w-4" />
                Download CSV
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => onOpenChange(false)}
                className="h-8 w-8 p-0"
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </DialogHeader>
        <ScrollArea className="flex-1 p-6">
          <table
            id={tableId}
            className="border-collapse border border-gray-300 w-full"
          >
            {tableContent}
          </table>
        </ScrollArea>
      </DialogContent>
    </Dialog>
  )
}