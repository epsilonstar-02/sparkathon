import { useState, useRef, useEffect } from 'react'
import { Card } from '../components/Card'
import { Avatar } from '../components/Avatar'
import { ScrollArea } from '../components/ScrollArea'
import { MessageInput } from '../components/MessageInput'
import { motion, AnimatePresence } from 'framer-motion'

export default function Chat() {
  // Placeholder state for chat and thoughts
  const [chat, setChat] = useState([
    { id: 1, sender: 'user', text: 'Hi, I need help planning my groceries.' },
    { id: 2, sender: 'agent', text: 'Of course! What meals are you planning this week?' }
  ])
  const [thoughts, setThoughts] = useState([
    { id: 1, text: 'Analyzing user intent...' },
    { id: 2, text: 'Suggesting meal plan options.' }
  ])
  const [input, setInput] = useState('')
  const [thinking, setThinking] = useState(false)

  // Simulate backend response
  const handleSend = (msg) => {
    if (!msg.trim()) return
    setChat(c => [...c, { id: Date.now(), sender: 'user', text: msg }])
    setInput('')
    setThinking(true)
    setTimeout(() => {
      setThoughts(t => [...t, { id: Date.now(), text: 'Thinking about best options...' }])
      setTimeout(() => {
        setChat(c => [...c, { id: Date.now(), sender: 'agent', text: 'Here are some personalized suggestions for you!' }])
        setThinking(false)
      }, 1200)
    }, 1000)
  }

  return (
    <div className="flex flex-col h-[80vh] rounded-2xl shadow-2xl bg-white/70 backdrop-blur-lg overflow-hidden border border-blue-100">
      <div className="flex flex-1 min-h-0">
        {/* Chat Area */}
        <ScrollArea className="flex-1 p-8 space-y-5 border-r min-w-0 bg-gradient-to-br from-blue-50/60 to-white/80">
          <AnimatePresence>
            {chat.map(msg => (
              <motion.div
                key={msg.id}
                initial={{ opacity: 0, y: 30 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: 30 }}
                transition={{ duration: 0.35, type: 'spring', bounce: 0.3 }}
              >
                <Card className={`flex items-start gap-4 p-5 ${msg.sender === 'user' ? 'bg-blue-50/80 ml-auto' : 'bg-yellow-50/80 mr-auto'} border-0 shadow-md`}> 
                  <Avatar sender={msg.sender} />
                  <div>
                    <div className="font-semibold text-sm text-blue-700 mb-1">{msg.sender === 'user' ? 'You' : 'Walmart AI'}</div>
                    <div className="text-gray-900 text-base leading-relaxed">{msg.text}</div>
                  </div>
                </Card>
              </motion.div>
            ))}
          </AnimatePresence>
        </ScrollArea>
        {/* Thought Stream */}
        <ScrollArea className="w-[30%] min-w-[220px] max-w-xs p-6 space-y-4 bg-gradient-to-br from-blue-100/80 to-white/80">
          <div className="font-bold text-blue-700 mb-2 text-lg tracking-tight">Agent Thought Stream</div>
          <AnimatePresence>
            {thoughts.map(thought => (
              <motion.div
                key={thought.id}
                initial={{ opacity: 0, x: 30 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 30 }}
                transition={{ duration: 0.3 }}
              >
                <Card className="p-4 bg-white/90 shadow-sm border-l-4 border-blue-400">
                  <div className="text-gray-700 text-sm">{thought.text}</div>
                </Card>
              </motion.div>
            ))}
            {thinking && (
              <motion.div
                key="thinking"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.4, repeat: Infinity, repeatType: 'reverse' }}
              >
                <Card className="p-4 bg-blue-50/80 border-l-4 border-blue-400 animate-pulse">
                  <div className="text-blue-600 font-medium flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-blue-400 animate-pulse"></span>
                    Thinking...
                  </div>
                </Card>
              </motion.div>
            )}
          </AnimatePresence>
        </ScrollArea>
      </div>
      {/* Input Area */}
      <div className="border-t p-6 bg-gradient-to-br from-blue-50/80 to-white/80 shadow-inner">
        <div className="max-w-2xl mx-auto">
          <MessageInput
            value={input}
            onChange={e => setInput(e.target.value)}
            onSend={() => handleSend(input)}
          />
        </div>
      </div>
    </div>
  )
} 