import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { MessageSquare, Calendar } from "lucide-react"
import { useChat } from "./chat-provider"
import { cn } from "@/lib/utils"
import { formatDistanceToNow } from "date-fns"

export function ConversationList() {
  const { state, switchConversation } = useChat()

  if (state.conversations.length === 0) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        <MessageSquare className="h-8 w-8 mx-auto mb-2 opacity-50" />
        <p className="text-sm">No conversations yet</p>
      </div>
    )
  }

  return (
    <ScrollArea className="max-h-32">
      <div className="space-y-1">
        {state.conversations.map((conversation) => {
          const isActive = conversation.id === state.currentConversationId
          const messageCount = state.messages[conversation.id]?.length || 0
          
          return (
            <Button
              key={conversation.id}
              variant={isActive ? "secondary" : "ghost"}
              className={cn(
                "w-full justify-start h-auto p-3 text-left",
                isActive && "bg-muted"
              )}
              onClick={() => switchConversation(conversation.id)}
            >
              <div className="flex-1 min-w-0">
                <div className="flex items-start justify-between">
                  <h4 className="text-sm font-medium truncate flex-1">
                    {conversation.title || `Chat ${conversation.id}`}
                  </h4>
                  {messageCount > 0 && (
                    <span className="text-xs text-muted-foreground ml-2">
                      {messageCount}
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-1 mt-1">
                  <Calendar className="h-3 w-3 text-muted-foreground" />
                  <span className="text-xs text-muted-foreground">
                    {formatDistanceToNow(new Date(conversation.createdAt), { addSuffix: true })}
                  </span>
                </div>
              </div>
            </Button>
          )
        })}
      </div>
    </ScrollArea>
  )
}