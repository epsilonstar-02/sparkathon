import * as RadixAvatar from '@radix-ui/react-avatar'

export function Avatar({ sender }) {
  const isUser = sender === 'user'
  return (
    <RadixAvatar.Root className="w-11 h-11 rounded-full flex items-center justify-center border-2 border-blue-200 shadow-lg bg-gradient-to-br from-blue-400 to-blue-700">
      <RadixAvatar.Fallback className="text-lg font-bold text-white" delayMs={0}>
        {isUser ? (
          <span className="w-11 h-11 flex items-center justify-center rounded-full bg-gradient-to-br from-blue-500 to-blue-700 shadow">U</span>
        ) : (
          <span className="w-11 h-11 flex items-center justify-center rounded-full bg-gradient-to-br from-yellow-300 to-yellow-500 shadow">A</span>
        )}
      </RadixAvatar.Fallback>
    </RadixAvatar.Root>
  )
} 