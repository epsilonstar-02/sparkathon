// src/components/Product.js
import React, { useRef } from 'react';
import { Box, Text } from '@react-three/drei';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';

const Product = ({ product, position, isHighlighted, addToCart }) => {
  const ref = useRef();
  const color = isHighlighted ? '#fbbf24' : '#64748b';
  
  // Animation for highlighted products
  useFrame(({ clock }) => {
    if (ref.current) {
      if (isHighlighted) {
        ref.current.position.y = position[1] + Math.sin(clock.getElapsedTime() * 2) * 0.1;
        ref.current.rotation.y = clock.getElapsedTime() * 0.5;
      } else {
        ref.current.position.y = position[1];
        ref.current.rotation.y = 0;
      }
    }
  });

  return (
    <group 
      ref={ref} 
      position={position}
      onClick={() => addToCart(product)}
    >
      <Box
        args={[0.5, 0.5, 0.5]}
        castShadow
        receiveShadow
      >
        <meshStandardMaterial 
          color={color}
          emissive={isHighlighted ? color : '#000'}
          emissiveIntensity={isHighlighted ? 0.5 : 0}
        />
      </Box>
      
      <Text
        position={[0, 0.8, 0]}
        color={isHighlighted ? "#000" : "#334155"}
        fontSize={0.15}
        maxWidth={1}
        textAlign="center"
        anchorX="center"
        anchorY="top"
      >
        {product.name}
      </Text>
      
      <Text
        position={[0, 0.6, 0]}
        color={isHighlighted ? "#000" : "#4b5563"}
        fontSize={0.12}
        anchorX="center"
        anchorY="top"
      >
        ${product.price.toFixed(2)}
      </Text>
    </group>
  );
};

export default Product;