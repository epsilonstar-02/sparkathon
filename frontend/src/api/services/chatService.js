// Chat Service
// This file contains all chat-related API calls

import { apiClient } from '../client.js'
import { API_ENDPOINTS } from '../config.js'

export const chatService = {
  // Get chat history for a user
  // USAGE: Load previous conversations in Chat.jsx
  // INTEGRATION POINT: Chat component - load chat history on component mount
  async getChatHistory(userId = null) {
    try {
      const params = userId ? { user_id: userId } : {}
      return await apiClient.get(API_ENDPOINTS.CHAT_HISTORY, params)
    } catch (error) {
      console.error('Failed to fetch chat history:', error)
      throw error
    }
  },

  // Send user message and get AI response
  // USAGE: Chat.jsx when user sends a message
  // INTEGRATION POINT: Chat component - handleSend function
  async sendMessage(userId, content, isUser = true) {
    try {
      const messageData = {
        user_id: userId,
        content: content,
        is_user: isUser
      }
      return await apiClient.post(API_ENDPOINTS.CHAT, messageData)
    } catch (error) {
      console.error('Failed to send message:', error)
      throw error
    }
  },

  // Send user message and simulate AI response
  // USAGE: Complete chat interaction in Chat.jsx
  // INTEGRATION POINT: Chat component - replace current handleSend logic
  async sendChatMessage(userId, userMessage) {
    try {
      // Send user message
      const userMessageResponse = await this.sendMessage(userId, userMessage, true)
      
      // TODO: Replace this with actual AI service integration
      // For now, simulate AI response based on message content
      const aiResponse = this.generateAIResponse(userMessage)
      
      // Send AI response
      const aiMessageResponse = await this.sendMessage(userId, aiResponse, false)
      
      return {
        userMessage: userMessageResponse,
        aiMessage: aiMessageResponse
      }
    } catch (error) {
      console.error('Failed to process chat message:', error)
      throw error
    }
  },

  // Simulate AI response (replace with actual AI service)
  // USAGE: Temporary AI response generation
  // INTEGRATION POINT: Replace this with your actual AI service
  generateAIResponse(userMessage) {
    const message = userMessage.toLowerCase()
    
    if (message.includes('grocery') || message.includes('shopping')) {
      return "I'd be happy to help you with your grocery shopping! What specific items are you looking for today?"
    } else if (message.includes('meal') || message.includes('recipe')) {
      return "Great! I can help you plan meals and find the ingredients you need. What type of cuisine are you interested in?"
    } else if (message.includes('budget') || message.includes('save')) {
      return "I can help you find budget-friendly options and deals. What's your target budget for this shopping trip?"
    } else if (message.includes('healthy') || message.includes('diet')) {
      return "I can suggest healthy options based on your dietary preferences. Do you have any specific dietary restrictions?"
    } else {
      return "I'm here to help with your shopping needs! Feel free to ask about products, meal planning, or finding the best deals."
    }
  },

  // Clear chat history (optional functionality)
  // USAGE: Clear conversation button in Chat.jsx
  // INTEGRATION POINT: Chat component - clear chat functionality
  async clearChatHistory(userId) {
    try {
      // Note: This would require a backend endpoint to delete chat messages
      // For now, this is a placeholder
      console.log(`Clearing chat history for user ${userId}`)
      return { status: 'success', message: 'Chat history cleared' }
    } catch (error) {
      console.error('Failed to clear chat history:', error)
      throw error
    }
  }
}