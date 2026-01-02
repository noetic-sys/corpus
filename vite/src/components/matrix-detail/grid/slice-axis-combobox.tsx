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
import type { EntityRole } from '@/client/types.gen'

interface AxisOption {
  role: EntityRole
  entitySetId: number
  entitySetName: string
  count: number
}

interface SliceAxisComboboxProps {
  axes: AxisOption[]
  activeAxisRole: string
  onAxisChange: (role: string) => void
}

export interface SliceAxisComboboxHandle {
  open: () => void
}

export const SliceAxisCombobox = forwardRef<SliceAxisComboboxHandle, SliceAxisComboboxProps>(
  ({ axes, activeAxisRole, onAxisChange }, ref) => {
    const [open, setOpen] = useState(false)

    useImperativeHandle(ref, () => ({
      open: () => setOpen(true)
    }))

    const selectedAxis = axes.find(axis => axis.role === activeAxisRole)

    return (
      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger asChild>
          <Button
            variant="outline"
            role="combobox"
            aria-expanded={open}
            className="w-[180px] justify-between h-8"
            style="blocky"
          >
            <div className="flex items-center gap-1.5 overflow-hidden">
              <span className="text-xs text-muted-foreground shrink-0">Slice:</span>
              <span className="truncate font-medium">{selectedAxis?.entitySetName}</span>
            </div>
            <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-[220px] p-0" variant="blocky">
          <Command>
            <CommandInput placeholder="Search axes..." />
            <CommandList>
              <CommandEmpty>No axis found.</CommandEmpty>
              <CommandGroup>
                {axes.map((axis) => (
                  <CommandItem
                    key={axis.role}
                    value={`${axis.entitySetName} ${axis.role}`}
                    onSelect={() => {
                      onAxisChange(axis.role)
                      setOpen(false)
                    }}
                  >
                    <Check
                      className={cn(
                        'mr-2 h-4 w-4',
                        activeAxisRole === axis.role ? 'opacity-100' : 'opacity-0'
                      )}
                    />
                    <div className="flex flex-col flex-1">
                      <span>{axis.entitySetName}</span>
                      <span className="text-xs text-muted-foreground">{axis.role}</span>
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

SliceAxisCombobox.displayName = 'SliceAxisCombobox'
