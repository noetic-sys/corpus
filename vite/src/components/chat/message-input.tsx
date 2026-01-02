import { useState } from 'react'
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Send, Loader2, Lock, Unlock } from "lucide-react"
import { useChat } from "./chat-provider"
import { usePageContext } from "./hooks/use-page-context"
import type { PermissionMode } from "./types"
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group"

export function MessageInput() {
  const [input, setInput] = useState('')
  const [permissionMode, setPermissionMode] = useState<PermissionMode>('read')
  const { state, sendMessage } = useChat()
  const pageContext = usePageContext()

  const handleSubmit = (e?: React.FormEvent) => {
    e?.preventDefault()

    if (!input.trim() || state.isLoading || state.connectionStatus !== 'connected') {
      return
    }

    sendMessage(input.trim(), permissionMode, pageContext)
    setInput('')
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  const isDisabled = state.isLoading || state.connectionStatus !== 'connected'

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      {/* Permission mode selector */}
      <div className="flex items-center gap-2">
        <span className="text-xs text-muted-foreground">Mode:</span>
        <ToggleGroup
          type="single"
          value={permissionMode}
          onValueChange={(value) => value && setPermissionMode(value as PermissionMode)}
          className="gap-0"
        >
          <ToggleGroupItem value="read" className="gap-1 text-xs h-7 px-2.5">
            <Lock className="h-3 w-3" />
            <span>Read</span>
          </ToggleGroupItem>
          <ToggleGroupItem value="write" className="gap-1 text-xs h-7 px-2.5">
            <Unlock className="h-3 w-3" />
            <span>Write</span>
          </ToggleGroupItem>
        </ToggleGroup>
      </div>

      <div className="relative">
        <Textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={
            state.connectionStatus !== 'connected'
              ? 'Connecting to chat...'
              : 'Type your message... (Enter to send, Shift+Enter for new line)'
          }
          disabled={isDisabled}
          className="min-h-[60px] resize-none pr-12"
          maxLength={4000}
        />
        <Button
          type="submit"
          size="icon"
          disabled={isDisabled || !input.trim()}
          className="absolute right-2 bottom-2 h-8 w-8"
        >
          {state.isLoading ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Send className="h-4 w-4" />
          )}
        </Button>
      </div>

      {/* Character count and status */}
      <div className="flex items-center justify-between text-xs text-muted-foreground">
        <div className="flex items-center gap-2">
          {state.connectionStatus !== 'connected' && (
            <span className="text-yellow-600">
              {state.connectionStatus === 'connecting' ? 'Connecting...' : 'Disconnected'}
            </span>
          )}
          {state.isLoading && (
            <span className="text-blue-600">Agent is typing...</span>
          )}
        </div>
        <span className={input.length > 3800 ? 'text-red-600' : ''}>
          {input.length}/4000
        </span>
      </div>

      {/* Page context indicator */}
      {pageContext && Object.keys(pageContext).length > 1 && (
        <div className="text-xs text-muted-foreground bg-muted/50 rounded p-2">
          <span className="font-medium">Current context:</span> {pageContext.page}
          {pageContext.matrixId && ` (Matrix #${pageContext.matrixId})`}
        </div>
      )}
    </form>
  )
}