import { Button } from "@/components/ui/button"
import { Download, Expand, Table } from "lucide-react"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
import { downloadTableAsCSV } from "@/lib/csv-utils"
import { useState } from "react"
import { TableExpandDialog } from "./table-expand-dialog"

interface MessageMarkdownProps {
  content: string
  messageId: number
  variant?: "compact" | "full"
}

export function MessageMarkdown({ content, messageId, variant = "compact" }: MessageMarkdownProps) {
  const [expandedTable, setExpandedTable] = useState<React.ReactNode | null>(null)

  const tableId = `table-${messageId}`

  const handleExpandTable = (tableContent: React.ReactNode) => {
    setExpandedTable(tableContent)
  }

  const handleDownloadCSV = () => {
    downloadTableAsCSV(tableId)
  }

  return (
    <>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          ol: ({ children }) => <ol className="list-decimal list-inside space-y-1">{children}</ol>,
          ul: ({ children }) => <ul className="list-disc list-inside space-y-1">{children}</ul>,
          p: ({ children }) => <p className="mb-2 last:mb-0 break-words">{children}</p>,
          table: ({ children }) => {
            if (variant === "compact") {
              // In compact view, show only the expand button, hide the table
              return (
                <div className="my-2 p-3 border border-dashed border-gray-300 rounded-lg bg-gray-50/50">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Table className="h-4 w-4 text-muted-foreground" />
                      <span className="text-sm text-muted-foreground">Table available</span>
                    </div>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleExpandTable(children)}
                      className="gap-2 text-xs"
                    >
                      <Expand className="h-3 w-3" />
                    </Button>
                  </div>
                </div>
              )
            }

            // In full view, show the table with download button
            return (
              <div className="space-y-2">
                <div className="flex justify-end gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleDownloadCSV}
                    className="gap-2 text-xs"
                  >
                    <Download className="h-3 w-3" />
                    Download CSV
                  </Button>
                </div>
                <table
                  id={tableId}
                  className="border-collapse border border-gray-300 w-full"
                >
                  {children}
                </table>
              </div>
            )
          },
          th: ({ children }) => <th className="border border-gray-300 px-4 py-2 bg-gray-50 font-semibold text-left">{children}</th>,
          td: ({ children }) => <td className="border border-gray-300 px-4 py-2">{children}</td>,
        }}
      >
        {content}
      </ReactMarkdown>

      {expandedTable && (
        <TableExpandDialog
          tableContent={expandedTable}
          tableId={`expanded-${tableId}`}
          open={!!expandedTable}
          onOpenChange={() => setExpandedTable(null)}
        />
      )}
    </>
  )
}