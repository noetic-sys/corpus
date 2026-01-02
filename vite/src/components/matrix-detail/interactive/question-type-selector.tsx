import { useState } from 'react'
import { useAuth } from '@/hooks/useAuth'
import { useQuery } from '@tanstack/react-query'
import { Button } from "@/components/ui/button"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList } from "@/components/ui/command"
import { Check, ChevronsUpDown } from "lucide-react"
import { cn } from "@/lib/utils"
import { getQuestionTypeIcon, getQuestionTypeDisplayName } from "@/lib/question-types"
import { getQuestionTypes } from '@/client'
import { apiClient } from '@/lib/api'
import type { QuestionTypeResponse } from '@/client'
import {throwApiError} from "@/lib/api-error.ts";

interface QuestionTypeSelectorProps {
  selectedTypeId?: number
  onTypeSelect: (typeId: number, typeName: string) => void
  disabled?: boolean
  className?: string
}


export function QuestionTypeSelector({
  selectedTypeId = 1,
  onTypeSelect,
  disabled = false,
  className = ''
}: QuestionTypeSelectorProps) {
  const { getToken } = useAuth()
  const [isOpen, setIsOpen] = useState(false)

  const { data: questionTypes = [], isLoading } = useQuery({
    queryKey: ['question-types'],
    queryFn: async (): Promise<QuestionTypeResponse[]> => {
      const token = await getToken()

      const response = await getQuestionTypes({
        headers: {
          authorization: `Bearer ${token}`
        },
        client: apiClient
      })

      if (response.error) {
        throwApiError(response.error, 'Failed to fetch question types')
      }

      return response.data || []
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
    gcTime: 10 * 60 * 1000, // 10 minutes
  })

  const selectedType = questionTypes.find(type => type.id === selectedTypeId)
  const selectedTypeName = selectedType?.name || 'SHORT_ANSWER'
  const displayName = getQuestionTypeDisplayName(selectedTypeName)
  const SelectedIcon = getQuestionTypeIcon(selectedTypeName)

  if (isLoading) {
    return (
      <div className={`h-10 w-full bg-gray-200 rounded animate-pulse ${className}`} />
    )
  }

  return (
    <Popover open={isOpen} onOpenChange={setIsOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          style="blocky"
          role="combobox"
          aria-expanded={isOpen}
          className={`w-full justify-between ${className}`}
          disabled={disabled}
        >
          <div className="flex items-center gap-2">
            <SelectedIcon className="h-4 w-4" />
            {displayName}
          </div>
          <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
        </Button>
      </PopoverTrigger>
      <PopoverContent variant="blocky" className="w-[200px] p-0">
        <Command variant="blocky">
          <CommandInput placeholder="Search question type..." />
          <CommandList>
            <CommandEmpty>No question type found.</CommandEmpty>
            <CommandGroup>
              {questionTypes.map((type) => {
                const typeDisplayName = getQuestionTypeDisplayName(type.name)
                const TypeIcon = getQuestionTypeIcon(type.name)
                const isSelected = type.id === selectedTypeId

                return (
                  <CommandItem
                    key={type.id}
                    variant="blocky"
                    value={typeDisplayName}
                    onSelect={() => {
                      onTypeSelect(type.id, type.name)
                      setIsOpen(false)
                    }}
                  >
                    <Check
                      className={cn(
                        "mr-2 h-4 w-4",
                        isSelected ? "opacity-100" : "opacity-0"
                      )}
                    />
                    <TypeIcon className="h-4 w-4" />
                    {typeDisplayName}
                  </CommandItem>
                )
              })}
            </CommandGroup>
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  )
}