import { useState, useRef, useEffect, useContext } from 'react'
import { Card } from '../components/Card'
import { Avatar } from '../components/Avatar'
import { ScrollArea } from '../components/ScrollArea'
import { MessageInput } from '../components/MessageInput'
import { motion, AnimatePresence } from 'framer-motion'
import { PremiumUserContext } from '../App'
import Button from '../components/Button'

function useEphemeralThoughts(thoughts, setThoughts, isPremium) {
  useEffect(() => {
    if (!isPremium) return
    if (thoughts.length === 0) return
    const timers = thoughts.map((thought, idx) =>
      setTimeout(() => {
        setThoughts(t => t.filter(t2 => t2.id !== thought.id))
      }, 3500 + idx * 400)
    )
    return () => timers.forEach(clearTimeout)
  }, [thoughts, setThoughts, isPremium])
}

// Helper to get real-time timestamp
function getTimestamp() {
  return new Date().toLocaleTimeString('en-US', { hour12: false })
}

// Mock backend call for multi-step reasoning
async function mockAgentAPI(userInput) {
  // Simulate multi-step reasoning with delays
  const baseTime = Date.now()
  const sleep = ms => new Promise(res => setTimeout(res, ms))
  let agent_thoughts = []
  let intent = null
  let products = []
  let recommendations = []
  let actions_taken = []
  let response = ''
  let success = true
  let error = null

  // Step 1: Analyze intent
  agent_thoughts.push(`[${getTimestamp()}] Analyzing user intent for: '${userInput}'`)
  await sleep(600)
  if (/oatmeal|cereal|breakfast/i.test(userInput)) {
    intent = 'product_interest'
  } else {
    intent = 'general_chat'
  }
  agent_thoughts.push(`[${getTimestamp()}] Detected intent: ${intent}`)
  await sleep(600)
  // Step 2: Take actions
  agent_thoughts.push(`[${getTimestamp()}] Executing actions for intent: ${intent}`)
  await sleep(600)
  if (intent === 'product_interest') {
    products = [
      { name: 'Quaker Old Fashioned Oats', id: 1 },
      { name: 'Great Value Instant Oatmeal', id: 2 }
    ]
    actions_taken.push('Searched for oatmeal products')
    agent_thoughts.push(`[${getTimestamp()}] Found ${products.length} products`)
    await sleep(600)
    recommendations = [
      'Try adding fresh fruit to your oatmeal for extra flavor!',
      'Consider steel-cut oats for a heartier texture.'
    ]
    agent_thoughts.push(`[${getTimestamp()}] Generated ${recommendations.length} recommendations`)
    await sleep(600)
  } else {
    actions_taken.push('Retrieved current shopping list')
    agent_thoughts.push(`[${getTimestamp()}] No product search needed`)
    await sleep(600)
  }
  // Step 3: Formulate response
  agent_thoughts.push(`[${getTimestamp()}] Formulating final response`)
  await sleep(600)
  if (intent === 'product_interest') {
    response = `Great choice! Here are some oatmeal options at Walmart:\n\n${products.map(p => `* ${p.name}`).join('\n')}\n\nWould you like tips on recipes or toppings?`
  } else {
    response = "Hi there! How can I help you with your shopping today?"
  }
  agent_thoughts.push(`[${getTimestamp()}] Response generated successfully`)
  return {
    response,
    products,
    recommendations,
    actions_taken,
    agent_thoughts,
    intent,
    success,
    error
  }
}

// Helper to parse timestamp and message from agent_thoughts string
function parseThought(thought) {
  const match = thought.match(/^\[(.*?)\]\s*(.*)$/)
  if (match) {
    return { time: match[1], text: match[2] }
  }
  return { time: '', text: thought }
}

