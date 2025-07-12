import { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Card } from '../components/Card';
import { apiClient } from '../api/client';
import { API_ENDPOINTS } from '../api/config';

// Expanded store layout with more space and better positioning
const storeLayout = {
  'A1: Canned & Jarred Meats': { x: 80, y: 80, color: 'bg-red-100', icon: '🥫' },
  'A2: Cooking Sauces & Marinades': { x: 200, y: 80, color: 'bg-orange-100', icon: '🧂' },
  'A3: Packaged Meals': { x: 320, y: 80, color: 'bg-yellow-100', icon: '🍱' },
  'A4: Canned & Jarred Beans & Legumes': { x: 440, y: 80, color: 'bg-amber-100', icon: '🫘' },
  'A5: Sofas & Couches': { x: 560, y: 80, color: 'bg-lime-100', icon: '🛋️' },
  'A6: Tablet Computers': { x: 80, y: 180, color: 'bg-green-100', icon: '💻' },
  'A7: Cell Phones': { x: 200, y: 180, color: 'bg-emerald-100', icon: '📱' },
  'A8: Refrigerators': { x: 320, y: 180, color: 'bg-teal-100', icon: '❄️' },
  'A9: Video Game Consoles': { x: 440, y: 180, color: 'bg-cyan-100', icon: '🎮' },
  'A10: Handheld Video Games': { x: 560, y: 180, color: 'bg-sky-100', icon: '🎮' },
  'A11: Ceiling Fans': { x: 80, y: 280, color: 'bg-blue-100', icon: '🌀' },
  'A12: Sectional Sofas': { x: 200, y: 280, color: 'bg-indigo-100', icon: '🛋️' },
  'A13: Futon Frames & Sets': { x: 320, y: 280, color: 'bg-violet-100', icon: '🛏️' },
  'A14: Canned & Jarred Poultry': { x: 440, y: 280, color: 'bg-purple-100', icon: '🍗' },
  'A15: Canned & Jarred Vegetables': { x: 560, y: 280, color: 'bg-fuchsia-100', icon: '🥦' },
  'A16: Prepared & Packaged Soups': { x: 80, y: 380, color: 'bg-pink-100', icon: '🥣' },
  'A17: Laptop Computers': { x: 200, y: 380, color: 'bg-rose-100', icon: '💻' },
  'A18: Loveseats': { x: 320, y: 380, color: 'bg-red-50', icon: '🪑' },
  'A19: Sausages & Hot Dogs': { x: 440, y: 380, color: 'bg-orange-50', icon: '🌭' },
  'A20: Toy Doodle Tablets': { x: 560, y: 380, color: 'bg-yellow-50', icon: '🧸' },
  'A21: Sandwich Spreads': { x: 320, y: 480, color: 'bg-lime-50', icon: '🥪' },
  'Checkout': { x: 680, y: 280, color: 'bg-gray-200', icon: '💳' },
  'Customer Service': { x: 680, y: 380, color: 'bg-blue-100', icon: '🛎️' },
};

