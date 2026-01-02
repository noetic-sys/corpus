import { createClient, createConfig } from '@/client/client'

// API URL for client-side calls - use environment variable or default to proxy
const getApiUrl = () => {
  return import.meta.env.VITE_API_URL!
}

// Configure the API client with base URL
export const apiConfig = createConfig({
  baseUrl: getApiUrl(),
  headers: {
    'Content-Type': 'application/json',
  },
})

// Create and export the configured client
export const apiClient = createClient(apiConfig)