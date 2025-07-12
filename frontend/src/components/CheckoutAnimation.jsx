// src/components/CheckoutAnimation.js
import React, { useRef } from 'react';
import { Html } from '@react-three/drei';
import { motion } from 'framer-motion';

const CheckoutAnimation = ({ cartItems }) => {
  return (
    <Html center>
      <motion.div 
        className="bg-white/90 backdrop-blur-sm rounded-2xl shadow-2xl p-6 max-w-md w-full"
        initial={{ scale: 0.8, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ duration: 0.3 }}
      >
        <div className="text-center mb-6">
          <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg xmlns="http://www.w3.org/2000/svg" className="h-8 w-8 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <h2 className="text-2xl font-bold text-gray-800">Order Complete!</h2>
          <p className="text-gray-600">Thank you for your purchase</p>
        </div>
        
        <div className="border-t border-b py-4 mb-6">
          <h3 className="font-semibold mb-3">Order Summary</h3>
          <div className="space-y-2 max-h-48 overflow-y-auto">
            {cartItems.map((item, index) => (
              <div key={index} className="flex justify-between">
                <span className="text-gray-600">{item.name}</span>
                <span className="font-medium">${item.price.toFixed(2)}</span>
              </div>
            ))}
          </div>
        </div>
        
        <div className="flex justify-between font-bold text-lg mb-6">
          <span>Total:</span>
          <span>
            ${cartItems.reduce((total, item) => total + item.price, 0).toFixed(2)}
          </span>
        </div>
        
        <div className="text-center text-gray-500 text-sm">
          <p>Your items will be delivered shortly</p>
        </div>
      </motion.div>
    </Html>
  );
};

export default CheckoutAnimation;