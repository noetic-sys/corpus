import { useAuth } from '@/hooks/useAuth'
import { ChatButton } from './chat-button'
import { ChatSheet } from './chat-sheet'

export function Chat() {
  const { user } = useAuth()

  if (!user) {
    return null
  }

  return (
    <>
      <ChatButton />
      <ChatSheet />
    </>
  )
}

export { ChatProvider, useChat } from './chat-provider'
export type { PageContext } from './types'