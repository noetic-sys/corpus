import { 
  Type, 
  FileText, 
  Calendar, 
  DollarSign, 
  CheckSquare,
  type LucideIcon
} from "lucide-react"

export const QUESTION_TYPE_DISPLAY_NAMES = {
  'SHORT_ANSWER': 'Short Answer',
  'LONG_ANSWER': 'Long Answer', 
  'DATE': 'Date',
  'CURRENCY': 'Currency',
  'SELECT': 'Select',
} as const

export const QUESTION_TYPE_ICONS: Record<string, LucideIcon> = {
  'SHORT_ANSWER': Type,
  'LONG_ANSWER': FileText,
  'DATE': Calendar,
  'CURRENCY': DollarSign,
  'SELECT': CheckSquare,
} as const

// ID to name mapping (based on typical database setup)
export const QUESTION_TYPE_ID_TO_NAME: Record<number, string> = {
  1: 'SHORT_ANSWER',
  2: 'LONG_ANSWER',
  3: 'DATE',
  4: 'CURRENCY',
  5: 'SELECT',
} as const

export const QUESTION_TYPE_BADGE_NAMES = {
  'SHORT_ANSWER': 'Short',
  'LONG_ANSWER': 'Long',
  'DATE': 'Date',
  'CURRENCY': 'Currency',
  'SELECT': 'Select',
} as const

// Question Type ID Constants
export const QUESTION_TYPE_IDS = {
  SHORT_ANSWER: 1,
  LONG_ANSWER: 2,
  DATE: 3,
  CURRENCY: 4,
  SELECT: 5,
} as const

// Helper functions for question type detection
export function isSelectType(questionTypeId: number): boolean {
  return questionTypeId === QUESTION_TYPE_IDS.SELECT
}

export function getQuestionTypeIcon(typeName: string): LucideIcon {
  return QUESTION_TYPE_ICONS[typeName] || Type
}

export function getQuestionTypeDisplayName(typeName: string): string {
  return QUESTION_TYPE_DISPLAY_NAMES[typeName as keyof typeof QUESTION_TYPE_DISPLAY_NAMES] || typeName
}

export function getQuestionTypeIconById(typeId: number): LucideIcon {
  const typeName = QUESTION_TYPE_ID_TO_NAME[typeId]
  return getQuestionTypeIcon(typeName)
}

export function getQuestionTypeBadgeName(typeId: number): string {
  const typeName = QUESTION_TYPE_ID_TO_NAME[typeId]
  return QUESTION_TYPE_BADGE_NAMES[typeName as keyof typeof QUESTION_TYPE_BADGE_NAMES] || 'Unknown'
}