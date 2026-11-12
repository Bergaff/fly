import * as React from "react";
import { cn } from "@/lib/utils";

function Input({ className, type, ...props }: React.ComponentProps<"input">) {
  return (
    <input
      type={type}
      data-slot="input"
      className={cn(
        "flex h-8 w-full min-w-0 rounded-none border border-input bg-transparent px-2 py-1 text-[13px]",
        "placeholder:text-muted-foreground/70 file:text-foreground selection:bg-foreground selection:text-background",
        "focus-visible:outline focus-visible:outline-1 focus-visible:outline-offset-1 focus-visible:outline-ring",
        "disabled:pointer-events-none disabled:cursor-not-allowed disabled:opacity-40",
        className,
      )}
      {...props}
    />
  );
}
export { Input };
