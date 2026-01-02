import type {
  MatrixCellWithAnswerResponse,
  TextAnswerDataResponse,
  DateAnswerDataResponse,
  CurrencyAnswerDataResponse,
  SelectAnswerDataResponse,
  MatrixDocumentResponse,
  DocumentResponse,
  CitationMinimalResponse,
} from '@/client'

export type AnswerData =
  | TextAnswerDataResponse
  | DateAnswerDataResponse
  | CurrencyAnswerDataResponse
  | SelectAnswerDataResponse

// Use the generated type - fully entity-ref based
export type MatrixCellType = MatrixCellWithAnswerResponse

// Helper to create entity ref lookup key
export type EntityRefLookup = {
  entitySetId: number
  entityId: number
  role: string
}

export type Citation = CitationMinimalResponse
// Use the generated MatrixDocumentResponse type for matrix context
export type MatrixDocument = MatrixDocumentResponse

// Helper type to get the document info from MatrixDocument
export type Document = DocumentResponse

export interface Question {
  id: number
  matrixId: number
  questionText: string
  questionTypeId: number
  aiModelId?: number | null
  aiConfigOverride?: Record<string, unknown> | null
  label?: string | null
  minAnswers?: number
  maxAnswers?: number | null
  useAgentQa?: boolean
  createdAt: string
  updatedAt: string
}