function LoaderIcon() {
  return (
    <span className="inline-block w-4 h-4 mr-2 align-middle">
      <svg className="animate-spin" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="#6366f1" strokeWidth="4" fill="none"/><path className="opacity-75" fill="#6366f1" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"/></svg>
    </span>
  )
}
function TickIcon() {
  return (
    <span className="inline-block w-4 h-4 mr-2 align-middle">
      <svg viewBox="0 0 20 20" fill="#22c55e"><path fillRule="evenodd" d="M16.707 6.293a1 1 0 00-1.414 0L9 12.586l-2.293-2.293a1 1 0 00-1.414 1.414l3 3a1 1 0 001.414 0l7-7a1 1 0 000-1.414z" clipRule="evenodd"/></svg>
    </span>
  )
}

// Sample agent_thoughts JSON for demo
const sampleAgentThoughts = [
  "[12:07:16] Analyzing user intent for: 'I like oatmeal'",
  "[12:07:16] Detected intent: general_chat",
  "[12:07:16] Executing actions for intent: general_chat",
  "[12:07:19] Completed 1 actions",
  "[12:07:19] Generating personalized recommendations",
  "[12:07:19] Generated 0 recommendations",
  "[12:07:19] Formulating final response",
  "[12:07:20] Response generated successfully"
]

