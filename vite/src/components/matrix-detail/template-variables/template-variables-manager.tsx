import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Plus, Variable, AlertTriangle } from 'lucide-react'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { useTemplateVariables } from '../hooks/use-template-variables'
import { useTemplateVariableManager } from './hooks/use-template-variable-manager'
import { TemplateVariableCard } from './template-variable-card'
import { TemplateVariableForm } from './template-variable-form'
import { TemplateVariablesEmptyState } from './template-variables-empty-state'
import { TemplateVariablesLoadingState } from './template-variables-loading-state'
import type { Question } from '../types'

interface TemplateVariablesManagerProps {
  matrixId: number
  questions: Question[]
  questionEntitySetId?: number
  className?: string
}

export function TemplateVariablesManager({ matrixId, questions, questionEntitySetId, className = '' }: TemplateVariablesManagerProps) {
  const { data: variables = [], isLoading, refetch } = useTemplateVariables(matrixId)
  const {
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
  } = useTemplateVariableManager(matrixId, questions, questionEntitySetId, variables, refetch)

  if (isLoading) {
    return <TemplateVariablesLoadingState className={className} />
  }

  return (
    <div className={`space-y-4 ${className}`}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Variable className="h-5 w-5" />
          <h3 className="text-lg font-semibold">Template Variables</h3>
          <Badge variant="secondary" style="blocky" className="text-xs border-[1px]">
            {variables.length}
          </Badge>
        </div>
        <Button 
          size="sm" 
          style="blocky"
          onClick={addNewVariable}
          disabled={isSubmitting}
          className="gap-1 border-[1px]"
        >
          <Plus className="h-4 w-4" />
          Add Variable
        </Button>
      </div>

      {deleteConfirmation && (
        <Alert variant="destructive" style="blocky" className="mb-4 border-[1px]">
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription className="flex items-center justify-between">
            <span>
              Are you sure you want to delete template variable &quot;{deleteConfirmation.templateString}&quot;? This action cannot be undone.
            </span>
            <div className="flex gap-2 ml-4">
              <Button 
                size="sm" 
                variant="outline" 
                style="blocky"
                onClick={cancelDelete}
                disabled={isSubmitting}
                className="border-[1px]"
              >
                Cancel
              </Button>
              <Button 
                size="sm" 
                variant="destructive" 
                style="blocky"
                onClick={confirmDelete}
                disabled={isSubmitting}
                className="border-[1px]"
              >
                {isSubmitting ? 'Deleting...' : 'Delete'}
              </Button>
            </div>
          </AlertDescription>
        </Alert>
      )}

      <div className="space-y-3">
        {/* Existing Variables */}
        {variables.map((variable) => {
          const isEditing = isVariableBeingEdited(variable.id)
          const editingVar = editingVariables.find(v => v.id === variable.id)
          
          return isEditing && editingVar ? (
            <TemplateVariableForm
              key={variable.id}
              variable={editingVar}
              index={editingVariables.indexOf(editingVar)}
              isSubmitting={isSubmitting}
              onUpdate={updateEditingVariable}
              onSave={saveVariable}
              onCancel={removeEditingVariable}
            />
          ) : (
            <TemplateVariableCard
              key={variable.id}
              variable={variable}
              isSubmitting={isSubmitting}
              onEdit={startEditing}
              onDelete={showDeleteConfirmation}
            />
          )
        })}

        {/* New Variables Being Added */}
        {editingVariables.filter(v => v.isNew).map((editingVar, index) => (
          <TemplateVariableForm
            key={`new-${index}`}
            variable={editingVar}
            index={editingVariables.indexOf(editingVar)}
            isSubmitting={isSubmitting}
            onUpdate={updateEditingVariable}
            onSave={saveVariable}
            onCancel={removeEditingVariable}
          />
        ))}

        {variables.length === 0 && editingVariables.length === 0 && (
          <TemplateVariablesEmptyState />
        )}
      </div>
    </div>
  )
}