import { useState } from 'react'
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from "@/components/ui/sheet"
import { Variable } from "lucide-react"
import { TemplateVariablesManager } from './template-variables-manager'
import { useTemplateVariables } from '../hooks/use-template-variables'
import type { Question } from '../types'

interface TemplateVariablesButtonProps {
  matrixId: number
  questions: Question[]
  questionEntitySetId?: number
}

export function TemplateVariablesButton({ matrixId, questions, questionEntitySetId }: TemplateVariablesButtonProps) {
  const { data: templateVariables = [] } = useTemplateVariables(matrixId)
  const [isTemplateSheetOpen, setIsTemplateSheetOpen] = useState(false)

  return (
    <Sheet open={isTemplateSheetOpen} onOpenChange={setIsTemplateSheetOpen}>
      <SheetTrigger asChild>
      <Button 
            variant="outline"
            size="sm" 
            style="blocky"
            className="gap-1 border-[1px] rounded-none"
          >
          <Variable className="h-4 w-4" />
          Template Variables
          {templateVariables.length > 0 && (
            <Badge variant="secondary" style="blocky" className="ml-1 text-xs px-1.5 py-0.5 border-[1px]">
              {templateVariables.length}
            </Badge>
          )}
        </Button>
      </SheetTrigger>
      <SheetContent side="right" className="w-[500px] sm:w-[600px]">
        <SheetHeader>
          <SheetTitle>Template Variables</SheetTitle>
        </SheetHeader>
        <div className="mt-6">
          <TemplateVariablesManager
            matrixId={matrixId}
            questions={questions}
            questionEntitySetId={questionEntitySetId}
          />
        </div>
      </SheetContent>
    </Sheet>
  )
}