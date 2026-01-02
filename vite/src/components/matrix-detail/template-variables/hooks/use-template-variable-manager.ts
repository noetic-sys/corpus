import { useState } from 'react'
import { useQueryClient, type QueryObserverResult } from '@tanstack/react-query'
import { useAuth } from '@/hooks/useAuth'
import { toast } from 'sonner'
import {
  createTemplateVariableApiV1MatricesMatrixIdTemplateVariablesPost,
  updateTemplateVariableApiV1TemplateVariablesVariableIdPatch,
  deleteTemplateVariableApiV1TemplateVariablesVariableIdDelete
} from '@/client'
import { apiClient } from '@/lib/api'
import type { MatrixTemplateVariableResponse } from '@/client'
import type { Question } from '../../types'
import { getAffectedQuestionIds, validateTemplateString, validateTemplateValue } from '../utils/template-variable-helpers'
import { invalidateByEntitySetFilter } from '../../utils/cache-utils'
import {throwApiError} from "@/lib/api-error.ts";

interface EditingVariable {
  id?: number
  templateString: string
  value: string
  isNew?: boolean
}

export function useTemplateVariableManager(
  matrixId: number,
  questions: Question[],
  questionEntitySetId: number | undefined,
  variables: MatrixTemplateVariableResponse[],
  refetch: () => Promise<QueryObserverResult<MatrixTemplateVariableResponse[], Error>>
) {
  const queryClient = useQueryClient()
  const { getToken } = useAuth()
  const [editingVariables, setEditingVariables] = useState<EditingVariable[]>([])
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [deleteConfirmation, setDeleteConfirmation] = useState<{ variableId: number; templateString: string } | null>(null)

  const invalidateAffectedCells = (templateVariableId: number) => {
    const affectedQuestionIds = getAffectedQuestionIds(templateVariableId, questions)

    if (affectedQuestionIds.length > 0 && questionEntitySetId) {
      // Invalidate tiles containing the specific questions affected by this template variable
      invalidateByEntitySetFilter(
        queryClient,
        matrixId,
        questionEntitySetId,
        affectedQuestionIds
      )
    }
  }

  const startEditing = (variable: MatrixTemplateVariableResponse) => {
    setEditingVariables(prev => [
      ...prev.filter(v => v.id !== variable.id),
      {
        id: variable.id,
        templateString: variable.templateString,
        value: variable.value
      }
    ])
  }

  const addNewVariable = () => {
    const newVar: EditingVariable = {
      templateString: '',
      value: '',
      isNew: true
    }
    setEditingVariables(prev => [...prev, newVar])
  }

  const updateEditingVariable = (index: number, field: keyof EditingVariable, value: string) => {
    setEditingVariables(prev => prev.map((v, i) => 
      i === index ? { ...v, [field]: value } : v
    ))
  }

  const removeEditingVariable = (index: number) => {
    setEditingVariables(prev => prev.filter((_, i) => i !== index))
  }

  const saveVariable = async (editingVar: EditingVariable, index: number) => {
    const templateValidation = validateTemplateString(editingVar.templateString)
    if (!templateValidation.isValid) {
      toast.error(templateValidation.error!)
      return
    }

    const valueValidation = validateTemplateValue(editingVar.value)
    if (!valueValidation.isValid) {
      toast.error(valueValidation.error!)
      return
    }

    setIsSubmitting(true)

    try {
      const token = await getToken()

      if (editingVar.isNew) {
        const response = await createTemplateVariableApiV1MatricesMatrixIdTemplateVariablesPost({
          path: { matrixId },
          body: {
            templateString: editingVar.templateString.trim(),
            value: editingVar.value.trim()
          },
          headers: {
            authorization: `Bearer ${token}`
          },
          client: apiClient
        })

        if (response.error) {
          throwApiError(response.error, 'Failed to create template variable')
        }
      } else {
        const response = await updateTemplateVariableApiV1TemplateVariablesVariableIdPatch({
          path: { variableId: editingVar.id! },
          body: {
            templateString: editingVar.templateString.trim(),
            value: editingVar.value.trim()
          },
          headers: {
            authorization: `Bearer ${token}`
          },
          client: apiClient
        })

        if (response.error) {
          throwApiError(response.error, 'Failed to update template variable')
        }
      }

      if (!editingVar.isNew && editingVar.id) {
        const originalVariable = variables.find(v => v.id === editingVar.id)
        
        if (originalVariable && originalVariable.value !== editingVar.value.trim()) {
          invalidateAffectedCells(editingVar.id)
        }
      }

      setEditingVariables(prev => prev.filter((_, i) => i !== index))
      
      await refetch()
      
      toast.success(`Template variable "${editingVar.templateString}" ${editingVar.isNew ? 'created' : 'updated'} successfully`)
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Failed to save template variable')
    } finally {
      setIsSubmitting(false)
    }
  }

  const showDeleteConfirmation = (variableId: number, templateString: string) => {
    setDeleteConfirmation({ variableId, templateString })
  }

  const cancelDelete = () => {
    setDeleteConfirmation(null)
  }

  const confirmDelete = async () => {
    if (!deleteConfirmation) return

    setIsSubmitting(true)

    try {
      invalidateAffectedCells(deleteConfirmation.variableId)

      const token = await getToken()
      const response = await deleteTemplateVariableApiV1TemplateVariablesVariableIdDelete({
        path: { variableId: deleteConfirmation.variableId },
        headers: {
          authorization: `Bearer ${token}`
        },
        client: apiClient
      })

      if (response.error) {
        throwApiError(response.error, 'Failed to delete template variable')
      }

      await refetch()
      toast.success(`Template variable "${deleteConfirmation.templateString}" deleted successfully`)
      setDeleteConfirmation(null)
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Failed to delete template variable')
    } finally {
      setIsSubmitting(false)
    }
  }

  const isVariableBeingEdited = (variableId: number) => {
    return editingVariables.some(v => v.id === variableId)
  }

  return {
    editingVariables,
    isSubmitting,
    deleteConfirmation,
    startEditing,
    addNewVariable,
    updateEditingVariable,
    removeEditingVariable,
    saveVariable,
    showDeleteConfirmation,
    cancelDelete,
    confirmDelete,
    isVariableBeingEdited
  }
}