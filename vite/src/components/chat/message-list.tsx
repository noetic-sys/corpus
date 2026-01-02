import { ScrollArea } from "@/components/ui/scroll-area"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Bot, Wrench, Clock, ChevronDown, ChevronRight } from "lucide-react"
import { useEffect, useRef, useState } from "react"
import { cn } from "@/lib/utils"
import { formatDistanceToNow } from "date-fns"
import { MessageMarkdown } from "./message-markdown"
import type { AgentMessageResponse, ToolCall } from "./types"

interface MessageListProps {
  messages: AgentMessageResponse[]
}

interface MessageProps {
  message: AgentMessageResponse
}

function ToolCallDisplay({ toolCall }: { toolCall: ToolCall }) {
  const [isExpanded, setIsExpanded] = useState(false)
  let args: Record<string, unknown> = {}
  try {
    args = JSON.parse(toolCall.function.arguments)
  } catch {
    // Invalid JSON, show raw arguments
  }

  const hasArgs = Object.keys(args).length > 0

  return (
    <div className="bg-muted/50 rounded p-2 text-xs space-y-1">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1">
          <Wrench className="h-3 w-3" />
          <span className="font-medium">{toolCall.function.name}</span>
        </div>
        {hasArgs && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setIsExpanded(!isExpanded)}
            className="h-4 w-4 p-0"
          >
            {isExpanded ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
          </Button>
        )}
      </div>
      {hasArgs && isExpanded && (
        <div className="text-muted-foreground">
          <pre className="whitespace-pre-wrap">{JSON.stringify(args, null, 2)}</pre>
        </div>
      )}
    </div>
  )
}

function ToolResponseDisplay({ content }: { content: string }) {
  const [isExpanded, setIsExpanded] = useState(false)

  // Try to parse as JSON to format it nicely
  let formattedContent = content
  try {
    const parsed = JSON.parse(content)
    formattedContent = JSON.stringify(parsed, null, 2)
  } catch {
    // Not JSON, use as-is
  }

  return (
    <div className="bg-muted/30 rounded p-2 text-xs space-y-1">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1">
          <Wrench className="h-3 w-3" />
          <span className="font-medium">Tool Response</span>
        </div>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setIsExpanded(!isExpanded)}
          className="h-4 w-4 p-0"
        >
          {isExpanded ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
        </Button>
      </div>
      {isExpanded && (
        <div className="text-muted-foreground">
          <pre className="whitespace-pre-wrap text-xs">{formattedContent}</pre>
        </div>
      )}
    </div>
  )
}

function Message({ message }: MessageProps) {
  const isUser = message.role === 'user'
  const isAssistant = message.role === 'assistant'
  const isTool = message.role === 'tool'


  const getBgColor = () => {
    if (isUser) return "bg-primary text-primary-foreground"
    if (isTool) return "bg-muted"
    return "bg-background border"
  }

  return (
    <div className={cn(
      "w-full mb-4",
      isUser ? "flex flex-col items-end" : "flex flex-col items-start"
    )}>
      <div className={cn(
        "max-w-[85%] space-y-2",
        isUser ? "ml-auto text-right" : "mr-auto text-left"
      )}>
        {/* Message header */}
        <div className={cn(
          "flex items-center gap-2 text-xs text-muted-foreground",
          isUser ? "flex-row-reverse justify-start" : "flex-row justify-start"
        )}>
          <Badge variant={isUser ? "default" : "secondary"} className="text-xs">
            {message.role}
          </Badge>
          <span className="flex items-center gap-1">
            <Clock className="h-3 w-3" />
            {formatDistanceToNow(new Date(message.createdAt), { addSuffix: true })}
          </span>
          {message.sequenceNumber > 0 && (
            <span>#{message.sequenceNumber}</span>
          )}
        </div>

        {/* Message content */}
        {message.content && (
          <>
            {isTool ? (
              <ToolResponseDisplay content={message.content} />
            ) : (
              <div className={cn(
                "w-full p-3 rounded-lg text-sm break-words",
                getBgColor()
              )}>
                <div className="max-w-[85%] overflow-hidden">
                  {isAssistant ? (
                    /*unforuntately with react markdown we have to constrain with hard constants, we can't do pct based*/
                    <div className="max-w-[320px] overflow-wrap-anywhere">
                      <MessageMarkdown
                        content={message.content}
                        messageId={message.id}
                        variant="compact"
                      />
                    </div>
                  ) : (
                    <div className={cn(
                      "whitespace-pre-wrap break-words",
                      isUser ? "text-left" : ""
                    )}>
                      {message.content}
                    </div>
                  )}
                </div>
              </div>
            )}
          </>
        )}

        {/* Tool calls */}
        {message.toolCalls && message.toolCalls.length > 0 && (
          <div className="space-y-2">
            {message.toolCalls.map((toolCall, index) => (
              <ToolCallDisplay key={`${toolCall.id}-${index}`} toolCall={toolCall} />
            ))}
          </div>
        )}

        {/* Tool call ID for tool responses */}
        {message.toolCallId && (
          <div className="text-xs text-muted-foreground">
            Response to: {message.toolCallId}
          </div>
        )}
      </div>
    </div>
  )
}

export function MessageList({ messages }: MessageListProps) {
  const scrollAreaRef = useRef<HTMLDivElement>(null)

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (scrollAreaRef.current) {
      const scrollContainer = scrollAreaRef.current.querySelector('[data-radix-scroll-area-viewport]')
      if (scrollContainer) {
        scrollContainer.scrollTop = scrollContainer.scrollHeight
      }
    }
  }, [messages.length])

  if (messages.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center p-8 text-center">
        <div className="max-w-sm">
          <Bot className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
          <h3 className="font-medium mb-2">Ready to help!</h3>
          <p className="text-sm text-muted-foreground">
            Ask me anything about your matrices, documents, or questions. I can help you create, update, and analyze your data.
          </p>
        </div>
      </div>
    )
  }

  return (
    <ScrollArea ref={scrollAreaRef} className="flex-1 h-full w-full pr-2 pl-2">
        {messages.map((message, index) => (
          <Message key={`${message.id}-${index}`} message={message} />
        ))}
    </ScrollArea>
  )
}