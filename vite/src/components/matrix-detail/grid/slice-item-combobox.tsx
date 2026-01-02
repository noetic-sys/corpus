import { useState, forwardRef, useImperativeHandle } from 'react'
import { Check, ChevronsUpDown } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from '@/components/ui/command'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover'

interface SliceOption {
  value: string
  label: string
  description?: string
}

interface SliceItemComboboxProps {
  axisName: string
  options: SliceOption[]
  selectedIndex: number
  onIndexChange: (index: number) => void
}

export interface SliceItemComboboxHandle {
  open: () => void
}

export const SliceItemCombobox = forwardRef<SliceItemComboboxHandle, SliceItemComboboxProps>(
  ({ axisName, options, selectedIndex, onIndexChange }, ref) => {
    const [open, setOpen] = useState(false)

    useImperativeHandle(ref, () => ({
      open: () => setOpen(true)
    }))

    const selectedOption = options[selectedIndex]

    return (
      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger asChild>
          <Button
            variant="outline"
            role="combobox"
            aria-expanded={open}
            className="w-[320px] justify-between h-8"
            style="blocky"
          >
            <div className="flex items-center gap-2 overflow-hidden flex-1 min-w-0">
              <span className="font-medium truncate">{selectedOption?.label}</span>
              {selectedOption?.description && selectedOption.description !== selectedOption.label && (
                <>
                  <span className="text-muted-foreground">•</span>
                  <span className="text-xs text-muted-foreground truncate">
                    {selectedOption.description}
                  </span>
                </>
              )}
            </div>
            <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-[400px] p-0" variant="blocky">
          <Command>
            <CommandInput placeholder={`Search ${axisName.toLowerCase()}...`} />
            <CommandList>
              <CommandEmpty>No {axisName.toLowerCase()} found.</CommandEmpty>
              <CommandGroup>
                {options.map((option, idx) => (
                  <CommandItem
                    key={option.value}
                    value={`${option.label} ${option.description || ''}`}
                    onSelect={() => {
                      onIndexChange(idx)
                      setOpen(false)
                    }}
                  >
                    <Check
                      className={cn(
                        'mr-2 h-4 w-4',
                        selectedIndex === idx ? 'opacity-100' : 'opacity-0'
                      )}
                    />
                    <div className="flex flex-col flex-1 overflow-hidden">
                      <span className="font-medium truncate">{option.label}</span>
                      {option.description && option.description !== option.label && (
                        <span className="text-xs text-muted-foreground truncate">
                          {option.description}
                        </span>
                      )}
                    </div>
                  </CommandItem>
                ))}
              </CommandGroup>
            </CommandList>
          </Command>
        </PopoverContent>
      </Popover>
    )
  }
)

SliceItemCombobox.displayName = 'SliceItemCombobox'
