import { useState, useEffect } from 'react'
import { Button } from "@/components/ui/button"
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from "@/components/ui/sheet"
import { type QuestionResponse, type AiProviderResponse, type AiModelResponse } from '@/client'
import { Grid2x2Plus } from "lucide-react"
import { QuestionCreateForm } from './question-create-form'

interface QuestionCreateInlineProps {
  matrixId: number
  entitySetId: number
  onQuestionCreated: (question: QuestionResponse) => void
  onCreatingChange?: (isCreating: boolean) => void
  className?: string
  aiProviders: AiProviderResponse[]
  aiModels: AiModelResponse[]
}

export function QuestionCreateInline({
  matrixId,
  entitySetId,
  onQuestionCreated,
  onCreatingChange,
  className = '',
  aiProviders,
  aiModels
}: QuestionCreateInlineProps) {
  const [isOpen, setIsOpen] = useState(false)

  useEffect(() => {
    onCreatingChange?.(isOpen)
  }, [isOpen, onCreatingChange])

  const handleQuestionCreated = (question: QuestionResponse) => {
    onQuestionCreated(question)
    setIsOpen(false)
  }

  const handleCancel = () => {
    setIsOpen(false)
  }

  return (
    <div className={`w-full h-full p-2 flex items-center justify-center ${className}`}>
      <Sheet open={isOpen} onOpenChange={setIsOpen}>
        <SheetTrigger asChild>
          <Button
            variant="outline"
            style="blocky"
            size="sm"
            className="h-10 w-10 p-0 rounded-none"
            title="Add Question"
          >
            <Grid2x2Plus className="h-4 w-4" />
          </Button>
        </SheetTrigger>
        <SheetContent side="right" className="w-[400px] sm:w-[540px]">
          <SheetHeader>
            <SheetTitle>Create Question</SheetTitle>
          </SheetHeader>
          <div className="mt-6">
            <QuestionCreateForm
              matrixId={matrixId}
              entitySetId={entitySetId}
              onQuestionCreated={handleQuestionCreated}
              onCancel={handleCancel}
              aiProviders={aiProviders}
              aiModels={aiModels}
            />
          </div>
        </SheetContent>
      </Sheet>
    </div>
  )
}