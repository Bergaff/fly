import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-1.5 whitespace-nowrap rounded-[2px] font-mono uppercase tracking-[0.06em] disabled:pointer-events-none disabled:opacity-40 [&_svg]:pointer-events-none [&_svg]:shrink-0 shrink-0 focus-visible:outline focus-visible:outline-1 focus-visible:outline-offset-1 focus-visible:outline-ring cursor-pointer",
  {
    variants: {
      variant: {
        default: "border border-transparent bg-primary text-primary-foreground hover:bg-primary/85",
        outline: "border border-input bg-transparent hover:bg-accent hover:text-accent-foreground",
        secondary: "border border-transparent bg-secondary text-secondary-foreground hover:bg-secondary/70",
        ghost: "border border-transparent hover:bg-accent hover:text-accent-foreground",
        destructive: "border border-transparent bg-destructive text-background hover:bg-destructive/85",
        link: "text-foreground underline underline-offset-2",
      },
      size: {
        default: "h-8 px-3 text-[11px]",
        sm: "h-7 px-2.5 text-[10px]",
        lg: "h-9 px-4 text-[12px]",
        icon: "size-8 text-[11px]",
        "icon-sm": "size-7 text-[10px]",
      },
    },
    defaultVariants: { variant: "default", size: "default" },
  },
);

function Button({
  className,
  variant,
  size,
  asChild = false,
  ...props
}: React.ComponentProps<"button"> & VariantProps<typeof buttonVariants> & { asChild?: boolean }) {
  const Comp = asChild ? Slot : "button";
  return <Comp data-slot="button" className={cn(buttonVariants({ variant, size, className }))} {...props} />;
}

export { Button, buttonVariants };
