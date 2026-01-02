import { useState, useEffect } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Checkbox } from "@/components/ui/checkbox"
import { Copy, Loader2 } from "lucide-react"
import { useMatrixTemplateVariables } from './hooks/use-matrix-template-variables'
import type { EntitySetResponse } from '@/client'

const templateVariableOverrideSchema = z.object({
  templateVariableId: z.number(),
  newValue: z.string(),
})

const duplicateMatrixSchema = z.object({
  name: z.string().min(1, 'Matrix name is required'),
  description: z.string().optional(),
  entitySetIds: z.array(z.number()),
  templateVariableOverrides: z.array(templateVariableOverrideSchema).optional(),
})

type DuplicateMatrixFormData = z.infer<typeof duplicateMatrixSchema>

interface MatrixDuplicationFormProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  matrixId: number
  matrixName: string
  entitySets: EntitySetResponse[]
  onSubmit: (data: DuplicateMatrixFormData) => Promise<void>
  isLoading?: boolean
}

export function MatrixDuplicationForm({
  open,
  onOpenChange,
  matrixId,
  matrixName,
  entitySets,
  onSubmit,
  isLoading = false
}: MatrixDuplicationFormProps) {
  const [templateVariableValues, setTemplateVariableValues] = useState<Record<number, string>>({})

  const { data: templateVariables = [], isLoading: isLoadingTemplateVars } = useMatrixTemplateVariables(matrixId)

  const form = useForm<DuplicateMatrixFormData>({
    resolver: zodResolver(duplicateMatrixSchema),
    defaultValues: {
      name: `${matrixName} (Copy)`,
      description: '',
      entitySetIds: entitySets.map(es => es.id), // All selected by default
      templateVariableOverrides: [],
    },
  })

  // Initialize template variable values when data loads
  useEffect(() => {
    if (templateVariables.length > 0) {
      const initialValues: Record<number, string> = {}
      templateVariables.forEach(tv => {
        if (!(tv.id in templateVariableValues)) {
          initialValues[tv.id] = tv.value
        }
      })
      if (Object.keys(initialValues).length > 0) {
        setTemplateVariableValues(prev => ({ ...prev, ...initialValues }))
      }
    }
  }, [templateVariables, templateVariableValues])

  const handleSubmit = async (data: DuplicateMatrixFormData) => {
    // Build template variable overrides from the form state
    const overrides = templateVariables
      .filter(tv => templateVariableValues[tv.id] !== tv.value)
      .map(tv => ({
        templateVariableId: tv.id,
        newValue: templateVariableValues[tv.id] || tv.value,
      }))

    const submitData = {
      ...data,
      templateVariableOverrides: overrides.length > 0 ? overrides : undefined,
    }

    await onSubmit(submitData)
  }

  const handleTemplateVariableChange = (templateVariableId: number, value: string) => {
    setTemplateVariableValues(prev => ({
      ...prev,
      [templateVariableId]: value,
    }))
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[600px] max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Copy className="h-5 w-5" />
            Duplicate Matrix
          </DialogTitle>
          <DialogDescription>
            Create a copy of &quot;{matrixName}&quot; with custom settings and template variable values.
          </DialogDescription>
        </DialogHeader>

        <Form {...form}>
          <form onSubmit={form.handleSubmit(handleSubmit)} className="space-y-6">
            <FormField
              control={form.control}
              name="name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Matrix Name</FormLabel>
                  <FormControl>
                    <Input placeholder="Enter matrix name" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="description"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Description (Optional)</FormLabel>
                  <FormControl>
                    <Textarea 
                      placeholder="Enter matrix description" 
                      {...field} 
                      rows={3}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="entitySetIds"
              render={() => (
                <FormItem>
                  <div className="mb-4">
                    <FormLabel className="text-base">Entity Sets to Duplicate</FormLabel>
                    <FormDescription>
                      Select which entity sets to include in the duplicated matrix.
                    </FormDescription>
                  </div>
                  {entitySets.map((entitySet) => (
                    <FormField
                      key={entitySet.id}
                      control={form.control}
                      name="entitySetIds"
                      render={({ field }) => {
                        return (
                          <FormItem
                            key={entitySet.id}
                            className="flex flex-row items-start space-x-3 space-y-0"
                          >
                            <FormControl>
                              <Checkbox
                                checked={field.value?.includes(entitySet.id)}
                                onCheckedChange={(checked) => {
                                  return checked
                                    ? field.onChange([...field.value, entitySet.id])
                                    : field.onChange(
                                        field.value?.filter(
                                          (value) => value !== entitySet.id
                                        )
                                      )
                                }}
                              />
                            </FormControl>
                            <div className="space-y-1 leading-none">
                              <FormLabel className="font-normal">
                                {entitySet.name}
                              </FormLabel>
                              <FormDescription>
                                {entitySet.entityType} • {entitySet.members?.length || 0} members
                              </FormDescription>
                            </div>
                          </FormItem>
                        )
                      }}
                    />
                  ))}
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* Template Variables Section */}
            {isLoadingTemplateVars && (
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin" />
                Loading template variables...
              </div>
            )}

            {templateVariables.length > 0 && (
              <div className="space-y-4">
                <div>
                  <h4 className="text-sm font-medium">Template Variables</h4>
                  <p className="text-sm text-muted-foreground">
                    Customize the values for template variables in the duplicated matrix.
                  </p>
                </div>
                
                <div className="space-y-3 max-h-48 overflow-y-auto border rounded-md p-3">
                  {templateVariables.map((templateVar) => (
                    <div key={templateVar.id} className="space-y-2">
                      <div className="flex items-center justify-between">
                        <label className="text-sm font-medium">
                          ${`{{${templateVar.templateString}}}`}
                        </label>
                        <span className="text-xs text-muted-foreground">
                          ID: {templateVar.id}
                        </span>
                      </div>
                      <Input
                        value={templateVariableValues[templateVar.id] || templateVar.value}
                        onChange={(e) => handleTemplateVariableChange(templateVar.id, e.target.value)}
                        placeholder={`Original: ${templateVar.value}`}
                      />
                    </div>
                  ))}
                </div>
              </div>
            )}

            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => onOpenChange(false)}
                disabled={isLoading}
              >
                Cancel
              </Button>
              <Button type="submit" disabled={isLoading}>
                {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                Duplicate Matrix
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  )
}