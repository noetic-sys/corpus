import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet"
import { Button } from "@/components/ui/button"
import { Separator } from "@/components/ui/separator"
import { Plus, MessageSquare, Settings, ArrowLeft } from "lucide-react"
import { useChat } from "./chat-provider"
import { ConversationList } from "./conversation-list"
import { MessageList } from "./message-list"
import { MessageInput } from "./message-input"
import { usePageContext } from "./hooks/use-page-context"

export function ChatSheet() {
  const { state, closeChat, createNewConversation, backToConversationList } = useChat()
  const pageContext = usePageContext()

  const handleNewChat = () => {
    createNewConversation(pageContext)
  }

  const currentMessages = state.currentConversationId 
    ? state.messages[state.currentConversationId] || []
    : []

  return (
    <Sheet open={state.isOpen} onOpenChange={closeChat}>
      <SheetContent className="w-[400px] sm:w-[540px] p-0 flex flex-col h-full max-h-screen">
        <SheetHeader className="px-4 py-3 border-b">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              {state.currentConversationId && (
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={backToConversationList}
                  className="h-8 w-8"
                  title="Back to conversations"
                >
                  <ArrowLeft className="h-4 w-4" />
                </Button>
              )}
              <SheetTitle className="flex items-center gap-2">
                <MessageSquare className="h-5 w-5" />
                Agent Chat
              </SheetTitle>
            </div>
            <div className="flex gap-1">
              <Button
                variant="ghost"
                size="icon"
                onClick={handleNewChat}
                className="h-8 w-8"
                title="New conversation"
              >
                <Plus className="h-4 w-4" />
              </Button>
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8"
                title="Settings"
              >
                <Settings className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </SheetHeader>

        {state.currentConversationId ? (
          <div className="flex flex-col flex-1 min-h-0">
            {/* Show current conversation title instead of full conversation list */}
            {state.conversations.length > 1 && (
              <div className="px-4 py-2 border-b bg-muted/20">
                <div className="text-sm text-muted-foreground">
                  Conversation: {state.conversations.find(c => c.id === state.currentConversationId)?.title || `#${state.currentConversationId}`}
                </div>
              </div>
            )}

            {/* Messages area */}
            <div className="flex-1 min-h-0 overflow-hidden w-full">
              <MessageList messages={currentMessages} />
            </div>

            <Separator />

            {/* Message input */}
            <div className="p-4">
              <MessageInput />
            </div>
          </div>
        ) : (
          // No conversation selected
          <div className="flex-1 flex flex-col items-center justify-center p-8 text-center">
            <MessageSquare className="h-12 w-12 text-muted-foreground mb-4" />
            <h3 className="text-lg font-medium mb-2">Start a conversation</h3>
            <p className="text-muted-foreground mb-6 max-w-sm">
              Chat with our AI agent to get help with your matrices, documents, and questions.
            </p>
            <Button onClick={handleNewChat} className="gap-2">
              <Plus className="h-4 w-4" />
              New Conversation
            </Button>
            
            {/* Recent conversations */}
            {state.conversations.length > 0 && (
              <div className="mt-8 w-full max-w-sm">
                <h4 className="text-sm font-medium mb-3 text-left">Recent Conversations</h4>
                <ConversationList />
              </div>
            )}
          </div>
        )}

        {/* Connection status */}
        <div className="px-4 py-2 border-t bg-muted/20">
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span>
              Status: <span className="capitalize">{state.connectionStatus}</span>
            </span>
            {state.currentConversationId && (
              <span>
                Conversation #{state.currentConversationId}
              </span>
            )}
          </div>
        </div>
      </SheetContent>
    </Sheet>
  )
}