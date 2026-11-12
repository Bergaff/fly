import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center gap-1.5 rounded-none border px-1.5 py-px font-mono text-[10px] uppercase tracking-[0.06em] w-fit whitespace-nowrap shrink-0 [&>svg]:size-3 [&>svg]:pointer-events-none",
  {
    variants: {
      variant: {
        default: "border-foreground/30 bg-foreground/5 text-foreground",
        secondary: "border-border bg-transparent text-muted-foreground",
        destructive: "border-destructive/50 bg-transparent text-destructive",
        outline: "border-border bg-transparent text-foreground",
      },
    },
    defaultVariants: { variant: "default" },
  },
);

function Badge({ className, variant, style, ...props }: React.ComponentProps<"span"> & VariantProps<typeof badgeVariants>) {
  return <span data-slot="badge" className={cn(badgeVariants({ variant }), className)} style={style} {...props} />;
}

export { Badge, badgeVariants };