export default function Map({ userId="cmcqhdhix00jauwtg9jza2xo7" }) {
  const [shoppingList, setShoppingList] = useState([]);
  const [activeAisle, setActiveAisle] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [products, setProducts] = useState({});
  const [currentStep, setCurrentStep] = useState(-1); // -1: not started, 0: start, 1-n: aisles, n+1: checkout
  const [isNavigating, setIsNavigating] = useState(false);
  const [progress, setProgress] = useState(0);
  const listRef = useRef(null);

  // Fetch shopping list and products
  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        setError(null);
        
        // Fetch shopping list
        const listResponse = await apiClient.get(API_ENDPOINTS.SHOPPING_LIST(userId));
        
        // Get product IDs
        const productIds = listResponse.map(item => item.product_id);
        
        // Fetch products in batch
        const productsResponse = await apiClient.get(API_ENDPOINTS.PRODUCTS, {
          ids: productIds.join(',')
        });
        
        // Create product map
        const productMap = {};
        productsResponse.forEach(product => {
          productMap[product.id] = product;
        });
        
        setProducts(productMap);
        setShoppingList(listResponse.map(item => ({
          ...item,
          product: productMap[item.product_id] || null
        })));
        
      } catch (err) {
        console.error('Error fetching data:', err);
        setError(err.message || 'Failed to load shopping list');
      } finally {
        setLoading(false);
      }
    };
    
    if (userId) fetchData();
  }, [userId]);

  // Group items by aisle
  const groupedItems = shoppingList.reduce((groups, item) => {
    const aisle = item.product?.category || 'Other';
    const aisleKey = Object.keys(storeLayout).find(key => key.includes(aisle)) || `Aisle: ${aisle}`;
    
    if (!groups[aisleKey]) groups[aisleKey] = [];
    groups[aisleKey].push(item);
    return groups;
  }, {});

  // Create aisles from grouped items
  const aisles = Object.entries(groupedItems).map(([name, items]) => {
    const aisleConfig = storeLayout[name] || {
      x: Math.random() * 500 + 50,
      y: Math.random() * 500 + 50,
      color: 'bg-gray-100',
      icon: '🛒'
    };
    
    return {
      name,
      items,
      count: items.reduce((sum, item) => sum + item.quantity, 0),
      ...aisleConfig
    };
  });

  // Sort aisles by aisle number
  const sortedAisles = [...aisles].sort((a, b) => {
    const aNum = parseInt(a.name.split(':')[0].replace('A', ''));
    const bNum = parseInt(b.name.split(':')[0].replace('A', ''));
    return aNum - bNum;
  });

  // Start navigation
  const startNavigation = () => {
    setIsNavigating(true);
    setCurrentStep(0); // Start at the beginning
    setProgress(0);
  };

  // Go to next step
  const goToNextStep = () => {
    if (currentStep < sortedAisles.length) {
      setCurrentStep(prev => prev + 1);
      setProgress(((currentStep + 1) / (sortedAisles.length + 1)) * 100);
    } else {
      // Finished navigation
      setIsNavigating(false);
      setCurrentStep(-1);
    }
  };

  // Go to previous step
  const goToPrevStep = () => {
    if (currentStep > 0) {
      setCurrentStep(prev => prev - 1);
      setProgress(((currentStep - 1) / (sortedAisles.length + 1)) * 100);
    }
  };

  // Effect to set active aisle based on current step
  useEffect(() => {
    if (currentStep === 0) {
      setActiveAisle(null); // Start point
    } else if (currentStep > 0 && currentStep <= sortedAisles.length) {
      const aisle = sortedAisles[currentStep - 1];
      setActiveAisle(aisle.name);
      
      // Scroll to the active aisle in the list
      if (listRef.current) {
        const element = document.getElementById(`aisle-${currentStep - 1}`);
        if (element) {
          element.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
      }
    } else if (currentStep === sortedAisles.length + 1) {
      setActiveAisle('Checkout');
    }
  }, [currentStep, sortedAisles]);

  // Loading state
  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center h-full p-8 bg-gradient-to-br from-blue-50 to-gray-50 rounded-2xl">
        <div className="animate-pulse w-16 h-16 bg-blue-200 rounded-full mb-4"></div>
        <div className="h-4 w-48 bg-gray-200 rounded mb-2"></div>
        <div className="h-4 w-32 bg-gray-200 rounded"></div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-full p-8 bg-gradient-to-br from-blue-50 to-gray-50 rounded-2xl">
        <div className="text-5xl mb-3">⚠️</div>
        <h3 className="text-xl font-bold text-red-600 mb-2">Error Loading Map</h3>
        <p className="text-gray-600 mb-4 text-center">{error}</p>
        <button 
          className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition shadow-md"
          onClick={() => window.location.reload()}
        >
          Try Again
        </button>
      </div>
    );
  }

  // Empty state
  if (shoppingList.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full p-8 bg-gradient-to-br from-blue-50 to-gray-50 rounded-2xl">
        <div className="text-6xl mb-4">🛒</div>
        <h3 className="text-xl font-bold text-gray-700 mb-2">Your Shopping List is Empty</h3>
        <p className="text-gray-500 text-center mb-6">
          Add some items to your shopping list to see them on the map!
        </p>
        <button className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition shadow-md">
          Start Shopping
        </button>
      </div>
    );
  }

  return (
    <div className="flex flex-col lg:flex-row h-[85vh] gap-6 bg-gradient-to-br from-blue-50 to-gray-50 rounded-2xl p-4 shadow-lg">
      {/* Map Area */}
      <div className="relative flex-1 bg-white rounded-2xl shadow-lg overflow-hidden flex items-center justify-center min-h-[600px]">
        {/* Store map background */}
        <div className="absolute inset-0 bg-gradient-to-br from-blue-50 to-gray-100">
          {/* Grid pattern for aisles */}
          <div className="absolute inset-0 grid grid-cols-5 grid-rows-7 gap-4 opacity-20">
            {Array.from({ length: 35 }).map((_, i) => (
              <div key={i} className="border border-gray-300 rounded"></div>
            ))}
          </div>
          
          {/* Aisle markers */}
          {Object.entries(storeLayout).map(([name, aisle]) => (
            <div 
              key={name}
              className={`absolute w-24 h-8 rounded-md ${aisle.color} flex items-center justify-center shadow-md border border-white`}
              style={{ left: `${aisle.x - 48}px`, top: `${aisle.y - 16}px` }}
            >
              <span className="text-xs font-bold text-gray-700">{name.split(':')[0]}</span>
            </div>
          ))}
          
          {/* Store features */}
          <div className="absolute top-4 left-4 bg-blue-600 text-white px-3 py-1 rounded-full text-xs font-bold">
            ENTRANCE
          </div>
          
          <div className="absolute top-4 right-4 bg-green-600 text-white px-3 py-1 rounded-full text-xs font-bold">
            EXIT
          </div>
        </div>
        
        {/* Start Here marker */}
        <motion.div
          className="absolute z-20 group cursor-pointer"
          style={{ left: 80, top: 480, transform: 'translate(-50%, -50%)' }}
          animate={currentStep === 0 ? { scale: [1, 1.2, 1] } : { scale: 1 }}
          transition={{ duration: 0.7, repeat: currentStep === 0 ? Infinity : 0 }}
        >
          <div className="w-16 h-16 bg-gradient-to-br from-yellow-400 to-orange-500 rounded-full flex items-center justify-center shadow-lg mx-auto">
            <span className="text-2xl">🏁</span>
          </div>
          <div className="mt-2 text-center">
            <span className="font-bold text-orange-600 text-sm">Start Here</span>
          </div>
        </motion.div>
        
        {/* Aisle Pins */}
        {sortedAisles.map((aisle, index) => (
          <motion.div
            key={aisle.name}
            className="absolute z-20 group cursor-pointer"
            style={{ left: aisle.x, top: aisle.y, transform: 'translate(-50%, -50%)' }}
            animate={
              activeAisle === aisle.name ? { scale: [1, 1.2, 1] } : 
              currentStep > index ? { scale: 1, opacity: 0.7 } : 
              { scale: 1 }
            }
            transition={{ duration: 0.7, repeat: activeAisle === aisle.name ? Infinity : 0 }}
            onClick={() => setActiveAisle(activeAisle === aisle.name ? null : aisle.name)}
            whileHover={{ scale: 1.1 }}
          >
            <button
              className={`w-10 h-10 rounded-full shadow-lg border-2 border-white flex items-center justify-center transition-all
                ${activeAisle === aisle.name ? 'bg-gradient-to-br from-blue-500 to-blue-700 ring-4 ring-blue-300' : 
                  currentStep > index ? 'bg-gray-300' : 
                  'bg-gradient-to-br from-blue-500 to-blue-700 hover:ring-2 hover:ring-blue-200'}`}
            >
              <span className={`${currentStep > index ? 'text-gray-500' : 'text-white'}`}>
                {aisle.icon}
              </span>
            </button>
            
            {/* Tooltip */}
            <div className="absolute left-1/2 -translate-x-1/2 mt-2 opacity-0 group-hover:opacity-100 transition pointer-events-none">
              <div className="bg-white text-gray-800 text-xs font-bold px-3 py-1 rounded shadow border border-gray-200 whitespace-nowrap">
                {aisle.name}
              </div>
            </div>
          </motion.div>
        ))}
        
        {/* Path lines */}
        <svg className="absolute inset-0 pointer-events-none">
          {/* Line from start to first aisle */}
          {sortedAisles.length > 0 && currentStep >= 0 && (
            <line 
              x1={80} 
              y1={480} 
              x2={sortedAisles[0].x} 
              y2={sortedAisles[0].y} 
              stroke="#93c5fd" 
              strokeWidth="3" 
              strokeDasharray="8 4"
            />
          )}
          
          {/* Lines between aisles */}
          {sortedAisles.map((aisle, i) => {
            if (i === 0) return null;
            const prevAisle = sortedAisles[i - 1];
            return (
              <line 
                key={`path-${i}`} 
                x1={prevAisle.x} 
                y1={prevAisle.y} 
                x2={aisle.x} 
                y2={aisle.y} 
                stroke="#93c5fd" 
                strokeWidth="3" 
                strokeDasharray="8 4"
                opacity={currentStep >= i ? 1 : 0.3}
              />
            );
          })}
          
          {/* Line from last aisle to checkout */}
          {sortedAisles.length > 0 && (
            <line 
              x1={sortedAisles[sortedAisles.length - 1].x} 
              y1={sortedAisles[sortedAisles.length - 1].y} 
              x2={storeLayout.Checkout.x} 
              y2={storeLayout.Checkout.y} 
              stroke="#93c5fd" 
              strokeWidth="3" 
              strokeDasharray="8 4"
              opacity={currentStep > sortedAisles.length ? 1 : 0.3}
            />
          )}
        </svg>
        
        {/* Checkout marker */}
        <motion.div
          className="absolute z-20 group cursor-pointer"
          style={{ left: storeLayout.Checkout.x, top: storeLayout.Checkout.y, transform: 'translate(-50%, -50%)' }}
          animate={currentStep > sortedAisles.length ? { scale: [1, 1.05, 1] } : { scale: 1 }}
          transition={{ duration: 1.5, repeat: currentStep > sortedAisles.length ? Infinity : 0 }}
        >
          <button
            className={`w-12 h-12 rounded-full shadow-lg border-2 border-white flex items-center justify-center transition-all
              ${currentStep > sortedAisles.length ? 
                'bg-gradient-to-br from-red-500 to-red-700' : 
                'bg-gradient-to-br from-gray-400 to-gray-600'}`}
          >
            <span className="text-white text-xl">{storeLayout.Checkout.icon}</span>
          </button>
          <div className="absolute left-1/2 -translate-x-1/2 mt-2">
            <div className="bg-white text-gray-800 text-xs font-bold px-3 py-1 rounded shadow border border-gray-200 whitespace-nowrap">
              Checkout
            </div>
          </div>
        </motion.div>
        
        {/* Navigation indicator */}
        <AnimatePresence>
          {isNavigating && (
            <motion.div 
              className="absolute top-4 left-1/2 transform -translate-x-1/2 bg-white shadow-lg rounded-full px-4 py-2 flex items-center"
              initial={{ opacity: 0, y: -20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
            >
              <div className="flex items-center">
                <button 
                  className="w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center mr-2"
                  onClick={goToPrevStep}
                  disabled={currentStep === 0}
                >
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-gray-700" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M12.707 5.293a1 1 0 010 1.414L9.414 10l3.293 3.293a1 1 0 01-1.414 1.414l-4-4a1 1 0 010-1.414l4-4a1 1 0 011.414 0z" clipRule="evenodd" />
                  </svg>
                </button>
                
                <div className="w-32 bg-gray-200 rounded-full h-2.5 mr-3">
                  <div 
                    className="bg-green-500 h-2.5 rounded-full" 
                    style={{ width: `${progress}%` }}
                  ></div>
                </div>
                
                <button 
                  className="w-8 h-8 rounded-full bg-blue-500 flex items-center justify-center"
                  onClick={goToNextStep}
                >
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-white" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z" clipRule="evenodd" />
                  </svg>
                </button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
      
      {/* Shopping List */}
      <Card className="w-full lg:w-80 p-6 flex flex-col gap-3 bg-white/90 backdrop-blur-sm shadow-lg rounded-2xl border border-gray-200">
        <div className="flex items-center justify-between mb-4 pb-2 border-b border-gray-200">
          <h2 className="text-xl font-bold text-blue-800 flex items-center">
            <span className="mr-2">🛒</span> Shopping List
          </h2>
          <span className="bg-blue-100 text-blue-800 px-2 py-1 rounded-full text-sm font-medium">
            {shoppingList.reduce((sum, item) => sum + item.quantity, 0)} items
          </span>
        </div>
        
        <div className="overflow-y-auto flex-1" ref={listRef}>
          <div className="mb-4">
            <div className="flex items-center justify-between mb-2">
              <h3 className="font-semibold text-gray-700">Optimized Route:</h3>
              <span className="text-xs bg-green-100 text-green-800 px-2 py-1 rounded">
                Most Efficient
              </span>
            </div>
            <div className="bg-gray-50 rounded-lg p-3 text-sm">
              <div className="flex items-center py-1 mb-1">
                <span className="w-6 h-6 rounded-full bg-yellow-500 text-white flex items-center justify-center text-xs mr-2">
                  S
                </span>
                <span className="font-medium">Start Here</span>
              </div>
              
              {sortedAisles.map((aisle, index) => (
                <div 
                  key={aisle.name} 
                  id={`aisle-${index}`}
                  className={`flex items-center py-1 ${currentStep === index + 1 ? 'bg-blue-100 rounded px-2' : ''}`}
                >
                  <span className="w-6 h-6 rounded-full bg-blue-500 text-white flex items-center justify-center text-xs mr-2">
                    {index + 1}
                  </span>
                  <span className="font-medium">{aisle.name}</span>
                </div>
              ))}
              
              <div className="flex items-center py-1 mt-2 border-t border-gray-200 pt-2">
                <span className="w-6 h-6 rounded-full bg-red-500 text-white flex items-center justify-center text-xs mr-2">
                  ✓
                </span>
                <span className="font-medium">Checkout</span>
              </div>
            </div>
          </div>
          
          <div className="space-y-4">
            {sortedAisles.map((aisle, index) => (
              <div 
                key={aisle.name} 
                className={`border border-gray-200 rounded-lg overflow-hidden transition-all ${
                  currentStep === index + 1 ? 'ring-2 ring-blue-500' : ''
                }`}
              >
                <button
                  className={`flex items-center w-full text-left p-3 transition font-medium ${
                    activeAisle === aisle.name ? 'bg-blue-50 text-blue-700' : 'hover:bg-gray-50'
                  }`}
                  onClick={() => setActiveAisle(activeAisle === aisle.name ? null : aisle.name)}
                >
                  <div className="flex items-center">
                    <span className={`w-8 h-8 rounded-full ${aisle.color} flex items-center justify-center text-base mr-3`}>
                      {aisle.icon}
                    </span>
                    <div>
                      <div className="font-semibold">{aisle.name.split(':')[0]}</div>
                      <div className="text-xs text-gray-500">{aisle.name.split(':')[1]} • {aisle.count} items</div>
                    </div>
                  </div>
                  <span className={`ml-auto transform transition ${activeAisle === aisle.name ? 'rotate-180' : ''}`}>
                    <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-gray-400" viewBox="0 0 20 20" fill="currentColor">
                      <path fillRule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clipRule="evenodd" />
                    </svg>
                  </span>
                </button>
                
                {activeAisle === aisle.name && (
                  <motion.div 
                    className="bg-white border-t border-gray-100"
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                  >
                    <div className="p-3 space-y-2">
                      {aisle.items.map((item) => (
                        <div key={item.id} className="flex items-center py-2 px-3 bg-white rounded border border-gray-100">
                          <span className="w-6 h-6 rounded-full bg-gray-100 flex items-center justify-center text-xs mr-3 font-medium">
                            {item.quantity}
                          </span>
                          <span className="flex-1 truncate">
                            {item.product?.name || `Product ${item.product_id}`}
                          </span>
                          {item.product?.thumbnailUrl && (
                            <img 
                              src={item.product.thumbnailUrl} 
                              alt={item.product.name} 
                              className="w-8 h-8 rounded object-cover ml-3"
                            />
                          )}
                        </div>
                      ))}
                    </div>
                  </motion.div>
                )}
              </div>
            ))}
          </div>
        </div>
        
        <div className="mt-4 pt-4 border-t border-gray-200">
          {!isNavigating ? (
            <button 
              className="w-full py-3 bg-gradient-to-r from-green-500 to-green-600 text-white font-semibold rounded-lg shadow-md hover:shadow-lg transition flex items-center justify-center"
              onClick={startNavigation}
            >
              <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 mr-2" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z" clipRule="evenodd" />
              </svg>
              Start Navigation
            </button>
          ) : (
            <div className="flex gap-2">
              <button 
                className="flex-1 py-3 bg-gradient-to-r from-gray-500 to-gray-600 text-white font-semibold rounded-lg shadow-md hover:shadow-lg transition"
                onClick={() => setIsNavigating(false)}
              >
                Cancel
              </button>
              <button 
                className="flex-1 py-3 bg-gradient-to-r from-blue-500 to-blue-600 text-white font-semibold rounded-lg shadow-md hover:shadow-lg transition"
                onClick={goToNextStep}
              >
                {currentStep > sortedAisles.length ? 'Finish' : 'Next Step'}
              </button>
            </div>
          )}
        </div>
      </Card>
    </div>
  );
}