import * as RadixScrollArea from '@radix-ui/react-scroll-area'

export function ScrollArea({ children, className = '' }) {
  return (
    <RadixScrollArea.Root className={`h-full w-full ${className}`}> 
      <RadixScrollArea.Viewport className="h-full w-full rounded-xl">
        {children}
      </RadixScrollArea.Viewport>
      <RadixScrollArea.Scrollbar orientation="vertical" className="bg-gray-200 rounded-full w-2" />
    </RadixScrollArea.Root>
  )
} 