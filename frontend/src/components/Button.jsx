import React from 'react';

export default function Button({ children, onClick, type = 'button', className = '', ...props }) {
  return (
    <button
      type={type}
      onClick={onClick}
      className={`bg-blue-600 text-white font-bold px-7 py-2 rounded-xl shadow hover:bg-blue-700 transition text-base flex items-center justify-center min-h-[40px] ${className}`}
      {...props}
    >
      {children}
    </button>
  );
} 