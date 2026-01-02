import * as React from "react"
import { CheckIcon, ChevronsUpDownIcon, Bot } from "lucide-react"

import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { ScrollArea } from "@/components/ui/scroll-area"
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
} from "@/components/ui/command"
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover"
import { type AiModelResponse, type AiProviderResponse } from '@/client'

interface AIModelSelectorProps {
  providers: AiProviderResponse[]
  models: AiModelResponse[]
  selectedModelId?: number | null
  onModelSelect: (modelId: number | null) => void
  disabled?: boolean
  className?: string
}

export function AIModelSelector({
  providers,
  models,
  selectedModelId,
  onModelSelect,
  disabled = false,
  className = ''
}: AIModelSelectorProps) {
  const [open, setOpen] = React.useState(false)
  
  // Find the selected model and its provider
  const selectedModel = selectedModelId ? models.find(m => m.id === selectedModelId) : null
  const selectedProvider = selectedModel?.provider

  // Group models by provider
  const modelsByProvider = models.reduce((acc, model) => {
    const providerId = model.provider?.id
    if (!providerId) return acc
    
    if (!acc[providerId]) {
      acc[providerId] = []
    }
    acc[providerId].push(model)
    return acc
  }, {} as Record<number, AiModelResponse[]>)

  const handleSelect = (value: string) => {
    if (value === 'default') {
      onModelSelect(null)
    } else {
      onModelSelect(parseInt(value))
    }
    setOpen(false)
  }

  return (
    <div className={`space-y-2 ${className}`}>
      <label className="text-sm font-medium text-muted-foreground">
        AI Model (optional)
      </label>
      
      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger asChild>
          <Button
            variant="outline"
            role="combobox"
            aria-expanded={open}
            disabled={disabled}
            className="w-full justify-between"
          >
            {selectedModel ? (
              <div className="flex items-center gap-2">
                <Bot className="h-4 w-4" />
                <span>{selectedModel.displayName}</span>
                {selectedProvider && (
                  <Badge variant="outline" className="text-xs">
                    {selectedProvider.displayName}
                  </Badge>
                )}
              </div>
            ) : (
              <div className="flex items-center gap-2">
                <Bot className="h-4 w-4 text-muted-foreground" />
                <span className="text-muted-foreground">System default</span>
              </div>
            )}
            <ChevronsUpDownIcon className="ml-2 h-4 w-4 shrink-0 opacity-50" />
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-full p-0" align="start" sideOffset={5}>
          <Command>
            <CommandInput placeholder="Search models..." />
              <ScrollArea className="h-72" type="always">
            <CommandEmpty>No model found.</CommandEmpty>
            <CommandList className="max-h-none overflow-visible">
                  {/* Default option */}
                  <CommandGroup>
                    <CommandItem
                      value="default"
                      onSelect={handleSelect}
                    >
                      <CheckIcon
                        className={cn(
                          "mr-2 h-4 w-4",
                          selectedModelId === null ? "opacity-100" : "opacity-0"
                        )}
                      />
                      <Bot className="mr-2 h-4 w-4 text-muted-foreground" />
                      <span>System Default</span>
                      <Badge variant="secondary" className="ml-auto text-xs">Auto</Badge>
                    </CommandItem>
                  </CommandGroup>
                  
                  {/* Provider groups */}
                  {providers.map((provider) => {
                    const providerModels = modelsByProvider[provider.id] || []
                    if (providerModels.length === 0) return null
                    
                    return (
                      <React.Fragment key={provider.id}>
                        <CommandSeparator />
                        <CommandGroup heading={provider.displayName}>
                          {providerModels.map(model => (
                            <CommandItem
                              key={model.id}
                              value={`${model.displayName} ${model.modelName} ${provider.displayName}`}
                              onSelect={() => handleSelect(model.id.toString())}
                            >
                              <CheckIcon
                                className={cn(
                                  "mr-2 h-4 w-4",
                                  selectedModelId === model.id ? "opacity-100" : "opacity-0"
                                )}
                              />
                              <Bot className="mr-2 h-4 w-4" />
                              <span className="flex-1">{model.displayName}</span>
                            </CommandItem>
                          ))}
                        </CommandGroup>
                      </React.Fragment>
                    )
                  })}
            </CommandList>
              </ScrollArea>
          </Command>
        </PopoverContent>

      </Popover>
    </div>
  )
}