import { useState } from 'react'
import { useAuth } from '@/hooks/useAuth'
import { Button } from "@/components/ui/button"
import { MonacoTextarea } from "@/components/ui/monaco-textarea"
import { Input } from "@/components/ui/input"
import { Switch } from "@/components/ui/switch"
import { Label } from "@/components/ui/label"
import { Plus, X, Check, GripVertical, Variable, AlertCircle } from "lucide-react"
import type { IKeyboardEvent } from 'monaco-editor'
import { type QuestionResponse, type AiProviderResponse, type AiModelResponse } from '@/client'
import { toast } from "sonner"
import { QuestionTypeSelector } from './question-type-selector'
import { isSelectType } from '@/lib/question-types'
import { useQueryClient } from '@tanstack/react-query'
import { invalidateByEntitySetFilter } from '../utils/cache-utils'
import { useMatrixTemplateVariables } from '../hooks/use-matrix-template-variables'
import { useMatrixContext } from '../context/matrix-context'
import {
  createQuestionApiV1MatricesMatrixIdQuestionsPost,
  createQuestionWithOptionsApiV1MatricesMatrixIdQuestionsWithOptionsPost,
  updateQuestionWithOptionsApiV1MatricesMatrixIdQuestionsQuestionIdPatch
} from '@/client'
import { apiClient } from '@/lib/api'
import { throwApiError } from '@/lib/api-error'
import { AIModelSelector } from './ai-model-selector'
import type { Question } from '../types'

interface QuestionOption {
  value: string
}

interface QuestionFormBaseProps {
  matrixId: number
  mode: 'create' | 'edit'
  question?: Question
  questionEntitySetId?: number
  existingOptions?: QuestionOption[]
  onSuccess: (question: QuestionResponse) => void
  onCancel: () => void
  className?: string
  aiProviders?: AiProviderResponse[]
  aiModels?: AiModelResponse[]
}

