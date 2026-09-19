import * as React from "react";
import { cn } from "@/lib/utils";

function Textarea({ className, ...props }: React.ComponentProps<"textarea">) {
  return (
    <textarea
      data-slot="textarea"
      className={cn(
        "field-sizing-content flex min-h-16 w-full rounded-none border border-input bg-transparent px-2 py-1.5 text-[13px] leading-relaxed",
        "placeholder:text-muted-foreground/70 focus-visible:outline focus-visible:outline-1 focus-visible:outline-offset-1 focus-visible:outline-ring",
        "disabled:cursor-not-allowed disabled:opacity-40",
        className,
      )}
      {...props}
    />
  );
}
export { Textarea };
