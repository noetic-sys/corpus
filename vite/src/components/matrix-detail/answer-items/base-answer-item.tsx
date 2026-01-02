import type { AnswerData, Citation } from '../types'

export interface BaseAnswerItemProps {
  answerData: AnswerData
  className?: string
  citations?: Citation[]
  cellId?: number
}

export type AnswerItemRendererProps = BaseAnswerItemProps