export function QuestionFormBase({
  matrixId,
  mode,
  question,
  questionEntitySetId,
  existingOptions = [],
  onSuccess,
  onCancel,
  className = '',
  aiProviders = [],
  aiModels = []
}: QuestionFormBaseProps) {
  const { getToken } = useAuth()
  const { matrixType } = useMatrixContext()
  const isEditMode = mode === 'edit'
  const isCorrelationMatrix = matrixType === 'cross_correlation'

  const [questionText, setQuestionText] = useState(
    isEditMode && question ? question.questionText : ''
  )
  const [label, setLabel] = useState(
    isEditMode && question ? question.label || '' : ''
  )
  const [questionTypeId, setQuestionTypeId] = useState(
    isEditMode && question ? question.questionTypeId : 1
  )
  const [selectedAiModelId, setSelectedAiModelId] = useState<number | null>(
    isEditMode && question ? question.aiModelId || null : null
  )
  const [minAnswers, setMinAnswers] = useState<number>(
    isEditMode && question ? question.minAnswers || 1 : 1
  )
  const [maxAnswers, setMaxAnswers] = useState<number | null>(
    isEditMode && question
      ? (question.maxAnswers !== undefined ? question.maxAnswers : null)
      : 1
  )
  const [useAgentQa, setUseAgentQa] = useState<boolean>(
    isEditMode && question ? question.useAgentQa || false : false
  )
  const [options, setOptions] = useState<QuestionOption[]>(
    existingOptions.length > 0
      ? existingOptions
      : [{ value: '' }, { value: '' }]
  )
  const [isSubmitting, setIsSubmitting] = useState(false)
  const queryClient = useQueryClient()
  const { data: templateVariables = [] } = useMatrixTemplateVariables(matrixId)
  
  // Store original values for comparison in edit mode
  const originalOptions = existingOptions

  const addOption = () => {
    setOptions(prev => [...prev, { value: '' }])
  }

  const removeOption = (index: number) => {
    if (options.length <= 2) return // Keep at least 2 options
    setOptions(prev => prev.filter((_, i) => i !== index))
  }

  const updateOption = (index: number, value: string) => {
    setOptions(prev => prev.map((opt, i) => 
      i === index ? { ...opt, value } : opt
    ))
  }

  const handleTypeSelect = (typeId: number) => {
    setQuestionTypeId(typeId)
  }

  // Helper function to check if options have changed
  const optionsHaveChanged = (): boolean => {
    const currentValidOptions = options.filter(opt => opt.value.trim())
    const originalValidOptions = originalOptions.filter(opt => opt.value.trim())
    
    if (currentValidOptions.length !== originalValidOptions.length) {
      return true
    }
    
    return !currentValidOptions.every((opt, index) => 
      opt.value.trim() === originalValidOptions[index]?.value.trim()
    )
  }

  const handleSubmit = async () => {
    if (!questionText.trim()) {
      toast.error('Validation Error', {
        description: 'Question text is required'
      })
      return
    }

    // Note: Template variable validation for correlation matrices is handled on the backend
    // The Monaco editor converts ${{A}} and ${{B}} display syntax to @{{LEFT}} and @{{RIGHT}} internally

    // Note: Template variable validation is now handled on the backend
    // The Monaco editor handles conversion between names and IDs

    // Validate answer count configuration
    if (minAnswers < 1) {
      toast.error('Validation Error', {
        description: 'Minimum answers must be at least 1'
      })
      return
    }
    
    if (maxAnswers !== null && maxAnswers < minAnswers) {
      toast.error('Validation Error', {
        description: 'Maximum answers must be greater than or equal to minimum answers'
      })
      return
    }

    // Validate options for select questions
    if (isSelectType(questionTypeId)) {
      const validOptions = options.filter(opt => opt.value.trim())
      if (validOptions.length < 2) {
        toast.error('Validation Error', {
          description: 'At least 2 options are required for single select questions'
        })
        return
      }
    }

    setIsSubmitting(true)

    try {
      const requestBody: Record<string, unknown> = {}
      
      if (isEditMode && question) {
        // Edit mode - only include changed fields
        if (questionText.trim() !== question.questionText) {
          requestBody.questionText = questionText.trim()
        }

        if (label.trim() !== (question.label || '')) {
          requestBody.label = label.trim() || null
        }

        if (questionTypeId !== question.questionTypeId) {
          requestBody.questionTypeId = questionTypeId
        }

        if (selectedAiModelId !== (question.aiModelId || null)) {
          requestBody.aiModelId = selectedAiModelId
        }

        if (minAnswers !== (question.minAnswers || 1)) {
          requestBody.minAnswers = minAnswers
        }

        if (maxAnswers !== (question.maxAnswers || null)) {
          requestBody.maxAnswers = maxAnswers
        }

        if (useAgentQa !== (question.useAgentQa || false)) {
          requestBody.useAgentQa = useAgentQa
        }

        // Only include options if:
        // 1. We're changing the question type to/from select
        // 2. The options have actually changed
        const typeChanged = questionTypeId !== question.questionTypeId
        const isChangingToOrFromSelect = typeChanged && (isSelectType(questionTypeId) || isSelectType(question.questionTypeId))
        
        if (isChangingToOrFromSelect) {
          // Type is changing, always include options
          if (isSelectType(questionTypeId)) {
            const validOptions = options.filter(opt => opt.value.trim())
            requestBody.options = validOptions.map((opt) => ({
              value: opt.value.trim()
            }))
          } else {
            // Changing from select to non-select, remove options
            requestBody.options = []
          }
        } else if (isSelectType(questionTypeId) && optionsHaveChanged()) {
          // Still a select type, but options have changed
          const validOptions = options.filter(opt => opt.value.trim())
          requestBody.options = validOptions.map((opt) => ({
            value: opt.value.trim()
          }))
        }
      } else {
        // Create mode - include all fields
        requestBody.questionText = questionText.trim()
        requestBody.label = label.trim() || null
        requestBody.questionTypeId = questionTypeId
        requestBody.aiModelId = selectedAiModelId
        requestBody.minAnswers = minAnswers
        requestBody.maxAnswers = maxAnswers
        requestBody.useAgentQa = useAgentQa

        // Add options for select questions
        if (isSelectType(questionTypeId)) {
          const validOptions = options.filter(opt => opt.value.trim())
          requestBody.options = validOptions.map((opt) => ({
            value: opt.value.trim()
          }))
        }
      }

      const token = await getToken()

      let response
      if (isEditMode && question) {
        // Always use the unified update endpoint for editing
        response = await updateQuestionWithOptionsApiV1MatricesMatrixIdQuestionsQuestionIdPatch({
          path: {
            matrixId: matrixId,
            questionId: question.id
          },
          body: requestBody,
          headers: {
            authorization: `Bearer ${token}`
          },
          client: apiClient
        })
      } else {
        // For creation, use different endpoints based on question type
        if (isSelectType(questionTypeId)) {
          // Select types require options - use the question-with-options endpoint
          const validOptions = options.filter(opt => opt.value.trim())

          if (!questionEntitySetId) {
            throw new Error('Entity set ID is required for creating questions')
          }

          response = await createQuestionWithOptionsApiV1MatricesMatrixIdQuestionsWithOptionsPost({
            path: { matrixId: matrixId },
            query: { entitySetId: questionEntitySetId },
            body: {
              questionText: questionText.trim(),
              questionTypeId: questionTypeId,
              label: label.trim() || null,
              aiModelId: selectedAiModelId,
              minAnswers: minAnswers,
              maxAnswers: maxAnswers,
              useAgentQa: useAgentQa,
              options: validOptions.map((opt) => ({
                value: opt.value.trim()
              }))
            },
            headers: {
              authorization: `Bearer ${token}`
            },
            client: apiClient
          })
        } else {
          // For all other question types, use the regular endpoint
          if (!questionEntitySetId) {
            throw new Error('Entity set ID is required for creating questions')
          }

          response = await createQuestionApiV1MatricesMatrixIdQuestionsPost({
            path: { matrixId: matrixId },
            query: { entitySetId: questionEntitySetId },
            body: {
              questionText: questionText.trim(),
              questionTypeId: questionTypeId,
              label: label.trim() || null,
              aiModelId: selectedAiModelId,
              minAnswers: minAnswers,
              maxAnswers: maxAnswers,
              useAgentQa: useAgentQa
            },
            headers: {
              authorization: `Bearer ${token}`
            },
            client: apiClient
          })
        }
      }

      if (response.error) {
        throwApiError(response.error, `Failed to ${isEditMode ? 'update' : 'create'} question`)
      }

      const data = response.data
      
      if (isEditMode && question) {
        // Check if we sent any fields that would trigger reprocessing
        const sentReprocessingFields = Object.keys(requestBody).some(key => 
          key !== 'label' // label is the only field that doesn't trigger reprocessing
        )
        
        if (sentReprocessingFields && questionEntitySetId && question) {
          // Invalidate tiles containing this question's entity slice
          invalidateByEntitySetFilter(
            queryClient,
            matrixId,
            questionEntitySetId,
            [question.id]
          )
        }
        
        // Always invalidate the matrix data, questions list, and entity sets to refresh
        await queryClient.invalidateQueries({ queryKey: ['matrix', matrixId] })
        await queryClient.invalidateQueries({ queryKey: ['matrix-questions', matrixId] })
        await queryClient.invalidateQueries({ queryKey: ['matrix-entity-sets', matrixId] })
      }
      
      const optionsText = isSelectType(questionTypeId)
        ? ` with ${options.filter(opt => opt.value.trim()).length} options`
        : ''
      
      toast.success(`Question ${isEditMode ? 'updated' : 'created'} successfully`, {
        description: `${data.questionText.slice(0, 50)}${data.questionText.length > 50 ? '...' : ''}${optionsText}`
      })
      
      onSuccess(data)
    } catch (error) {
      toast.error(`Failed to ${isEditMode ? 'update' : 'create'} question`, {
        description: error instanceof Error ? error.message : 'Please try again'
      })
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
      e.preventDefault()
      if (questionText.trim() && !isSubmitting) {
        handleSubmit()
      }
    } else if (e.key === 'Escape') {
      e.preventDefault()
      onCancel()
    }
  }

  const handleMonacoKeyDown = (e: IKeyboardEvent) => {
    if (e.keyCode === 13 && (e.metaKey || e.ctrlKey)) { // Enter key
      e.preventDefault()
      if (questionText.trim() && !isSubmitting) {
        handleSubmit()
      }
    } else if (e.keyCode === 27) { // Escape key
      e.preventDefault()
      onCancel()
    }
  }

  const isSelectQuestion = isSelectType(questionTypeId)

  return (
    <div className={`w-full space-y-4 ${className}`}>
      {/* Question Type Selector */}
      <div className="flex space-y-2">
        <div className="flex-1 w-full">
        <label className="text-sm font-medium text-muted-foreground">
          Question Type
        </label>
        </div>
        <div className="flex-1 w-full">
        <QuestionTypeSelector
          selectedTypeId={questionTypeId}
          onTypeSelect={handleTypeSelect}
          disabled={isSubmitting}
          className="w-full"
        />
        </div>
      </div>

      {/* AI Model Selector */}
      {aiProviders.length > 0 && aiModels.length > 0 && (
        <AIModelSelector
          providers={aiProviders}
          models={aiModels}
          selectedModelId={selectedAiModelId}
          onModelSelect={setSelectedAiModelId}
          disabled={isSubmitting}
        />
      )}

      {/* Agent QA Toggle */}
      <div className="flex items-center justify-between space-x-2">
        <Label htmlFor="use-agent-qa" className="text-sm font-medium text-muted-foreground">
          Agent QA
        </Label>
        <Switch
          id="use-agent-qa"
          checked={useAgentQa}
          onCheckedChange={setUseAgentQa}
          disabled={isSubmitting}
        />
      </div>

      {/* Answer Count Configuration */}
      <div className="space-y-2">
        <label className="text-sm font-medium text-muted-foreground">
          Answer Count Configuration
        </label>
        <div className="flex gap-2">
          <div className="flex-1">
            <label className="text-xs text-muted-foreground mb-1 block">
              Minimum Answers
            </label>
            <Input
              variant="blocky"
              type="number"
              min="1"
              value={minAnswers}
              onChange={(e) => setMinAnswers(Math.max(1, parseInt(e.target.value) || 1))}
              disabled={isSubmitting}
              className="text-sm"
            />
          </div>
          <div className="flex-1">
            <label className="text-xs text-muted-foreground mb-1 block">
              Maximum Answers
            </label>
            <div className="flex gap-1">
              <Input
                variant="blocky"
                type="number"
                min={minAnswers}
                value={maxAnswers || ''}
                onChange={(e) => {
                  const val = parseInt(e.target.value)
                  setMaxAnswers(val ? Math.max(minAnswers, val) : null)
                }}
                placeholder="Unlimited"
                disabled={isSubmitting}
                className="text-sm flex-1"
              />
              <Button
                variant="outline"
                style="blocky"
                size="sm"
                onClick={() => setMaxAnswers(null)}
                disabled={isSubmitting}
                className="px-2 text-xs"
                title="Set to unlimited"
              >
                ∞
              </Button>
            </div>
          </div>
        </div>
        <div className="text-xs text-muted-foreground">
          {minAnswers === maxAnswers 
            ? `Exactly ${minAnswers} answer${minAnswers !== 1 ? 's' : ''} required`
            : maxAnswers === null 
            ? `At least ${minAnswers} answer${minAnswers !== 1 ? 's' : ''} required (unlimited)`
            : `Between ${minAnswers} and ${maxAnswers} answers required`
          }
        </div>
      </div>

      {/* Label */}
      <div className="space-y-2">
        <label className="text-sm font-medium text-muted-foreground">
          Label (optional)
        </label>
        <Input
          variant="blocky"
          value={label}
          onChange={(e) => setLabel(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Enter a label for this question..."
          className="text-sm"
          disabled={isSubmitting}
        />
      </div>

      {/* Question Text */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <label className="text-sm font-medium text-muted-foreground">
            Question Text
          </label>
          {templateVariables.length > 0 && (
            <div className="flex items-center gap-1 text-xs text-muted-foreground">
              <Variable className="h-3 w-3" />
              <span>Use {'${{variableName}}'} syntax</span>
            </div>
          )}
        </div>

        {isCorrelationMatrix && (
          <div className="flex items-start gap-2 p-3 bg-blue-500/10 border border-blue-500/20 rounded-md text-xs text-blue-600 dark:text-blue-400">
            <AlertCircle className="h-4 w-4 mt-0.5 flex-shrink-0" />
            <div>
              <strong>Correlation Matrix:</strong> Questions must include both <code className="px-1 py-0.5 bg-blue-500/20 rounded">${'{{A}}'}</code> and <code className="px-1 py-0.5 bg-blue-500/20 rounded">${'{{B}}'}</code> template variables to reference the left and right documents.
            </div>
          </div>
        )}

        <MonacoTextarea
          variant="blocky"
          value={questionText}
          onChange={(value: string | undefined) => setQuestionText(value || '')}
          onKeyDown={handleMonacoKeyDown}
          placeholder={
            isCorrelationMatrix
              ? "Enter your question... Must include ${'${{A}}'} and ${'${{B}}'} for correlation matrices"
              : templateVariables.length > 0
              ? "Enter your question... Use ${'${{variableName}}'} for template variables"
              : "Enter your question..."
          }
          className="text-md"
          disabled={isSubmitting}
          minHeight={60}
          templateVariables={templateVariables}
        />
      </div>

      {/* Options for select questions */}
      {isSelectQuestion && (
        <div className="space-y-2">
          <label className="text-sm font-medium text-muted-foreground">
            Answer Options
          </label>
          <div className="space-y-2">
            {options.map((option, index) => (
              <div key={index} className="flex items-center gap-2">
                <GripVertical className="h-4 w-4 text-muted-foreground cursor-grab" />
                <Input
                  variant="blocky"
                  placeholder={`Option ${index + 1}`}
                  value={option.value}
                  onChange={(e) => updateOption(index, e.target.value)}
                  disabled={isSubmitting}
                  className="flex-1 text-sm"
                />
                {options.length > 2 && (
                  <Button
                    variant="ghost"
                    style="blocky"
                    size="icon"
                    onClick={() => removeOption(index)}
                    disabled={isSubmitting}
                    className="h-8 w-8"
                  >
                    <X className="h-4 w-4" />
                  </Button>
                )}
              </div>
            ))}
            
            <Button
              variant="ghost"
              style="blocky"
              size="sm"
              onClick={addOption}
              disabled={isSubmitting}
              className="w-full text-sm"
            >
              <Plus className="h-4 w-4 mr-1" />
              Add Option
            </Button>
          </div>
        </div>
      )}


      {/* Action Buttons */}
      <div className="flex gap-2 pt-2">
        <Button
          style="blocky"
          onClick={handleSubmit}
          disabled={!questionText.trim() || isSubmitting}
          className="flex-1"
          size="sm"
        >
          <Check className="h-4 w-4 mr-1" />
          {isEditMode ? 'Update Question' : 'Create Question'}
        </Button>
        <Button
          variant="outline"
          style="blocky"
          onClick={onCancel}
          disabled={isSubmitting}
          size="sm"
        >
          Cancel
        </Button>
      </div>
    </div>
  )
}