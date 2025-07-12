// import { useState, useRef, useEffect } from 'react'
// import { Card } from '../components/Card'
// import { Avatar } from '../components/Avatar'
// import { ScrollArea } from '../components/ScrollArea'
// import { MessageInput } from '../components/MessageInput'
// import { motion, AnimatePresence } from 'framer-motion'

// export default function Chat() {
//   // Placeholder state for chat and thoughts
//   const [chat, setChat] = useState([
//     { id: 1, sender: 'user', text: 'Hi, I need help planning my groceries.' },
//     { id: 2, sender: 'agent', text: 'Of course! What meals are you planning this week?' }
//   ])
//   const [thoughts, setThoughts] = useState([
//     { id: 1, text: 'Analyzing user intent...' },
//     { id: 2, text: 'Suggesting meal plan options.' }
//   ])
//   const [input, setInput] = useState('')
//   const [thinking, setThinking] = useState(false)

//   // Simulate backend response
//   const handleSend = (msg) => {
//     if (!msg.trim()) return
//     setChat(c => [...c, { id: Date.now(), sender: 'user', text: msg }])
//     setInput('')
//     setThinking(true)
//     setTimeout(() => {
//       setThoughts(t => [...t, { id: Date.now(), text: 'Thinking about best options...' }])
//       setTimeout(() => {
//         setChat(c => [...c, { id: Date.now(), sender: 'agent', text: 'Here are some personalized suggestions for you!' }])
//         setThinking(false)
//       }, 1200)
//     }, 1000)
//   }

//   return (
//     <div className="flex flex-col h-[80vh] rounded-2xl shadow-2xl bg-white/70 backdrop-blur-lg overflow-hidden border border-blue-100">
//       <div className="flex flex-1 min-h-0">
//         {/* Chat Area */}
//         <ScrollArea className="flex-1 p-8 space-y-5 border-r min-w-0 bg-gradient-to-br from-blue-50/60 to-white/80">
//           <AnimatePresence>
//             {chat.map(msg => (
//               <motion.div
//                 key={msg.id}
//                 initial={{ opacity: 0, y: 30 }}
//                 animate={{ opacity: 1, y: 0 }}
//                 exit={{ opacity: 0, y: 30 }}
//                 transition={{ duration: 0.35, type: 'spring', bounce: 0.3 }}
//               >
//                 <Card className={`flex items-start gap-4 p-5 ${msg.sender === 'user' ? 'bg-blue-50/80 ml-auto' : 'bg-yellow-50/80 mr-auto'} border-0 shadow-md`}> 
//                   <Avatar sender={msg.sender} />
//                   <div>
//                     <div className="font-semibold text-sm text-blue-700 mb-1">{msg.sender === 'user' ? 'You' : 'Walmart AI'}</div>
//                     <div className="text-gray-900 text-base leading-relaxed">{msg.text}</div>
//                   </div>
//                 </Card>
//               </motion.div>
//             ))}
//           </AnimatePresence>
//         </ScrollArea>
//         {/* Thought Stream */}
//         <ScrollArea className="w-[30%] min-w-[220px] max-w-xs p-6 space-y-4 bg-gradient-to-br from-blue-100/80 to-white/80">
//           <div className="font-bold text-blue-700 mb-2 text-lg tracking-tight">Agent Thought Stream</div>
//           <AnimatePresence>
//             {thoughts.map(thought => (
//               <motion.div
//                 key={thought.id}
//                 initial={{ opacity: 0, x: 30 }}
//                 animate={{ opacity: 1, x: 0 }}
//                 exit={{ opacity: 0, x: 30 }}
//                 transition={{ duration: 0.3 }}
//               >
//                 <Card className="p-4 bg-white/90 shadow-sm border-l-4 border-blue-400">
//                   <div className="text-gray-700 text-sm">{thought.text}</div>
//                 </Card>
//               </motion.div>
//             ))}
//             {thinking && (
//               <motion.div
//                 key="thinking"
//                 initial={{ opacity: 0 }}
//                 animate={{ opacity: 1 }}
//                 exit={{ opacity: 0 }}
//                 transition={{ duration: 0.4, repeat: Infinity, repeatType: 'reverse' }}
//               >
//                 <Card className="p-4 bg-blue-50/80 border-l-4 border-blue-400 animate-pulse">
//                   <div className="text-blue-600 font-medium flex items-center gap-2">
//                     <span className="w-2 h-2 rounded-full bg-blue-400 animate-pulse"></span>
//                     Thinking...
//                   </div>
//                 </Card>
//               </motion.div>
//             )}
//           </AnimatePresence>
//         </ScrollArea>
//       </div>
//       {/* Input Area */}
//       <div className="border-t p-6 bg-gradient-to-br from-blue-50/80 to-white/80 shadow-inner">
//         <div className="max-w-2xl mx-auto">
//           <MessageInput
//             value={input}
//             onChange={e => setInput(e.target.value)}
//             onSend={() => handleSend(input)}
//           />
//         </div>
//       </div>
//     </div>
//   )
// } 

