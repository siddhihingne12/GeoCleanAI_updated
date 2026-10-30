import * as React from 'react'
import { Slot } from '@radix-ui/react-slot'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '../../lib/utils'

const buttonVariants = cva('inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-xl text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-900 disabled:pointer-events-none disabled:opacity-45 [&_svg]:size-4 [&_svg]:shrink-0', {
  variants: {
    variant: {
      default: 'bg-emerald-600 text-white hover:bg-emerald-500 shadow-lg shadow-emerald-600/20',
      outline: 'border border-slate-600 bg-slate-800/50 text-slate-200 hover:bg-slate-700/60 hover:border-slate-500',
      ghost: 'text-slate-300 hover:bg-slate-800/60 hover:text-slate-100',
      secondary: 'bg-slate-700 text-slate-200 hover:bg-slate-600',
    },
    size: { default: 'h-10 px-4 py-2', sm: 'h-8 rounded-lg px-3 text-xs', icon: 'size-9' },
  }, defaultVariants: { variant: 'default', size: 'default' },
})
export type ButtonProps = React.ButtonHTMLAttributes<HTMLButtonElement> & VariantProps<typeof buttonVariants> & { asChild?: boolean }
export function Button({ className, variant, size, asChild = false, ...props }: ButtonProps) {
  const Comp = asChild ? Slot : 'button'
  return <Comp className={cn(buttonVariants({ variant, size, className }))} {...props} />
}
