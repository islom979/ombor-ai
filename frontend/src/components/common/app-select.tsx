"use client"

import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { cn } from "@/lib/utils"

export interface SelectOption<T extends string = string> {
  value: T
  label: string
}

interface AppSelectProps<T extends string> {
  value: T | null
  onChange: (value: T) => void
  options: SelectOption<T>[]
  placeholder?: string
  className?: string
  disabled?: boolean
  id?: string
}

/** shadcn (Base UI) Select ustidan qulay o'ram: qiymat → yorliq xaritasi avtomatik. */
export function AppSelect<T extends string>({
  value,
  onChange,
  options,
  placeholder = "Tanlang...",
  className,
  disabled,
  id,
}: AppSelectProps<T>) {
  return (
    <Select<T>
      value={value}
      onValueChange={(next) => next !== null && onChange(next as T)}
      items={options}
      disabled={disabled}
    >
      <SelectTrigger id={id} className={cn("w-full", className)}>
        <SelectValue placeholder={placeholder} />
      </SelectTrigger>
      <SelectContent>
        {options.map((option) => (
          <SelectItem key={option.value} value={option.value}>
            {option.label}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  )
}
