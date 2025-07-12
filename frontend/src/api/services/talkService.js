// services/talkService.js

import { apiClient } from '../client.js'
import { API_ENDPOINTS } from '../config.js'

export const talkService = {
  async sendAudio(audioBlob, userId) {
    try {
      const formData = new FormData()
      formData.append('audio', audioBlob, 'audio.webm')
      formData.append('userId', userId)

      // Log form data keys
      for (let [key, value] of formData.entries()) {
        console.log(key, value instanceof Blob ? `Blob (${value.type})` : value);
      }

      const response = await apiClient.post(API_ENDPOINTS.TALK, 
         formData
      )

      // if (!response.ok) {
      //   throw new Error(`Server error: ${response.status}`)
      // }

      // // Check if it's an audio blob
      // if (response instanceof Blob) {
       // Check if we got a JSON response with audio data
      // Your client returns the parsed JSON directly for JSON responses
      if (response && typeof response === 'object') {
        return {
          user_transcription: response.user_transcription,
          agent_text: response.agent_text,
          audio: response.audio,
          content_type: response.content_type
        }
      }
      throw new Error('Invalid response format from server')
      // }

      // const contentType = response.headers.get('content-type')
      // if (contentType.includes('audio')) {
        // // Return binary audio blob
        // return await response.blob()
      // } else {
      //   // Assume JSON fallback
      //   return await response.json()
      // }
    } catch (error) {
      console.error('Failed to send audio:', error)
      throw new Error('Voice processing failed. Please try again.')
    }
  }
}
