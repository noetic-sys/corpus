import { useState } from "react"
import { cn } from "@/lib/utils"
import { Edit, RefreshCw, Trash2, Tag, Copy } from "lucide-react"
import { ReprocessDropdown, type ReprocessAction } from "../reprocess/reprocess-dropdown"
import { useReprocessQuestion } from "../hooks/use-reprocess-question"
import { useSoftDeleteQuestion } from "../hooks/use-soft-delete-question"
import { useUpdateQuestionLabel } from "../hooks/use-update-question-label"
import { useDuplicateQuestion } from "../hooks/use-duplicate-question"
import { useQuestionOptions } from "../hooks/use-question-options"
import { QuestionEditForm } from "../interactive/question-edit-form"
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet"
import { DeleteConfirmationDialog } from "../dialogs/delete-confirmation-dialog"
import { LabelEditDialog } from "../dialogs/label-edit-dialog"
import { isSelectType } from "@/lib/question-types"
import type { Question } from '../types'
import type { AiProviderResponse, AiModelResponse, EntityRole } from '@/client'

interface QuestionHeaderOverlayProps {
  question: Question
  matrixId: number
  entitySetId: number
  memberId: number
  role: string
  children: React.ReactNode
  aiProviders?: AiProviderResponse[]
  aiModels?: AiModelResponse[]
}

export function QuestionHeaderOverlay({ question, matrixId, entitySetId, role, children, aiProviders = [], aiModels = [] }: QuestionHeaderOverlayProps) {
  const { reprocessQuestion, isReprocessing } = useReprocessQuestion()
  const { softDeleteQuestion, isDeleting } = useSoftDeleteQuestion()
  const { updateQuestionLabel, isUpdating: isUpdatingLabel } = useUpdateQuestionLabel()
  const { duplicateQuestion, isDuplicating } = useDuplicateQuestion()
  // Only query for options if this is a select-type question
  const shouldQueryOptions = isSelectType(question.questionTypeId)
  const { data: optionSet } = useQuestionOptions(question.id, shouldQueryOptions)
  const [isEditSheetOpen, setIsEditSheetOpen] = useState(false)
  const [showDeleteDialog, setShowDeleteDialog] = useState(false)
  const [showLabelDialog, setShowLabelDialog] = useState(false)


  const handleReprocessQuestion = async () => {
    await reprocessQuestion(matrixId, question.id, entitySetId, role)
  }

  const handleDuplicateQuestion = async () => {
    await duplicateQuestion(matrixId, question.id)
  }

  const handleEditQuestion = () => {
    setIsEditSheetOpen(true)
  }

  const handleEditLabel = () => {
    setShowLabelDialog(true)
  }

  const handleDeleteClick = () => {
    setShowDeleteDialog(true)
  }

  const handleConfirmDelete = async () => {
    await softDeleteQuestion(matrixId, question.id, entitySetId, role as EntityRole)
    setShowDeleteDialog(false)
  }

  const handleQuestionUpdated = () => {
    setIsEditSheetOpen(false)
    // Optionally trigger a refresh of the question data here
  }

  const handleCancelEdit = () => {
    setIsEditSheetOpen(false)
  }

  const handleSaveLabel = async (label: string | null) => {
    await updateQuestionLabel(matrixId, question.id, label)
  }

  const actions: ReprocessAction[] = [
    {
      id: 'edit-question',
      label: 'Edit Question',
      onClick: handleEditQuestion,
      disabled: isReprocessing || isDeleting || isUpdatingLabel || isDuplicating,
      isLoading: false,
      icon: <Edit className="mr-2 h-4 w-4" />
    },
    {
      id: 'duplicate-question',
      label: 'Duplicate Question',
      onClick: handleDuplicateQuestion,
      disabled: isReprocessing || isDeleting || isUpdatingLabel || isDuplicating,
      isLoading: isDuplicating,
      icon: <Copy className="mr-2 h-4 w-4" />
    },
    {
      id: 'edit-label',
      label: 'Edit Label',
      onClick: handleEditLabel,
      disabled: isReprocessing || isDeleting || isUpdatingLabel || isDuplicating,
      isLoading: isUpdatingLabel,
      icon: <Tag className="mr-2 h-4 w-4" />
    },
    {
      id: 'reprocess-question',
      label: 'Reprocess Column',
      onClick: handleReprocessQuestion,
      disabled: isReprocessing || isDeleting || isUpdatingLabel || isDuplicating,
      isLoading: isReprocessing,
      icon: <RefreshCw className={cn("mr-2 h-4 w-4", isReprocessing && "animate-spin")} />
    },
    {
      id: 'delete-question',
      label: 'Delete Question',
      onClick: handleDeleteClick,
      disabled: isReprocessing || isDeleting || isUpdatingLabel || isDuplicating,
      isLoading: isDeleting,
      icon: <Trash2 className="mr-2 h-4 w-4 text-destructive" />
    }
  ]

  // Convert option set to the format expected by the form
  const existingOptions = optionSet?.options?.map(opt => ({ value: opt.value })) || []

  return (
    <>
      <ReprocessDropdown actions={actions}>
        <div className={cn(
          "w-full h-full transition-colors cursor-pointer",
          "hover:bg-muted/50"
        )}>
          {children}
        </div>
      </ReprocessDropdown>

      <Sheet open={isEditSheetOpen} onOpenChange={setIsEditSheetOpen}>
        <SheetContent side="right" className="w-[400px] sm:w-[540px]">
          <SheetHeader>
            <SheetTitle>Edit Question</SheetTitle>
          </SheetHeader>
          <div className="mt-6">
            <QuestionEditForm
              matrixId={matrixId}
              question={question}
              questionEntitySetId={entitySetId}
              existingOptions={existingOptions}
              onQuestionUpdated={handleQuestionUpdated}
              onCancel={handleCancelEdit}
              aiProviders={aiProviders}
              aiModels={aiModels}
            />
          </div>
        </SheetContent>
      </Sheet>

      <DeleteConfirmationDialog
        open={showDeleteDialog}
        onOpenChange={setShowDeleteDialog}
        onConfirm={handleConfirmDelete}
        title="Delete Question"
        description="Are you sure you want to delete this question?"
        isDeleting={isDeleting}
      />

      <LabelEditDialog
        open={showLabelDialog}
        onOpenChange={setShowLabelDialog}
        currentLabel={question.label}
        onSave={handleSaveLabel}
        isLoading={isUpdatingLabel}
        title="Edit Question Label"
        description="Set a label for this question to help with organization."
      />
    </>
  )
}