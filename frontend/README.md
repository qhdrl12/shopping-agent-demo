# Frontend - Shopping Agent UI

Next.js-based chat interface for AI fashion shopping assistant.

## 🚀 Quick Start

### Installation
```bash
npm install
```

### Development
```bash
npm run dev
```
Visit http://localhost:3000

### Build & Deploy
```bash
npm run build
npm start
```

## 🏗️ Architecture

### Tech Stack
- **Next.js 15.4** - React framework with App Router
- **React 19** - UI components & hooks
- **TypeScript** - Type safety
- **Tailwind CSS 4** - Styling & responsive design
- **Axios** - HTTP client for API calls
- **SWR** - Data fetching & caching

## 📁 Project Structure

```
frontend/
├── src/
│   ├── app/
│   │   ├── page.tsx          # Main chat interface
│   │   ├── layout.tsx        # App layout
│   │   └── payment/          # Payment flow pages
│   │       ├── success/      # Payment success
│   │       ├── fail/         # Payment failure
│   │       └── cancel/       # Payment cancellation
│   └── components/
│       └── Chat.tsx          # Main chat component
├── public/              # Static assets
└── package.json        # Dependencies & scripts
```

## 🎨 Components

### Chat Component (`components/Chat.tsx`)
Main chat interface featuring:
- 💬 Real-time message streaming
- 🎯 Interactive example query buttons
- 💳 Payment integration buttons
- 📱 Responsive design
- 🔄 Session management

### Payment Pages (`app/payment/`)
- **Success**: Payment completion confirmation
- **Fail**: Payment failure handling
- **Cancel**: Payment cancellation processing

## 🔧 Features

### Chat Interface
- Real-time streaming responses
- Markdown message rendering with syntax highlighting
- Interactive example queries for user guidance
- Session persistence across page reloads

### Payment Integration
- Seamless Kakao Pay integration
- Payment status handling (success/fail/cancel)
- Transaction confirmation & receipt display

### User Experience
- Responsive design for mobile & desktop
- Loading states & error handling
- Auto-scroll for new messages
- Clean, modern UI design

## 🌐 API Integration

### Endpoints
- `POST /chat/stream` - Streaming chat responses
- `GET /session/{sessionId}` - Session state retrieval
- Payment endpoints for transaction processing

### Error Handling
- Network error recovery
- API timeout handling
- User-friendly error messages
- Graceful degradation

## 🎯 Example Queries

Interactive buttons provide users with sample queries:
- "무신사에서 인기 있는 나이키 운동화 추천해줘"
- "겨울 패딩 재킷 추천"
- "20대 남성 캐주얼 룩 추천"
- "화이트 스니커즈 비교해줘"

## 🔄 State Management

### Session Management
- Automatic session creation
- Session persistence with localStorage
- Session cleanup on navigation

### Message Flow
- Real-time message streaming
- Message history persistence
- Optimistic UI updates

## 📱 Responsive Design

### Breakpoints
- Mobile: < 768px
- Tablet: 768px - 1024px  
- Desktop: > 1024px

### Features
- Mobile-first approach
- Touch-optimized interactions
- Adaptive layouts
- Performance optimization

## 🎨 Styling

### Tailwind Configuration
- Custom color palette
- Component utilities
- Responsive utilities
- Dark mode support (future)

### Design System
- Consistent spacing & typography
- Modern card-based layouts
- Subtle animations & transitions
- Accessible color contrasts

## 🔍 Development Tools

### Scripts
- `dev` - Development server with Turbopack
- `build` - Production build
- `start` - Production server
- `lint` - ESLint code analysis

### Configuration
- TypeScript strict mode
- ESLint with Next.js config
- Tailwind CSS with PostCSS
- Next.js App Router

## 🐛 Troubleshooting

### Common Issues
- **API Connection**: Check backend server is running on port 8000
- **CORS Errors**: Verify CORS configuration in backend
- **Build Errors**: Check TypeScript types and dependencies
- **Styling Issues**: Verify Tailwind CSS configuration

### Development Tips
- Use browser dev tools for debugging
- Check network tab for API calls
- Monitor console for errors
- Test responsive design at different breakpoints