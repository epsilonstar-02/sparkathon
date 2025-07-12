import { useFrame } from '@react-three/fiber';
import React, { useState, useEffect, useRef, useMemo, useCallback } from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls, Text, Html } from '@react-three/drei';
import * as THREE from 'three';
import { motion } from 'framer-motion';
import { useSpring, animated } from '@react-spring/three';
import axios from 'axios';
import { FiChevronLeft, FiChevronRight } from 'react-icons/fi';
// API base URL
const API_BASE_URL = 'http://localhost:8000';
const USER_ID = 'cmcqhdhix00jauwtg9jza2xo7';

// Aisle configuration with 3D positions
const aisleConfig = {
  'Bakery': { color: '#fbbf24', icon: '🥖', position: [-6, 0, 0] },
  'Dairy': { color: '#60a5fa', icon: '🥛', position: [-4, 0, -5] },
  'Meat': { color: '#f87171', icon: '🥩', position: [0, 0, -6] },
  'Produce': { color: '#34d399', icon: '🥦', position: [4, 0, -5] },
  'Snacks': { color: '#f472b6', icon: '🍿', position: [-4, 0, 5] },
  'Drinks': { color: '#38bdf8', icon: '🥤', position: [0, 0, 6] },
  'Frozen': { color: '#93c5fd', icon: '❄️', position: [4, 0, 5] },
  'Household': { color: '#c7d2fe', icon: '🏠', position: [6, 0, 0] },
  'Checkout': { color: '#22c55e', icon: '💰', position: [0, 0, -8] },
};

// Helper function to truncate text
const truncateText = (text, maxLength = 20) => {
  if (!text) return '';
  if (text.length <= maxLength) return text;
  return text.substring(0, maxLength) + '...';
};

// Reusable 3D Box Component
const Box = ({ args, position, color, opacity = 1, ...props }) => (
  <mesh position={position} {...props}>
    <boxGeometry args={args} />
    <meshStandardMaterial color={color} opacity={opacity} transparent={opacity < 1} />
  </mesh>
);

// 3D Store Layout Component
const StoreLayout = ({ 
  aisleConfig,
  products,
  searchTerm,
  selectedAisle,
  selectedProduct,
  addToCart,
  navigateTo,
  onProductHover
}) => {
  const filteredProducts = useMemo(() => {
    if (!searchTerm) return products;
    return products.filter(p => 
      p?.name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (p?.category?.toLowerCase().includes(searchTerm.toLowerCase()))
    );
  }, [products, searchTerm]);

  return (
    <group>
      {/* Store Floor */}
      <Box
        args={[20, 0.1, 20]}
        position={[0, -0.05, 0]}
        color="#f8fafc"
        receiveShadow
      />

      {/* Store Walls */}
      <Box
        args={[20, 5, 0.2]}
        position={[0, 2.5, -10]}
        color="#e2e8f0"
        receiveShadow
      />
      
      <Box
        args={[0.2, 5, 20]}
        position={[-10, 2.5, 0]}
        color="#e2e8f0"
        receiveShadow
      />
      
      <Box
        args={[0.2, 5, 20]}
        position={[10, 2.5, 0]}
        color="#e2e8f0"
        receiveShadow
      />

      {/* Entry Door */}
      <Box
        args={[4, 3, 0.1]}
        position={[0, 1.5, 10]}
        color="#3b82f6"
      />
      
      <Text
        position={[0, 3, 10.1]}
        color="#1e40af"
        fontSize={0.5}
        anchorX="center"
        anchorY="middle"
      >
        ENTRANCE
      </Text>

      {/* Exit Door */}
      <Box
        args={[4, 3, 0.1]}
        position={[0, 1.5, -10]}
        color="#ef4444"
      />
      
      <Text
        position={[0, 3, -10.1]}
        color="#b91c1c"
        fontSize={0.5}
        anchorX="center"
        anchorY="middle"
      >
        EXIT
      </Text>

      {/* Aisles */}
      {Object.entries(aisleConfig).map(([name, config]) => {
        if (!config) return null;
        
        // Fix: Properly check if aisle is selected
        const isSelected = selectedAisle === name;
        const aisleProducts = filteredProducts.filter(p => 
          p?.category === name
        );
        
        return (
          <group key={name} position={config.position || [0, 0, 0]}>
            {/* Aisle Base */}
            <Box
              args={[3, 1, 3]}
              position={[0, 0.5, 0]}
              color={config.color}
              opacity={0.9}
              castShadow
              receiveShadow
            />
            
            {/* Aisle Label */}
            <Text
              position={[0, 2, 0]}
              color="#000"
              fontSize={0.5}
              maxWidth={3}
              textAlign="center"
              anchorX="center"
              anchorY="middle"
              outlineWidth={0.05}
              outlineColor="#ffffff"
            >
              {config.icon} {name}
            </Text>
            
            {/* Products in this aisle */}
            {aisleProducts.map((product, index) => {
              const row = Math.floor(index / 4);
              const col = index % 4;
              const position = [
                (col - 1.5) * 0.7,
                0.7,
                (row - 1) * 0.7
              ];
              
              return (
                <Product
                  key={product.id}
                  product={product}
                  position={position}
                  isHighlighted={isSelected || selectedProduct?.id === product.id}
                  addToCart={addToCart}
                  navigateTo={navigateTo}
                  onHover={onProductHover}
                />
              );
            })}
          </group>
        );
      })}
      
      {/* Checkout Counter */}
      <group position={aisleConfig['Checkout'].position}>
        <Box
          args={[8, 1, 2]}
          position={[0, 0.5, 0]}
          color="#22c55e"
          castShadow
          receiveShadow
        />
        
        <Text
          position={[0, 2, 0]}
          color="#166534"
          fontSize={0.6}
          maxWidth={8}
          textAlign="center"
          anchorX="center"
          anchorY="middle"
          outlineWidth={0.05}
          outlineColor="#ffffff"
        >
          🛒 CHECKOUT
        </Text>
      </group>
    </group>
  );
};

