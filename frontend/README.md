# Walmart AI Shopping Assistant Frontend

A modern, interactive React application that provides an AI-powered shopping experience for Walmart customers. This application features a conversational AI interface, interactive store maps, and comprehensive shopping analytics.

## 🚀 Features

### 🤖 AI Chat Interface
- **Mission Control**: Interactive chat with Walmart AI assistant
- **Real-time Thought Stream**: See the AI's reasoning process in real-time
- **Personalized Recommendations**: Get tailored shopping suggestions based on your preferences
- **Natural Language Processing**: Chat naturally about meal planning, grocery lists, and product recommendations

### 📊 Analytics Dashboard
- **Spending Habits**: Visual breakdown of your shopping categories
- **Top Purchases**: Track your most frequently bought items
- **Dietary Profile Adherence**: Monitor your nutritional goals with radar charts
- **Interaction History**: View your past conversations with the AI assistant

### 🗺️ Interactive Store Maps
- **2D Store Map**: Navigate through store aisles with interactive pins
- **3D Store Visualization**: Immersive 3D experience with product locations
- **Optimal Route Planning**: AI-powered pathfinding to optimize your shopping trip
- **Real-time Inventory**: See product availability and promotional offers

### 🎨 Modern UI/UX
- **Responsive Design**: Works seamlessly on desktop and mobile devices
- **Smooth Animations**: Framer Motion powered transitions and micro-interactions
- **Accessibility**: Built with accessibility best practices
- **Beautiful Visuals**: Modern gradient designs and intuitive navigation

## 🛠️ Tech Stack

- **Frontend Framework**: React 19.1.0
- **Build Tool**: Vite 7.0.0
- **Styling**: Tailwind CSS 3.4.17
- **UI Components**: Radix UI
- **3D Graphics**: Three.js with React Three Fiber
- **Animations**: Framer Motion
- **Charts**: Recharts
- **Routing**: React Router DOM
- **Development**: ESLint, PostCSS, Autoprefixer

## 📦 Dependencies

### Production Dependencies

```json
{
  "@radix-ui/react-avatar": "^1.1.10",
  "@radix-ui/react-scroll-area": "^1.2.9",
  "@radix-ui/themes": "^3.2.1",
  "@react-three/drei": "^10.4.2",
  "@react-three/fiber": "^9.1.4",
  "framer-motion": "^12.23.0",
  "react": "^19.1.0",
  "react-dom": "^19.1.0",
  "react-router-dom": "^7.6.3",
  "recharts": "^3.0.2",
  "three": "^0.178.0"
}
```

### Development Dependencies

```json
{
  "@eslint/js": "^9.29.0",
  "@types/react": "^19.1.8",
  "@types/react-dom": "^19.1.6",
  "@vitejs/plugin-react": "^4.5.2",
  "autoprefixer": "^10.4.21",
  "eslint": "^9.29.0",
  "eslint-plugin-react-hooks": "^5.2.0",
  "eslint-plugin-react-refresh": "^0.4.20",
  "globals": "^16.2.0",
  "postcss": "^8.5.6",
  "tailwindcss": "^3.4.17",
  "vite": "^7.0.0"
}
```

## 🚀 Installation

### Prerequisites
- **Node.js**: Version 18.0.0 or higher
- **npm**: Version 9.0.0 or higher (comes with Node.js)

### Quick Start

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd walmart-fe/frontend
   ```

2. **Install all dependencies**
   ```bash
   npm install
   ```

3. **Start the development server**
   ```bash
   npm run dev
   ```

4. **Open your browser**
   Navigate to `http://localhost:5173` to view the application

### Manual Installation

If you prefer to install dependencies manually:

```bash
# Install production dependencies
npm install @radix-ui/react-avatar@^1.1.10
npm install @radix-ui/react-scroll-area@^1.2.9
npm install @radix-ui/themes@^3.2.1
npm install @react-three/drei@^10.4.2
npm install @react-three/fiber@^9.1.4
npm install framer-motion@^12.23.0
npm install react@^19.1.0
npm install react-dom@^19.1.0
npm install react-router-dom@^7.6.3
npm install recharts@^3.0.2
npm install three@^0.178.0

```
## 📱 Application Structure

```
src/
├── components/          # Reusable UI components
│   ├── Avatar.jsx      # User/AI avatar component
│   ├── Card.jsx        # Card layout component
│   ├── MessageInput.jsx # Chat input component
│   └── ScrollArea.jsx  # Scrollable area component
├── pages/              # Main application pages
│   ├── Chat.jsx        # AI chat interface
│   ├── Dashboard.jsx   # Analytics dashboard
│   ├── Map.jsx         # 2D store map
│   └── Map3D.jsx       # 3D store visualization
├── assets/             # Static assets
└── App.jsx             # Main application component
```

## 🎯 Key Features Explained

### AI Chat Interface
The chat interface provides a conversational experience where users can:
- Ask for meal planning suggestions
- Get product recommendations
- Plan shopping lists
- Receive nutritional advice

The interface includes a real-time "thought stream" that shows the AI's reasoning process, making the interaction more transparent and engaging.

### Interactive Maps
- **2D Map**: Traditional store layout with clickable pins for different aisles
- **3D Map**: Immersive 3D visualization with:
  - Product placement and availability
  - Promotional highlights
  - Optimal route calculation using A* pathfinding
  - Real-time inventory status

### Analytics Dashboard
Comprehensive analytics including:
- Spending patterns across categories
- Most purchased items
- Dietary goal tracking
- AI interaction history




