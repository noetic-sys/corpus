import type { Question } from '../../types'

export function getAffectedQuestionIds(
  templateVariableId: number,
  questions: Question[]
): number[] {
  if (!questions || questions.length === 0) {
    return []
  }
  
  const templatePattern = `#{{${templateVariableId}}}`
  
  const affectedQuestions = questions.filter(question => {
    return question.questionText?.includes(templatePattern)
  })
  
  return affectedQuestions.map(question => question.id)
}

export function validateTemplateString(templateString: string): { isValid: boolean; error?: string } {
  if (!templateString.trim()) {
    return { isValid: false, error: 'Template string is required' }
  }

  if (!/^[a-zA-Z_][a-zA-Z0-9_]*$/.test(templateString.trim())) {
    return { 
      isValid: false, 
      error: 'Template string must be a valid variable name (letters, numbers, underscores only)' 
    }
  }

  return { isValid: true }
}

export function validateTemplateValue(value: string): { isValid: boolean; error?: string } {
  if (!value.trim()) {
    return { isValid: false, error: 'Value is required' }
  }

  return { isValid: true }
}