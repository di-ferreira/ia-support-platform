"use client";

import * as RadixSelect from "@radix-ui/react-select";
import { Check, ChevronDown } from "lucide-react";

import { cn } from "@/lib/utils";

interface SelectProps {
  valor: string;
  onValorChange: (valor: string) => void;
  placeholder?: string;
  id?: string;
  className?: string;
  "aria-label"?: string;
  children: React.ReactNode;
}

export function Select({
  valor,
  onValorChange,
  placeholder = "Selecione",
  id,
  className,
  "aria-label": ariaLabel,
  children,
}: SelectProps) {
  return (
    <RadixSelect.Root value={valor || undefined} onValueChange={onValorChange}>
      <RadixSelect.Trigger
        id={id}
        aria-label={ariaLabel}
        className={cn(
          "inline-flex h-8 items-center justify-between gap-2 rounded-md border border-neutral-300 bg-white px-2 text-xs text-neutral-700",
          "focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-500",
          className
        )}
      >
        <RadixSelect.Value placeholder={placeholder} />
        <RadixSelect.Icon>
          <ChevronDown className="h-3 w-3" aria-hidden="true" />
        </RadixSelect.Icon>
      </RadixSelect.Trigger>

      <RadixSelect.Portal>
        <RadixSelect.Content
          position="popper"
          className="z-50 overflow-hidden rounded-md border border-neutral-200 bg-white shadow-lg"
        >
          <RadixSelect.Viewport className="p-1">{children}</RadixSelect.Viewport>
        </RadixSelect.Content>
      </RadixSelect.Portal>
    </RadixSelect.Root>
  );
}

interface SelectItemProps {
  value: string;
  children: React.ReactNode;
}

export function SelectItem({ value, children }: SelectItemProps) {
  return (
    <RadixSelect.Item
      value={value}
      className="flex cursor-pointer items-center justify-between gap-2 rounded px-2 py-1 text-xs text-neutral-700 outline-none data-[highlighted]:bg-primary-50 data-[highlighted]:text-primary-700"
    >
      <RadixSelect.ItemText>{children}</RadixSelect.ItemText>
      <RadixSelect.ItemIndicator>
        <Check className="h-3 w-3" aria-hidden="true" />
      </RadixSelect.ItemIndicator>
    </RadixSelect.Item>
  );
}
