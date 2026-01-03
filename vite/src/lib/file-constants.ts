// Document upload constants
export const ACCEPTED_FILE_TYPES = [
  '.pdf', '.doc', '.docx', '.txt', '.md',
  '.xlsx', '.xls', '.pptx', '.ppt', '.csv',
  '.mp3', '.wav', '.flac', '.ogg', '.webm', '.m4a', '.aac'
]
export const MAX_FILE_SIZE = 10 * 1024 * 1024 // 10MB

// AI-powered chunking - recommend for files >= 5KB
export const AGENTIC_CHUNKING_SIZE_THRESHOLD = 5 * 1024