// 3D Product Component
const Product = ({ product, position, isHighlighted, addToCart, navigateTo, onHover }) => {
  const [hovered, setHovered] = useState(false);
  
  // Spring animation for hover effect
  const { scale } = useSpring({
    scale: hovered ? 1.1 : 1,
    config: { tension: 300, friction: 10 }
  });


  // Fix: Use actual highlighting state
  const shouldHighlight = isHighlighted || (selectedProduct && selectedProduct.id === product.id);
   // Spring animation for highlight effect
  const { emissiveIntensity, color } = useSpring({
    emissiveIntensity: shouldHighlight ? 0.8 : 0,
    color: shouldHighlight ? '#ff0000' : '#64748b',
    config: { tension: 300, friction: 10 }
  });
  return (
    <animated.group 
      position={position}
      scale={scale}
      onClick={(e) => {
        e.stopPropagation();
        addToCart(product);
        navigateTo(position);
      }}
      onPointerOver={(e) => {
        e.stopPropagation();
        setHovered(true);
        onHover(product);
      }}
      onPointerOut={(e) => {
        setHovered(false);
        onHover(null);
      }}
    >
      <mesh castShadow receiveShadow>
        <boxGeometry args={[0.5, 0.5, 0.5]} />
        <animated.meshStandardMaterial 
          color={color}
          emissive={color}
          emissiveIntensity={emissiveIntensity}
        />
      </mesh>
      
      <Text
        position={[0, 0.8, 0]}
        color="#334155"
        fontSize={0.15}
        maxWidth={1}
        textAlign="center"
        anchorX="center"
        anchorY="top"
      >
        {truncateText(product?.name, 12)}
      </Text>
      
      <Text
        position={[0, 0.6, 0]}
        color="#4b5563"
        fontSize={0.12}
        anchorX="center"
        anchorY="top"
      >
        ${product?.price?.toFixed(2)}
      </Text>
      
      {/* Tooltip */}
      {hovered && (
        <Html position={[0, 1.5, 0]}>
          <div className="bg-white p-2 rounded shadow-lg text-sm max-w-xs">
            <div className="font-semibold">{product?.name}</div>
            <div>${product?.price?.toFixed(2)}</div>
            <div className="text-gray-600 text-xs">{product?.category}</div>
          </div>
        </Html>
      )}
    </animated.group>
  );
};

