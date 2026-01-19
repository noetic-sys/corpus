import { createClient, createConfig } from '@/client/client'

// API URL for client-side calls
const getApiUrl = () => {
  return import.meta.env.VITE_API_URL!
}

// Agent service URL for agent-related calls (conversations, websocket)
const getAgentUrl = () => {
  return import.meta.env.VITE_AGENT_URL!
}

// Configure the API client with base URL
export const apiConfig = createConfig({
  baseUrl: getApiUrl(),
  headers: {
    'Content-Type': 'application/json',
  },
})

// Configure the agent client for agent service
export const agentConfig = createConfig({
  baseUrl: getAgentUrl(),
  headers: {
    'Content-Type': 'application/json',
  },
})

// Create and export the configured clients
export const apiClient = createClient(apiConfig)
export const agentClient = createClient(agentConfig)