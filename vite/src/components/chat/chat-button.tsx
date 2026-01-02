import { Button } from "@/components/ui/button"
import { MessageCircle, Loader2, Wifi, WifiOff, AlertCircle } from "lucide-react"
import { useChat } from "./chat-provider"
import { cn } from "@/lib/utils"

export function ChatButton() {
  const { state, openChat } = useChat()

  const getStatusIcon = () => {
    switch (state.connectionStatus) {
      case 'connected':
        return <Wifi className="h-3 w-3 text-green-500" />
      case 'connecting':
        return <Loader2 className="h-3 w-3 text-yellow-500 animate-spin" />
      case 'error':
        return <AlertCircle className="h-3 w-3 text-red-500" />
      case 'disconnected':
      default:
        return <WifiOff className="h-3 w-3 text-gray-500" />
    }
  }

  const hasUnreadMessages = false // TODO: Implement unread message tracking

  return (
    <div className="fixed bottom-6 right-6 z-50">
      <Button
        onClick={openChat}
        className={cn(
          "h-14 w-14 rounded-full shadow-lg hover:shadow-xl transition-all duration-200",
          "bg-primary hover:bg-primary/90",
          state.isOpen && "scale-90"
        )}
        size="icon"
      >
        <div className="relative">
          <MessageCircle className="h-6 w-6" />
          
          {/* Status indicator */}
          <div className="absolute -top-1 -right-1 h-4 w-4 bg-background rounded-full flex items-center justify-center border border-border">
            {getStatusIcon()}
          </div>
          
          {/* Unread indicator */}
          {hasUnreadMessages && (
            <div className="absolute -top-2 -right-2 h-3 w-3 bg-red-500 rounded-full animate-pulse" />
          )}
        </div>
      </Button>
    </div>
  )
}