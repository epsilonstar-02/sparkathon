

export function MessageInput({ value, onChange, onSend }) {
  return (
    <form
      className="flex gap-2 items-center"
      onSubmit={e => {
        e.preventDefault()
        onSend()
      }}
    >
      <input
        className="flex-1 rounded-lg border px-4 py-2 text-base shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
        type="text"
        placeholder="Type your message..."
        value={value}
        onChange={onChange}
        
      />
      <button
        type="submit"
        className="bg-blue-600 text-white px-5 py-2 rounded-lg font-semibold shadow hover:bg-blue-700 transition"
      >
        Send
      </button>
    </form>
  )
} 