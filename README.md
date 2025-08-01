# Shopping Demo - AI Fashion Assistant

AI-powered shopping assistant for Musinsa fashion platform using LangGraph multi-agent architecture.

## 🚀 Quick Start

### Prerequisites
- Python 3.12+
- Node.js 18+
- OpenAI API key
- Firecrawl API key

### Installation & Setup

1. **Clone & Environment**
```bash
git clone https://github.com/qhdrl12/shopping-agent-demo.git
cd shopping-demo
cp .env.example .env  # Configure API keys
```

2. **Backend Setup**
```bash
uv sync
uv run python main.py
```

3. **Frontend Setup**
```bash
cd frontend
npm install
npm run dev
```

### Access
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

## 🏗️ Architecture

### LangGraph Unified Workflow
- **Query Nodes**: Smart query analysis & routing
- **Search Nodes**: Musinsa product search & filtering
- **Extraction Nodes**: Product data validation & processing
- **Response Nodes**: User-friendly response generation
- **Question Nodes**: Contextual follow-up question generation

### Tech Stack
- **Backend**: Python, FastAPI, LangGraph, LangChain
- **Frontend**: Next.js, React, TypeScript, Tailwind
- **AI**: OpenAI, Firecrawl
- **Payment**: Kakao Pay integration

## 📁 Project Structure

```
shopping-demo/
├── backend/
│   ├── nodes/           # LangGraph processing nodes
│   ├── workflow/        # Unified workflow orchestration
│   ├── api/             # FastAPI endpoints
│   ├── prompts/         # System prompts & templates
│   ├── tools/           # Firecrawl integration
│   └── utils/           # Utility functions
├── frontend/            # Next.js application
├── main.py              # Backend entry point
└── pyproject.toml       # Python dependencies
```

## ✨ Features

### Core Functionality
- 🔍 AI-powered fashion search
- 🚀 Real-time streaming chat
- 💳 Kakao Pay integration
- 🔄 Interactive query examples
- 📱 Responsive design
- 👟 Brand-specific search (Nike support)

### 🆕 Recent Updates
- 💡 **Smart Suggested Questions**: AI-generated contextual follow-up questions
- 🤖 **Intelligent Query Routing**: Distinguishes between product searches and general questions  
- 🎯 **Enhanced Streaming**: Token-level streaming for real-time responses
- 🎨 **Modern UI**: Interactive suggestion cards with hover effects

## 📚 Documentation

- [Backend README](backend/README.md) - API details & architecture
- [Frontend README](frontend/README.md) - UI components & setup
- [CLAUDE.md](CLAUDE.md) - AI assistant guidance

## 🔧 Environment Variables

```env
OPENAI_API_KEY=your_openai_api_key
FIRECRAWL_API_KEY=your_firecrawl_api_key
LANGSMITH_API_KEY=your_langsmith_api_key
LANGSMITH_PROJECT=musinsa-shopping-agent
```

## 🔧 Troubleshooting

- **Import errors**: Check directory paths
- **API issues**: Verify environment variables
- **Port conflicts**: Ensure ports 3000/8000 available
- **CORS errors**: Update frontend configuration

## 📄 License

MIT License - see LICENSE file for details