export default function Chat() {
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
  const { isPremium } = useContext(PremiumUserContext)

  // Multi-step state
  const [products, setProducts] = useState([])
  const [recommendations, setRecommendations] = useState([])
  const [actionsTaken, setActionsTaken] = useState([])
  const [agentThoughts, setAgentThoughts] = useState([])
  const [intent, setIntent] = useState('')
  const [success, setSuccess] = useState(true)
  const [error, setError] = useState(null)

  const chatEndRef = useRef(null)
  const agentThoughtsScrollRef = useRef(null)
  const [showScrollToBottom, setShowScrollToBottom] = useState(false)

  // Premium Copilot-style fixed overlay state
  const [premiumThoughts, setPremiumThoughts] = useState([]) // [{text, status: 'loading'|'done'}]
  const [currentPremiumStep, setCurrentPremiumStep] = useState(0)

  // For demo, use sampleAgentThoughts as the agent_thoughts
  const [displayedSteps, setDisplayedSteps] = useState([]) // [{text, time, status: 'loading'|'done'}]
  const [currentStep, setCurrentStep] = useState(0)

  const [showAgentPanel, setShowAgentPanel] = useState(true)

  useEphemeralThoughts(thoughts, setThoughts, isPremium)

  // Auto-scroll chat to bottom when chat changes
  useEffect(() => {
    if (chatEndRef.current) {
      chatEndRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [chat])

  // Typing effect for agent thoughts
  function TypingThought({ text }) {
    const [displayed, setDisplayed] = useState('')
    useEffect(() => {
      let i = 0
      const interval = setInterval(() => {
        setDisplayed(text.slice(0, i + 1))
        i++
        if (i >= text.length) clearInterval(interval)
      }, 18)
      return () => clearInterval(interval)
    }, [text])
    return <span>{displayed}</span>
  }

  // Animate agent thoughts step-by-step with loader/tick
  useEffect(() => {
    if (!isPremium || !Array.isArray(agentThoughts) || agentThoughts.length === 0) return
    setPremiumThoughts([])
    setCurrentPremiumStep(0)
    let cancelled = false
    async function runSteps() {
      for (let i = 0; i < agentThoughts.length; ++i) {
        if (cancelled) break
        setPremiumThoughts(prev => [...prev, { text: agentThoughts[i].text, status: 'loading', id: Date.now() + i }])
        await new Promise(res => setTimeout(res, 900))
        if (cancelled) break
        setPremiumThoughts(prev => prev.map((t, idx) => idx === i ? { ...t, status: 'done' } : t))
        await new Promise(res => setTimeout(res, 500))
        setCurrentPremiumStep(i + 1)
      }
    }
    runSteps()
    return () => { cancelled = true }
  }, [agentThoughts, isPremium])

  // Animate steps one by one: loading → tick → next, only after user sends a message
  const animateAgentThoughts = (agentThoughtsArr) => {
    setDisplayedSteps([])
    setCurrentStep(0)
    let cancelled = false
    async function runSteps() {
      for (let i = 0; i < agentThoughtsArr.length; ++i) {
        if (cancelled) break
        const { time, text } = parseThought(agentThoughtsArr[i])
        setDisplayedSteps(prev => [...prev, { time, text, status: 'loading', id: Date.now() + i }])
        await new Promise(res => setTimeout(res, 900))
        if (cancelled) break
        setDisplayedSteps(prev => prev.map((t, idx) => idx === i ? { ...t, status: 'done' } : t))
        await new Promise(res => setTimeout(res, 400))
        setCurrentStep(i + 1)
      }
    }
    runSteps()
    return () => { cancelled = true }
  }

  // On send, call backend and animate agent thoughts
  const handleSend = async (msg) => {
    if (!msg.trim()) return
    setChat(c => [...c, { id: Date.now(), sender: 'user', text: msg }])
    setInput('')
    setThinking(true)
    setAgentThoughts([])
    setError(null)
    setProducts([])
    setRecommendations([])
    setActionsTaken([])
    setIntent('')
    setSuccess(true)
    // Call mock backend
    const data = await mockAgentAPI(msg)
    setThinking(false)
    setProducts(data.products || [])
    setRecommendations(data.recommendations || [])
    setActionsTaken(data.actions_taken || [])
    setIntent(data.intent || '')
    setSuccess(data.success)
    setError(data.error)
    // Animate agent thoughts from backend
    if (Array.isArray(data.agent_thoughts)) {
      animateAgentThoughts(data.agent_thoughts)
    }
    // Add agent's final response to chat
    setChat(c => [...c, { id: Date.now() + 1, sender: 'agent', text: data.response }])
  }

  // Scroll to bottom of agent thoughts
  const scrollAgentThoughtsToBottom = () => {
    if (agentThoughtsScrollRef.current) {
      agentThoughtsScrollRef.current.scrollTop = agentThoughtsScrollRef.current.scrollHeight
    }
  }

  // Show scroll-to-bottom button if not at bottom
  useEffect(() => {
    const ref = agentThoughtsScrollRef.current
    if (!ref) return
    const handleScroll = () => {
      const atBottom = ref.scrollHeight - ref.scrollTop - ref.clientHeight < 10
      setShowScrollToBottom(!atBottom)
    }
    ref.addEventListener('scroll', handleScroll)
    // Scroll to bottom on new thoughts
    scrollAgentThoughtsToBottom()
    return () => ref.removeEventListener('scroll', handleScroll)
  }, [agentThoughts.length])

  return (
    <div className="flex flex-row w-full h-[80vh] max-w-6xl mx-auto gap-8 items-stretch">
      {/* Chat Section (left) */}
      <div className="flex flex-col flex-1 rounded-2xl shadow-2xl bg-white/70 backdrop-blur-lg overflow-hidden border border-blue-100">
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
          {/* Scroll anchor for auto-scroll */}
          <div ref={chatEndRef} />
          {/* Optionally show products, recommendations, actions, etc. */}
          {products.length > 0 && (
            <div className="mt-8">
              <div className="font-bold text-blue-700 mb-2">Products:</div>
              <ul className="list-disc ml-6 text-blue-900">
                {products.map(p => <li key={p.id}>{p.name}</li>)}
              </ul>
            </div>
          )}
          {recommendations.length > 0 && (
            <div className="mt-4">
              <div className="font-bold text-blue-700 mb-2">Recommendations:</div>
              <ul className="list-disc ml-6 text-blue-900">
                {recommendations.map((r, i) => <li key={i}>{r}</li>)}
              </ul>
            </div>
          )}
          {actionsTaken.length > 0 && (
            <div className="mt-4">
              <div className="font-bold text-blue-700 mb-2">Actions Taken:</div>
              <ul className="list-disc ml-6 text-blue-900">
                {actionsTaken.map((a, i) => <li key={i}>{a}</li>)}
              </ul>
            </div>
          )}
          {intent && (
            <div className="mt-4 text-xs text-blue-400">Intent: {intent}</div>
          )}
          {error && (
            <div className="mt-4 text-xs text-red-500">Error: {error}</div>
          )}
        </ScrollArea>
        {/* Input Area */}
        <div className="border-t bg-white/90 px-6 py-4 sticky bottom-0 z-10 shadow-inner">
          <div className="max-w-2xl mx-auto flex items-center gap-3">
            <input
              className="flex-1 rounded-xl border border-blue-300 px-4 py-2 text-base bg-white placeholder:text-blue-300 focus:outline-none focus:ring-2 focus:ring-blue-400 focus:border-blue-500 transition-all min-h-[40px] max-h-24 resize-y shadow-sm"
              type="text"
              placeholder="Type your message..."
              value={input}
              onChange={e => setInput(e.target.value)}
              style={{ fontSize: '1rem' }}
            />
            <Button
              type="button"
              onClick={() => handleSend(input)}
            >
              Send
            </Button>
          </div>
        </div>
      </div>
      {/* AI Thought Stream Panel (right, never overlaps) */}
      {showAgentPanel && displayedSteps.length > 0 && (
        <div className="hidden lg:block w-[370px] max-w-[90vw]">
          <div className="relative rounded-2xl border-2 border-blue-200/60 bg-gradient-to-br from-blue-100/80 to-white/90 backdrop-blur-2xl shadow-2xl overflow-visible p-0 h-full flex flex-col">
            <div className="flex items-center gap-2 px-6 pt-5 pb-3">
              <span className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-400 to-purple-400 flex items-center justify-center shadow-lg border-2 border-white animate-pulse">
                <svg width="22" height="22" fill="none" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" fill="#6366f1" opacity="0.15"/><path d="M8 12a4 4 0 1 1 8 0" stroke="#6366f1" strokeWidth="2" strokeLinecap="round"/><circle cx="12" cy="12" r="2" fill="#6366f1"/></svg>
              </span>
              <span className="font-bold text-blue-700 text-lg tracking-tight">AI Thought Stream</span>
              <button
                className="ml-auto text-blue-400 hover:text-blue-700 text-2xl font-bold opacity-60 hover:opacity-100 transition pointer-events-auto rounded-full px-2 py-1"
                onClick={() => setShowAgentPanel(false)}
                tabIndex={0}
                aria-label="Close AI Thought Stream"
              >×</button>
            </div>
            <div className="px-6 pb-3 pt-1 text-xs text-blue-300">These thoughts are ephemeral and will disappear automatically.</div>
            <div className="px-4 pb-6 space-y-3 max-h-[60vh] overflow-y-auto custom-scrollbar">
              {displayedSteps.map((thought, idx) => (
                <div key={thought.id} className="flex items-start gap-3 p-4 rounded-xl bg-white/80 border border-blue-100 shadow transition-all animate-fade-in">
                  <span>
                    {thought.status === 'loading'
                      ? <svg className="w-5 h-5 text-blue-400 animate-spin" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="#6366f1" strokeWidth="4" fill="none"/><path className="opacity-75" fill="#6366f1" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"/></svg>
                      : <svg className="w-5 h-5 text-green-500" viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M16.707 6.293a1 1 0 00-1.414 0L9 12.586l-2.293-2.293a1 1 0 00-1.414 1.414l3 3a1 1 0 001.414 0l7-7a1 1 0 000-1.414z" clipRule="evenodd"/></svg>
                    }
                  </span>
                  <div>
                    <div className="text-xs text-blue-400 font-mono">{thought.time}</div>
                    <div className="text-blue-900 text-base font-mono">{thought.text}</div>
                  </div>
                </div>
              ))}
            </div>
            <div className="absolute inset-0 pointer-events-none rounded-2xl ring-2 ring-blue-400/20 animate-pulse-glow" />
          </div>
        </div>
      )}
    </div>
  )
} 