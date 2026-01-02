import type { JSX } from 'react'
import { QUESTION_TYPE_IDS } from '@/lib/question-types'
import { TextAnswerItem } from './text-answer-item'
import { DateAnswerItem } from './date-answer-item'
import { CurrencyAnswerItem } from './currency-answer-item'
import { SelectAnswerItem } from './select-answer-item'
import { LowConfidenceWarning } from './low-confidence-warning'
import type { AnswerData, Citation } from '../types'

interface AnswerItemRendererProps {
  answerData: AnswerData
  questionTypeId?: number
  className?: string
  citations?: Citation[]
  cellId?: number
}

export function AnswerItemRenderer({
  answerData,
  questionTypeId,
  className,
  citations,
  cellId
}: AnswerItemRendererProps) {
  const commonProps = { answerData, className, citations, cellId }

  // Get confidence from answerData (all answer types have confidence)
  const confidence = answerData.confidence ?? 1.0

  // Render appropriate answer component based on question type
  let answerComponent: JSX.Element

  switch (questionTypeId) {
    case QUESTION_TYPE_IDS.SHORT_ANSWER:
    case QUESTION_TYPE_IDS.LONG_ANSWER:
      answerComponent = <TextAnswerItem {...commonProps} />
      break

    case QUESTION_TYPE_IDS.DATE:
      answerComponent = <DateAnswerItem {...commonProps} />
      break

    case QUESTION_TYPE_IDS.CURRENCY:
      answerComponent = <CurrencyAnswerItem {...commonProps} />
      break

    case QUESTION_TYPE_IDS.SELECT:
      answerComponent = <SelectAnswerItem {...commonProps} />
      break

    default:
      answerComponent = <TextAnswerItem {...commonProps} />
  }

  return (
    <div className="space-y-2">
      <LowConfidenceWarning confidence={confidence} />
      {answerComponent}
    </div>
  )
}