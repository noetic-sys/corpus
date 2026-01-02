/**
 * Utility for handling API errors from OpenAPI client responses
 */

export interface ApiError {
  detail?: string | ValidationError[]
}

export interface ValidationError {
  msg: string
  type?: string
  loc?: (string | number)[]
}

/**
 * Extracts a readable error message from an API error response
 * @param error - The error object from API response
 * @param fallbackMessage - Default message if no specific error details found
 * @returns A readable error message string
 */
export function getApiErrorMessage(error: ApiError | undefined, fallbackMessage: string): string {
  if (!error?.detail) {
    return fallbackMessage
  }

  if (Array.isArray(error.detail)) {
    // Handle validation errors - extract messages from ValidationError[]
    const messages = error.detail.map(err => err.msg).filter(Boolean)
    return messages.length > 0 ? messages.join(', ') : fallbackMessage
  }

  // Handle simple string error
  return error.detail || fallbackMessage
}

/**
 * Throws an Error with a properly formatted message from API error response
 * @param error - The error object from API response
 * @param fallbackMessage - Default message if no specific error details found
 * @throws Error with formatted message
 */
export function throwApiError(error: ApiError | undefined, fallbackMessage: string): never {
  throw new Error(getApiErrorMessage(error, fallbackMessage))
}