import { useState, useRef, useEffect, useLayoutEffect } from 'react';
import axios from 'axios';
import { Card } from '../components/Card';
import { Avatar } from '../components/Avatar';
import { ScrollArea } from '../components/ScrollArea';
import { MessageInput } from '../components/MessageInput';
import { motion, AnimatePresence } from 'framer-motion';
import { talkService } from '../api/services/talkService';
import { FaMicrophone, FaStop, FaVolumeUp } from 'react-icons/fa';

export default function Chat() {
  const [chat, setChat] = useState([
    { id: 1, sender: 'user', text: 'Hi, I need help planning my groceries.' },
    { id: 2, sender: 'agent', text: 'Of course! What meals are you planning this week?' }
  ]);
  const [thoughts, setThoughts] = useState([
    { id: 1, text: 'Analyzing user intent...' },
    { id: 2, text: 'Suggesting meal plan options.' }
  ]);
  const [input, setInput] = useState('');
  const [thinking, setThinking] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const audioRef = useRef(null);
  const chatBottomRef = useRef(null);
  const thoughtsBottomRef = useRef(null);

  // Scroll to bottom of chat when messages change
  useLayoutEffect(() => {
    if (chatBottomRef.current) {
      chatBottomRef.current.scrollIntoView({ behavior: 'smooth', block: 'end' });
    }
  }, [chat]);

  // Scroll to bottom of thoughts when they change
  useLayoutEffect(() => {
    if (thoughtsBottomRef.current) {
      thoughtsBottomRef.current.scrollIntoView({ behavior: 'smooth', block: 'end' });
    }
  }, [thoughts]);

  // New state for typing animations
  const typingIntervals = useRef({});
  const [activeTyping, setActiveTyping] = useState({});
  const [thinkingId, setThinkingId] = useState(null);

  // Cleanup resources
  useEffect(() => {
    return () => {
      // Cleanup audio
      if (audioRef.current) {
        audioRef.current.pause();
        URL.revokeObjectURL(audioRef.current.src);
      }
      
      // Cleanup typing intervals
      Object.values(typingIntervals.current).forEach(interval => {
        clearInterval(interval);
      });
    };
  }, []);

  // Start typing animation for a message
  const startTypingAnimation = (messageId, fullText, speed = 30) => {
    // Clear any existing interval for this message
    if (typingIntervals.current[messageId]) {
      clearInterval(typingIntervals.current[messageId]);
    }
    
    // Start new animation
    let charIndex = 0;
    typingIntervals.current[messageId] = setInterval(() => {
      setChat(prevChat => 
        prevChat.map(msg => {
          if (msg.id === messageId) {
            const newText = fullText.substring(0, charIndex + 1);
            charIndex++;
            
            // Return updated message
            return { 
              ...msg, 
              text: newText,
              isTyping: charIndex < fullText.length
            };
          }
          return msg;
        })
      );
      
      // Clear interval when animation completes
      if (charIndex >= fullText.length) {
        clearInterval(typingIntervals.current[messageId]);
        delete typingIntervals.current[messageId];
        setActiveTyping(prev => ({ ...prev, [messageId]: false }));
      }
    }, speed);
  };

  // Play audio for a message after typing completes
  const playAudioAfterTyping = (audioUrl, messageId) => {
    // Check every 100ms if typing is complete
    const checkInterval = setInterval(() => {
      if (!activeTyping[messageId]) {
        clearInterval(checkInterval);
        playAgentAudio(audioUrl);
      }
    }, 100);
  };

  // Play agent voice response
  const playAgentAudio = (audioUrl) => {
    if (audioRef.current) {
      audioRef.current.pause();
      URL.revokeObjectURL(audioRef.current.src);
    }
    
    const audio = new Audio(audioUrl);
    audioRef.current = audio;
    
    audio.onended = () => {
      URL.revokeObjectURL(audioUrl);
      setIsPlaying(false);
    };
    
    audio.onplay = () => setIsPlaying(true);
    audio.play();
  };

  // Handle text message submission
  const handleSend = async (msg) => {
    if (!msg.trim()) return;
    
    // Add user message to chat
    const userMessageId = Date.now();
    const userMessage = { 
      id: userMessageId, 
      sender: 'user', 
      text: msg 
    };
    setChat(c => [...c, userMessage]);
    setInput('');
    setThinking(true);
    
    // Add thinking indicator
    const newThinkingId = Date.now();
    setThinkingId(newThinkingId);
    setThoughts(t => [...t, { id: newThinkingId, text: 'Processing your request...' }]);

    try {
      // Call agent endpoint directly
      const response = await axios.post('http://localhost:8001/chat', {
        message: msg,
        user_id: "cmcqhdhix00jauwtg9jza2xo7"
      });

      const agentText = response.data?.response || "I couldn't process that request.";
      
      // Remove thinking indicator
      setThoughts(t => t.filter(thought => thought.id !== newThinkingId));
      setThinkingId(null);
      
      // Add agent response with typing animation
      const agentMessageId = Date.now();
      setActiveTyping(prev => ({ ...prev, [agentMessageId]: true }));
      setChat(c => [...c, { 
        id: agentMessageId, 
        sender: 'agent', 
        text: '',
        isTyping: true
      }]);
      
      // Start typing animation
      startTypingAnimation(agentMessageId, agentText);
      
    } catch (error) {
      console.error('Failed to get agent response:', error);
      setThoughts(t => t.filter(thought => thought.id !== newThinkingId));
      setThinkingId(null);
      setChat(c => [...c, { 
        id: Date.now(), 
        sender: 'agent', 
        text: 'Sorry, I encountered an error processing your request.',
        isError: true
      }]);
    } finally {
      setThinking(false);
    }
  };

  // Start voice recording
  const startRecording = async () => {
    if (isPlaying) stopPlayback();
    
    try {
      setIsRecording(true);
      audioChunksRef.current = [];
      
      // Add temporary voice message to chat
      const tempMessageId = `temp-voice-${Date.now()}`;
      setChat(c => [...c, { 
        id: tempMessageId, 
        sender: 'user', 
        text: 'Recording...',
        isTemp: true
      }]);
      
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) audioChunksRef.current.push(event.data);
      };

      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });

        try {
          // Generate agentMessageId here, outside setChat
          const agentMessageId = `agent-${Date.now()}`;  // Moved outside setChat
          // Add thinking indicator
          const voiceThinkingId = Date.now();
          setThinking(true);
          setThinkingId(voiceThinkingId);
          setThoughts(t => [...t, { id: voiceThinkingId, text: 'Processing voice input...' }]);
          
          // Send audio to backend for processing
          const response = await talkService.sendAudio(audioBlob, "cmcqhdhix00jauwtg9jza2xo7");
          
          // Extract data from response
          const userTranscription = response.user_transcription;
          const agentText = response.agent_text;
          const audioBase64 = response.audio;
          const contentType = response.content_type;
          
          // Create audio Blob from base64
          const binaryString = atob(audioBase64);
          const bytes = new Uint8Array(binaryString.length);
          for (let i = 0; i < binaryString.length; i++) {
            bytes[i] = binaryString.charCodeAt(i);
          }
          const agentAudioBlob = new Blob([bytes], { type: contentType });
          const audioUrl = URL.createObjectURL(agentAudioBlob);
          
          // Remove thinking indicator
          setThoughts(t => t.filter(thought => thought.id !== voiceThinkingId));
          setThinkingId(null);
          
          // Update chat state
          setChat(c => {
            // 1. Remove temporary recording message
            const filtered = c.filter(msg => !msg.isTemp);
            
            // 2. Add user's actual transcription
            const withUserMessage = [
              ...filtered, 
              {
                id: `user-${Date.now()}`,
                sender: 'user',
                text: userTranscription
              }
            ];
            
            // 3. Add agent response with typing animation
            // const agentMessageId = `agent-${Date.now()}`;
            return [
                ...withUserMessage,
                {
                    id: agentMessageId,  // Use the pre-defined id
                    sender: 'agent',
                    text: '',
                    isTyping: true,
                    audioUrl: audioUrl
                }
            ];
          });

          // Start typing animation and schedule audio playback
          // Using timeout to ensure state is updated before starting animation
          setTimeout(() => {
            startTypingAnimation(agentMessageId, agentText);
            playAudioAfterTyping(audioUrl, agentMessageId);
          }, 0);
          
        } catch (err) {
          console.error('Voice processing failed:', err);
          setThoughts(t => t.filter(thought => thought.id !== voiceThinkingId));
          setThinkingId(null);
          setChat(c => 
            c.filter(msg => !msg.isTemp).concat({
              id: Date.now(),
              sender: 'user',
              text: `Voice input failed: ${err.message}`,
              isError: true
            })
          );
        } finally {
          setThinking(false);
        }
      };

      mediaRecorder.start();
    } catch (err) {
      console.error('Recording failed:', err);
      setIsRecording(false);
      setChat(c => [...c, { 
        id: Date.now(), 
        sender: 'user', 
        text: 'Microphone access denied',
        isError: true
      }]);
    }
  };

  // Stop voice recording
  const stopRecording = () => {
    setIsRecording(false);
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
    }
  };

  // Stop audio playback
  const stopPlayback = () => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
      setIsPlaying(false);
    }
  };

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
                <Card className={`flex items-start gap-4 p-5 ${msg.sender === 'user' 
                  ? 'bg-blue-50/80 ml-auto' 
                  : 'bg-yellow-50/80 mr-auto'
                } border-0 shadow-md`}> 
                  <Avatar sender={msg.sender} />
                  <div className="min-w-0">
                    <div className="font-semibold text-sm text-blue-700 mb-1">
                      {msg.sender === 'user' ? 'You' : 'Walmart AI'}
                    </div>
                    
                    {/* Message text with typing animation */}
                    <div className={`text-gray-900 text-base leading-relaxed ${
                      msg.isError ? 'text-red-600' : ''
                    }`}>
                      {msg.text}
                      {msg.isTyping && (
                        <span className="ml-1 inline-block w-2 h-4 bg-blue-500 animate-pulse"></span>
                      )}
                    </div>
                    
                    {/* Audio controls for agent response */}
                    {msg.sender === 'agent' && msg.audioUrl && !msg.isTyping && (
                      <div className="mt-3 flex items-center gap-3">
                        <button 
                          onClick={() => 
                            isPlaying ? stopPlayback() : playAgentAudio(msg.audioUrl)
                          }
                          className={`px-3 py-1 rounded-md text-sm flex items-center gap-2 ${
                            isPlaying 
                              ? 'bg-red-100 text-red-600' 
                              : 'bg-blue-100 text-blue-600'
                          }`}
                        >
                          {isPlaying ? <FaStop /> : <FaVolumeUp />}
                          {isPlaying ? 'Stop Playback' : 'Play Audio Again'}
                        </button>
                        <span className="text-xs text-gray-500">
                          Agent voice response
                        </span>
                      </div>
                    )}
                  </div>
                </Card>
              </motion.div>
            ))}
          </AnimatePresence>
          <div ref={chatBottomRef} />
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
            {thinking && !Object.values(activeTyping).some(v => v) && (
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
          <div ref={thoughtsBottomRef} />
        </ScrollArea>
      </div>
      
      {/* Input Area with Voice Controls */}
      <div className="border-t p-4 bg-gradient-to-br from-blue-50/80 to-white/80 shadow-inner">
        <div className="max-w-2xl mx-auto flex items-center gap-2">
          {/* Voice Recording Button */}
          <button
            onClick={isRecording ? stopRecording : startRecording}
            className={`p-3 rounded-full ${
              isRecording 
                ? 'bg-red-500 animate-pulse' 
                : 'bg-blue-500 hover:bg-blue-600'
            } text-white transition-colors`}
            aria-label={isRecording ? "Stop recording" : "Start voice recording"}
            disabled={thinking}
          >
            {isRecording ? <FaStop /> : <FaMicrophone />}
          </button>
          
          {/* Text Input */}
          <div className="flex-1">
            <MessageInput
              value={input}
              onChange={e => setInput(e.target.value)}
              onSend={() => handleSend(input)}
              disabled={thinking}
            />
          </div>
        </div>
      </div>
    </div>
  )
}