// Shopping Cart Icon Component
const ShoppingCartIcon = ({ count, onClick }) => (
  <div className="relative cursor-pointer" onClick={onClick}>
    <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6 text-gray-700" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 11-4 0 2 2 0 014 0z" />
    </svg>
    {count > 0 && (
      <span className="absolute -top-2 -right-2 bg-red-500 text-white text-xs rounded-full w-5 h-5 flex items-center justify-center">
        {count}
      </span>
    )}
  </div>
);

// Shopping List Panel Component
const ShoppingListPanel = ({
  cartItems,
  handleCheckout,
  isEntered,
  handleEnterStore,
  shoppingList,
  onSelectCategory,
  toggleCart,
  selectedProduct,
  isExpanded 
}) => {
  return (
    <div className="w-80 h-full bg-white shadow-lg flex flex-col">
      <div className="p-4 border-b flex justify-between items-center">
        <h2 className="text-xl font-bold text-gray-800">Shopping List</h2>
        <button onClick={toggleCart} className="p-2 text-gray-500 hover:text-gray-700">
          <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
            <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
          </svg>
        </button>
      </div>
      
      <div className="overflow-y-auto flex-1 p-4 space-y-4">
        {!isEntered ? (
          <div className="text-center py-12">
            <div className="text-6xl mb-4">🛒</div>
            <h3 className="text-xl font-semibold mb-2">Welcome to our 3D Store!</h3>
            <p className="text-gray-600 mb-6">Enter the store to start shopping</p>
            <button
              onClick={handleEnterStore}
              className="px-6 py-3 bg-blue-600 text-white rounded-full font-medium hover:bg-blue-700 transition"
            >
              Enter Store
            </button>
          </div>
        ) : (
          <>
            {/* Shopping List */}
             <div className="mb-6">
              <h3 className="text-lg font-semibold mb-3">Your Shopping List</h3>
              <div className="space-y-3">
                {shoppingList.map((item) => (
                  <div 
                    key={item.id} 
                    className={`flex items-center p-3 bg-white rounded-lg shadow cursor-pointer hover:bg-gray-50 transition ${
                      selectedProduct?.id === item.product?.id ? 'ring-2 ring-blue-500' : ''
                    }`}
                    onClick={() => onSelectCategory(item.product?.category)}
                  >
                    {item.product?.thumbnailUrl ? (
                      <img 
                        src={item.product.thumbnailUrl} 
                        alt={item.product.name}
                        className={`${isExpanded ? 'w-20 h-20' : 'w-16 h-16'} object-cover rounded-xl mr-3`}
                      />
                    ) : (
                      <div className={`bg-gray-200 border-2 border-dashed rounded-xl ${isExpanded ? 'w-20 h-20' : 'w-16 h-16'} mr-3`} />
                    )}
                    <div className="flex-1 min-w-0">
                      <h4 className="font-medium truncate">{truncateText(item.product?.name || 'Unknown Product', isExpanded ? 30 : 20)}</h4>
                      <div className="flex flex-wrap items-center mt-1">
                        <span className="text-sm text-gray-500 mr-2">Qty: {item.quantity}</span>
                        {isExpanded && (
                          <span className="text-sm text-gray-500 mr-2">
                            Price: ${item.product?.price?.toFixed(2)}
                          </span>
                        )}
                        <span className="text-sm font-semibold">
                          ${(item.quantity * item.product?.price)?.toFixed(2)}
                        </span>
                      </div>
                      {isExpanded && item.product?.description && (
                        <p className="text-xs text-gray-600 mt-1 truncate">
                          {item.product.description}
                        </p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
            
            {/* Cart Items */}
            <div className="mb-6">
              <h3 className="text-lg font-semibold mb-3">Your Cart</h3>
              {cartItems.length === 0 ? (
                <div className="text-center py-6">
                  <div className="text-5xl mb-3">🛒</div>
                  <p className="text-gray-600">Your cart is empty</p>
                </div>
              ) : (
               <div className="space-y-3">
                  {cartItems.map((item) => (
                    <div key={item.id} className="flex items-center p-3 bg-white rounded-lg shadow">
                      {item.thumbnailUrl ? (
                        <img 
                          src={item.thumbnailUrl} 
                          alt={item.name}
                          className={`${isExpanded ? 'w-20 h-20' : 'w-16 h-16'} object-cover rounded-xl mr-3`}
                        />
                      ) : (
                        <div className={`bg-gray-200 border-2 border-dashed rounded-xl ${isExpanded ? 'w-20 h-20' : 'w-16 h-16'} mr-3`} />
                      )}
                      <div className="flex-1 min-w-0">
                        <h4 className="font-medium truncate">{truncateText(item.name, isExpanded ? 30 : 20)}</h4>
                        <div className="flex flex-wrap items-center mt-1">
                          <span className="text-sm text-gray-500 mr-2">Qty: {item.quantity}</span>
                          {isExpanded && (
                            <span className="text-sm text-gray-500 mr-2">
                              Unit: ${item.price?.toFixed(2)}
                            </span>
                          )}
                          <span className="text-sm font-semibold">${(item.quantity * item.price)?.toFixed(2)}</span>
                        </div>
                        {isExpanded && item.description && (
                          <p className="text-xs text-gray-600 mt-1 truncate">
                            {item.description}
                          </p>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
            
            {cartItems.length > 0 && (
              <div className="border-t pt-4">
                <div className="flex justify-between font-semibold text-lg mb-4">
                  <span>Total:</span>
                  <span>
                    ${cartItems.reduce((total, item) => total + (item.price * item.quantity), 0)?.toFixed(2)}
                  </span>
                </div>
                <button
                  onClick={handleCheckout}
                  className="w-full py-3 bg-green-600 text-white rounded-lg font-medium hover:bg-green-700 transition flex items-center justify-center"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 mr-2" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                  </svg>
                  Checkout
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
};

// Minimap Component
const Minimap = ({ aisleConfig, avatarPosition, selectedAisle, toggleMinimap }) => {
  return (
    <div className="absolute bottom-4 right-4 bg-white/90 backdrop-blur-sm p-4 rounded-xl shadow-lg z-10">
      <div className="flex justify-between items-center mb-2">
        <h3 className="font-semibold flex items-center">
          <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M9 20l-5.447-2.724A1 1 0 013 16.382V7.618a1 1 0 011.447-.894L9 9m0 11l6-3m-6 3V9m6 10l4.553 2.276A1 1 0 0021 18.382V5.618a1 1 0 00-.553-.894L15 3m0 16V3m0 0L9 9"
            />
          </svg>
          Store Map
        </h3>
        <button onClick={toggleMinimap} className="p-1 text-gray-500 hover:text-gray-700">
          <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
            <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
          </svg>
        </button>
      </div>
      
      <div className="relative w-48 h-48 bg-gray-100 rounded-lg border border-gray-300">
        {/* Store outline */}
        <div className="absolute inset-4 border border-gray-400 rounded"></div>
        
        {/* Aisles */}
        {Object.entries(aisleConfig).map(([name, config]) => {
          const x = 50 + (config.position[0] / 20) * 40;
          const y = 50 + (config.position[2] / 20) * 40;
          const isSelected = selectedAisle === name;
          
          return (
            <div 
              key={name}
              className={`absolute w-6 h-6 rounded-full flex items-center justify-center text-xs ${
                isSelected ? 'ring-2 ring-offset-1 ring-blue-500' : ''
              }`}
              style={{
                left: `${x}%`,
                top: `${y}%`,
                backgroundColor: config.color,
                transform: 'translate(-50%, -50%)'
              }}
              title={name}
            >
              {config.icon}
            </div>
          );
        })}
        
        {/* Avatar position */}
        <div 
          className="absolute w-3 h-3 bg-blue-500 rounded-full border-2 border-white"
          style={{
            left: `${50 + (avatarPosition[0] / 20) * 40}%`,
            top: `${50 + (avatarPosition[2] / 20) * 40}%`,
            transform: 'translate(-50%, -50%)'
          }}
        />
        
        {/* Entry point */}
        <div 
          className="absolute w-4 h-4 bg-blue-400 rounded-full"
          style={{
            left: '50%',
            top: '90%',
            transform: 'translate(-50%, -50%)'
          }}
        />
      </div>
    </div>
  );
};

// Checkout Animation Component
const CheckoutAnimation = ({ cartItems, onComplete }) => {
  const [step, setStep] = useState(0);
  
  useEffect(() => {
    const timer = setTimeout(() => {
      if (step < 2) {
        setStep(step + 1);
      } else {
        setTimeout(() => {
          onComplete();
        }, 1000);
      }
    }, 2000);
    
    return () => clearTimeout(timer);
  }, [step, onComplete]);
  
  // Play sound effect
  useEffect(() => {
    if (step === 2) {
      const audio = new Audio('https://assets.mixkit.co/sfx/preview/mixkit-cash-register-open-2574.mp3');
      audio.play().catch(e => console.log("Audio play failed:", e));
    }
  }, [step]);
  
  return (
    <Html center>
      <motion.div 
        className="bg-white/90 backdrop-blur-sm rounded-2xl shadow-2xl p-6 max-w-md w-full"
        initial={{ scale: 0.8, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ duration: 0.3 }}
      >
        {step === 0 && (
          <div className="text-center">
            <div className="w-16 h-16 bg-yellow-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg xmlns="http://www.w3.org/2000/svg" className="h-8 w-8 text-yellow-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            </div>
            <h2 className="text-2xl font-bold text-gray-800">Processing Order</h2>
            <p className="text-gray-600 mt-2">Your items are being scanned</p>
          </div>
        )}
        
        {step === 1 && (
          <div className="text-center">
            <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg xmlns="http://www.w3.org/2000/svg" className="h-8 w-8 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
            </div>
            <h2 className="text-2xl font-bold text-gray-800">Processing Payment</h2>
            <p className="text-gray-600 mt-2">Your payment is being verified</p>
          </div>
        )}
        
        {step === 2 && (
          <div className="text-center">
            <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg xmlns="http://www.w3.org/2000/svg" className="h-8 w-8 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            </div>
            <h2 className="text-2xl font-bold text-gray-800">Order Complete!</h2>
            <p className="text-gray-600 mt-2">Thank you for your purchase</p>
            
            <div className="mt-6 border-t pt-4">
              <h3 className="font-semibold mb-3">Order Summary</h3>
              <div className="max-h-32 overflow-y-auto">
                {cartItems.map((item, index) => (
                  <div key={index} className="flex justify-between py-1">
                    <span className="text-gray-600">{truncateText(item.name, 20)}</span>
                    <span className="font-medium">${(item.price * item.quantity)?.toFixed(2)}</span>
                  </div>
                ))}
              </div>
              <div className="flex justify-between font-bold text-lg mt-3 pt-2 border-t">
                <span>Total:</span>
                <span>
                  ${cartItems.reduce((total, item) => total + (item.price * item.quantity), 0)?.toFixed(2)}
                </span>
              </div>
            </div>
          </div>
        )}
      </motion.div>
    </Html>
  );
};

// Avatar Navigation Component
const Avatars = ({ position, path, onPathComplete }) => {
  const ref = useRef();
  const [currentIndex, setCurrentIndex] = useState(0);
  
  useEffect(() => {
    if (path && path.length > 0) {
      const interval = setInterval(() => {
        if (currentIndex < path.length - 1) {
          setCurrentIndex(currentIndex + 1);
        } else {
          clearInterval(interval);
          if (onPathComplete) onPathComplete();
        }
      }, 300);
      
      return () => clearInterval(interval);
    }
  }, [path, currentIndex, onPathComplete]);
  
  useFrame(() => {
    if (ref.current && path && path.length > 0 && currentIndex < path.length) {
      ref.current.position.lerp(
        new THREE.Vector3(...path[currentIndex]),
        0.2
      );
    } else if (ref.current) {
      ref.current.position.lerp(
        new THREE.Vector3(...position),
        0.1
      );
    }
  });
  
  return (
    <group ref={ref} position={position}>
      <mesh>
        <cylinderGeometry args={[0.3, 0.3, 1, 16]} />
        <meshStandardMaterial color="#3b82f6" />
      </mesh>
      <mesh position={[0, 0.7, 0]}>
        <sphereGeometry args={[0.4, 16, 16]} />
        <meshStandardMaterial color="#fbbf24" />
      </mesh>
    </group>
  );
};

// Main 3D Store Component
export default function Map3D() {
  const [products, setProducts] = useState([]);
  const [cartItems, setCartItems] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedAisle, setSelectedAisle] = useState(null);
  const [selectedProduct, setSelectedProduct] = useState(null);
  const [avatarPosition, setAvatarPosition] = useState([0, 0.5, 8]);
  const [isCheckingOut, setIsCheckingOut] = useState(false);
  const [isMinimapVisible, setIsMinimapVisible] = useState(true);
  const [isEntered, setIsEntered] = useState(false);
  const [isCartOpen, setIsCartOpen] = useState(false);
  const [navigationPath, setNavigationPath] = useState([]);
  const [shoppingList, setShoppingList] = useState([]);
  const controlsRef = useRef();
  const canvasRef = useRef();
  const [sidebarWidth, setSidebarWidth] = useState(320);
  const [isResizing, setIsResizing] = useState(false);
  const sidebarRef = useRef(null);
  const startXRef = useRef(0);
  const startWidthRef = useRef(0);

  // Handle drag resize
  const startResize = useCallback((e) => {
    setIsResizing(true);
    startXRef.current = e.clientX;
    startWidthRef.current = sidebarWidth;
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';
  }, [sidebarWidth]);

  const doResize = useCallback((e) => {
    if (!isResizing) return;
    const delta = e.clientX - startXRef.current;
    const newWidth = Math.max(280, Math.min(600, startWidthRef.current + delta));
    setSidebarWidth(newWidth);
  }, [isResizing]);

  const stopResize = useCallback(() => {
    setIsResizing(false);
    document.body.style.cursor = '';
    document.body.style.userSelect = '';
  }, []);

  useEffect(() => {
    window.addEventListener('mousemove', doResize);
    window.addEventListener('mouseup', stopResize);
    return () => {
      window.removeEventListener('mousemove', doResize);
      window.removeEventListener('mouseup', stopResize);
    };
  }, [doResize, stopResize]);

  // Toggle sidebar width
  const toggleSidebarWidth = useCallback(() => {
    setSidebarWidth(prev => prev === 320 ? 480 : 320);
  }, []);

  // Responsive handling
  useEffect(() => {
    const handleResize = () => {
      if (window.innerWidth < 768) {
        setIsCartOpen(false);
        setSidebarWidth(0);
      } else {
        setIsCartOpen(true);
        setSidebarWidth(320);
      }
    };

    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // Fetch products from backend
  useEffect(() => {
    const fetchProducts = async () => {
      try {
        const response = await axios.get(`${API_BASE_URL}/api/products`);
        setProducts(response.data);
      } catch (error) {
        console.error('Failed to fetch products:', error);
      }
    };
    
    fetchProducts();
  }, []);

  // Fetch shopping list
  useEffect(() => {
    const fetchShoppingList = async () => {
      try {
        const response = await axios.get(`${API_BASE_URL}/api/users/${USER_ID}/shopping-list`);
        setShoppingList(response.data);
      } catch (error) {
        console.error('Failed to fetch shopping list:', error);
      }
    };
    
    fetchShoppingList();
  }, []);

  const handleCategorySelect = (category) => {
    setSelectedAisle(category);
    setSelectedProduct(null);
    
    // Find the aisle position
    const aisle = aisleConfig[category];
    if (aisle) {
      // Move avatar to the aisle
      setNavigationPath([avatarPosition, aisle.position]);
      setAvatarPosition(aisle.position);
      
      // Move camera to the aisle
      if (controlsRef.current) {
        controlsRef.current.target.set(...aisle.position);
        controlsRef.current.update();
      }
    }
  };

  const handleSearch = (term) => {
    setSearchTerm(term);
    
    if (!term) {
    setSelectedAisle(null);
    setSelectedProduct(null);
    return;
  }
  const lowerTerm = term.toLowerCase();
   // First, check if any aisle name matches
  const matchingAisle = Object.keys(aisleConfig).find(aisleName => 
    aisleName.toLowerCase().includes(lowerTerm)
  );

  // Then check for products that match
  const matchingProducts = products.filter(p => 
    p?.name?.toLowerCase().includes(lowerTerm) ||
    p?.category?.toLowerCase().includes(lowerTerm)
  );

   // Prioritize aisle matches
  if (matchingAisle) {
    setSelectedAisle(matchingAisle);
    setSelectedProduct(null);
    
    // Move to the aisle
    const aisle = aisleConfig[matchingAisle];
    if (aisle) {
      setNavigationPath([avatarPosition, aisle.position]);
      setAvatarPosition(aisle.position);
      
      if (controlsRef.current) {
        controlsRef.current.target.set(...aisle.position);
        controlsRef.current.update();
      }
    }
  } 
  // If no aisle match, select first matching product
  else if (matchingProducts.length > 0) {
    const foundProduct = matchingProducts[0];
    setSelectedProduct(foundProduct);
    handleCategorySelect(foundProduct.category);
  } 
  // Otherwise clear selection
  else {
    setSelectedAisle(null);
    setSelectedProduct(null);
  }
};
      
      

  const addToCart = (product) => {
    const existingItem = cartItems.find(item => item.id === product.id);
    
    if (existingItem) {
      setCartItems(cartItems.map(item => 
        item.id === product.id 
          ? { ...item, quantity: item.quantity + 1 } 
          : item
      ));
    } else {
      setCartItems([...cartItems, { ...product, quantity: 1 }]);
    }
    
    // Play sound effect
    const audio = new Audio('https://assets.mixkit.co/sfx/preview/mixkit-shopping-cart-773.mp3');
    audio.play().catch(e => console.log("Audio play failed:", e));
  };

  const handleCheckout = () => {
    setIsCheckingOut(true);
  };

  const handleCheckoutComplete = () => {
    setIsCheckingOut(false);
    setCartItems([]);
    
    // Move to exit
    setNavigationPath([
      avatarPosition,
      [0, 0.5, 10] // Exit position
    ]);
    
    // Play sound effect
    const audio = new Audio('https://assets.mixkit.co/sfx/preview/mixkit-completion-of-a-level-2063.mp3');
    audio.play().catch(e => console.log("Audio play failed:", e));
  };

  const handleEnterStore = () => {
    setIsEntered(true);
    
    // Animation path: entrance -> center of store
    setNavigationPath([
      [0, 0.5, 10], // Entrance
      [0, 0.5, 8]   // Center
    ]);
    
    setAvatarPosition([0, 0.5, 8]);
    
    // Play sound effect
    const audio = new Audio('https://assets.mixkit.co/sfx/preview/mixkit-door-bell-578.mp3');
    audio.play().catch(e => console.log("Audio play failed:", e));
  };

  const startGuidedTour = () => {
    if (!isEntered) {
      handleEnterStore();
      return;
    }
    
    // Create tour path: current position -> each aisle -> checkout
    const tourPath = [];
    let currentPosition = [...avatarPosition];
    
    // Add current position
    tourPath.push(currentPosition);
    
    // Add each aisle position
    Object.values(aisleConfig).forEach(aisle => {
      if (aisle.position) {
        tourPath.push(aisle.position);
        currentPosition = [...aisle.position];
      }
    });
    
    // Add checkout position
    tourPath.push(aisleConfig.Checkout.position);
    
    setNavigationPath(tourPath);
  };

  const toggleCart = () => {
    setIsCartOpen(!isCartOpen);
  };

  const toggleMinimap = () => {
    setIsMinimapVisible(!isMinimapVisible);
  };

  return (
    <div className="relative w-full h-screen bg-gradient-to-b from-blue-50 to-gray-100 overflow-hidden">
      {/* Header */}
      <header className="absolute top-0 left-0 right-0 z-20 p-4 bg-white/90 backdrop-blur-sm shadow-md">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center">
            <div className="w-10 h-10 bg-blue-600 rounded-lg flex items-center justify-center mr-3">
              <span className="text-white text-xl font-bold">W</span>
            </div>
            <h1 className="text-2xl font-bold text-gray-800">3D Grocery Store</h1>
          </div>
          
          <div className="flex-1 max-w-2xl mx-4">
            <div className="relative">
              <input
                type="text"
                placeholder="Search products..."
                className="w-full px-4 py-3 rounded-full bg-gray-100 border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500 pl-12"
                value={searchTerm}
                onChange={(e) => handleSearch(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleSearch(e.target.value)}
              />
              <div className="absolute left-4 top-3.5 text-gray-500">
                <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M8 4a4 4 0 100 8 4 4 0 000-8zM2 8a6 6 0 1110.89 3.476l4.817 4.817a1 1 0 01-1.414 1.414l-4.816-4.816A6 6 0 012 8z" clipRule="evenodd" />
                </svg>
              </div>
            </div>
          </div>
          
          <div className="flex items-center space-x-4">
            <button 
              className="p-2 rounded-full bg-gray-200 hover:bg-gray-300 transition"
              onClick={toggleMinimap}
            >
              <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M12 1.586l-4 4v12.828l4-4V1.586zM3.707 3.293a1 1 0 00-1.414 0l-1 1a1 1 0 000 1.414l1.586 1.586a1 1 0 001.414 0l1-1a1 1 0 000-1.414L3.707 3.293zm14-.002a1 1 0 00-1.414 0l-1.586 1.586a1 1 0 000 1.414l1 1a1 1 0 001.414 0l1.586-1.586a1 1 0 000-1.414l-1-1z" clipRule="evenodd" />
              </svg>
            </button>
            
            <button
              className="px-3 py-2 bg-purple-600 text-white rounded-full text-sm hover:bg-purple-700 transition"
              onClick={startGuidedTour}
            >
              Guided Tour
            </button>
            
            <div className="relative">
              <ShoppingCartIcon 
                count={cartItems.reduce((total, item) => total + item.quantity, 0)} 
                onClick={toggleCart}
              />
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <div className="absolute inset-0 pt-16">
        <div className="flex h-full">
          {/* Sidebar */}
           <div 
            ref={sidebarRef}
            className={`h-full bg-white shadow-lg flex flex-col transition-all duration-300 ease-in-out ${
              isCartOpen ? 'block' : 'hidden md:block'
            }`}
            style={{ width: isCartOpen ? `${sidebarWidth}px` : '0' }}
          >
            <div className="relative h-full">
              <ShoppingListPanel 
                cartItems={cartItems}
                handleCheckout={handleCheckout}
                isEntered={isEntered}
                handleEnterStore={handleEnterStore}
                shoppingList={shoppingList}
                onSelectCategory={handleCategorySelect}
                toggleCart={toggleCart}
                selectedProduct={selectedProduct}
                isExpanded={sidebarWidth > 380}
              />
              
              {/* Resize Handle */}
              <div 
                className="absolute top-0 -right-1 w-2 h-full cursor-col-resize z-20"
                onMouseDown={startResize}
              />
              
              {/* Toggle Button */}
              <button 
                className="absolute top-1/2 -right-4 bg-white rounded-full p-1 shadow-md z-30"
                onClick={toggleSidebarWidth}
              >
                {sidebarWidth > 380 ? <FiChevronLeft /> : <FiChevronRight />}
              </button>
            </div>
          </div>
          
          {/* 3D Canvas */}
           <div className="flex-1 relative transition-all duration-300" 
               style={{ marginLeft: isCartOpen ? '0' : `-${sidebarWidth}px` }}>
            <Canvas
              ref={canvasRef}
              shadows
              camera={{ position: [0, 15, 15], fov: 50 }}
              className="w-full h-full"
            >
              <ambientLight intensity={0.5} />
              <pointLight position={[10, 10, 10]} intensity={1} castShadow />
              <directionalLight 
                position={[0, 20, 10]} 
                intensity={0.8} 
                castShadow 
                shadow-mapSize-width={1024}
                shadow-mapSize-height={1024}
              />
              
              <StoreLayout 
                aisleConfig={aisleConfig}
                products={products}
                searchTerm={searchTerm}
                selectedAisle={selectedAisle}
                selectedProduct={selectedProduct}
                addToCart={addToCart}
                navigateTo={(position) => {
                  setNavigationPath([avatarPosition, position]);
                }}
                onProductHover={setSelectedProduct}
              />
              
              <Avatars 
                position={avatarPosition} 
                path={navigationPath}
                onPathComplete={() => setNavigationPath([])}
              />
              
              <OrbitControls 
                ref={controlsRef}
                enablePan={true}
                enableZoom={true}
                enableRotate={true}
                minPolarAngle={0}
                maxPolarAngle={Math.PI / 2}
                minDistance={5}
                maxDistance={25}
                minAzimuthAngle={-Math.PI / 4}
                maxAzimuthAngle={Math.PI / 4}
              />
              
              <gridHelper args={[20, 20, '#bbb', '#ddd']} />
              
              {isCheckingOut && <CheckoutAnimation cartItems={cartItems} onComplete={handleCheckoutComplete} />}
            </Canvas>
            
            {/* Minimap */}
            {isMinimapVisible && (
              <Minimap 
                aisleConfig={aisleConfig}
                avatarPosition={avatarPosition}
                selectedAisle={selectedAisle}
                toggleMinimap={toggleMinimap}
              />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}