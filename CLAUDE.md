# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a LangGraph-based shopping agent system that helps users find products on Musinsa (Korean fashion e-commerce platform). The system uses Firecrawl for web scraping and multiple AI agents for processing user queries.

## Technology Stack

### Backend
- **Python 3.12** with **uv** for package management
- **LangGraph**: Multi-agent workflow orchestration
- **LangChain**: LLM integration and tool management
- **FastAPI**: Web API server
- **Firecrawl**: Web scraping and data extraction
- **Pydantic**: Data validation and schemas

### Frontend
- **Next.js 14+** with TypeScript
- **React 18+** with Tailwind CSS
- **Axios**: HTTP client for API calls
- **SWR**: Data fetching and caching

## Development Commands

### Backend
```bash
# Install dependencies
uv sync

# Start development server
uv run python main.py

# Run with uvicorn directly
uv run uvicorn backend.api.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend
```bash
# Navigate to frontend directory
cd frontend/frontend

# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build
```

## Architecture

### Agent Workflow
The system uses a unified workflow with specialized processing nodes:

1. **Query Nodes** (`backend/nodes/query_nodes.py`): Analyzes user queries and handles general questions
2. **Search Nodes** (`backend/nodes/search_nodes.py`): Performs Musinsa product searches and filtering
3. **Extraction Nodes** (`backend/nodes/extraction_nodes.py`): Extracts and validates product information
4. **Response Nodes** (`backend/nodes/response_nodes.py`): Creates final user-friendly responses
5. **Question Nodes** (`backend/nodes/question_nodes.py`): Generates contextual follow-up questions

### Data Flow
```
User Query → Query Analysis → Search/General Response → Product Extraction → Final Response → Suggested Questions
```

### API Endpoints
- `POST /chat`: Non-streaming chat requests
- `POST /chat/stream`: Streaming chat requests
- `GET /session/{session_id}`: Get session state
- `DELETE /session/{session_id}`: Delete session
- `GET /health`: Health check

## Configuration

### Environment Variables
Create a `.env` file in the root directory:
```
OPENAI_API_KEY=your_openai_api_key_here
FIRECRAWL_API_KEY=your_firecrawl_api_key_here
LANGSMITH_API_KEY=your_langsmith_api_key_here
LANGSMITH_PROJECT=musinsa-shopping-agent
```

### File Structure
```
shopping-demo/
├── backend/
│   ├── api/             # FastAPI endpoints
│   ├── nodes/           # LangGraph processing nodes
│   ├── workflow/        # Unified workflow orchestration
│   ├── prompts/         # System prompts and templates
│   ├── tools/           # Firecrawl integration
│   └── utils/           # Utility functions
├── frontend/frontend/   # Next.js application
├── main.py             # Backend entry point
├── pyproject.toml      # Python dependencies
└── .env.example        # Environment variables template
```

## Development Workflow

1. **Start Backend**: `uv run python main.py`
2. **Start Frontend**: `cd frontend/frontend && npm run dev`
3. **Test API**: Backend runs on http://localhost:8000
4. **Test Frontend**: Frontend runs on http://localhost:3000

## Key Features

- **Unified LangGraph Workflow**: Node-based processing with intelligent routing
- **Suggested Questions**: AI-generated contextual follow-up questions
- **Real-time Streaming**: Live updates during agent processing with token-level streaming
- **Musinsa Integration**: Specialized for Korean fashion e-commerce
- **Smart Query Handling**: Distinguishes between product searches and general questions
- **Structured Data**: Pydantic schemas for type safety
- **Session Management**: Persistent chat sessions
- **Interactive UI**: Modern chat interface with suggested question cards
- **Error Handling**: Comprehensive error handling and retry logic

## Debugging

- **Backend Logs**: Check console output for agent execution steps
- **Frontend Network**: Use browser dev tools to inspect API calls
- **LangSmith**: Monitor agent performance and traces (if configured)
- **API Documentation**: Visit http://localhost:8000/docs for interactive API docs

## Common Issues

1. **Import Errors**: Ensure you're in the correct directory when running commands
2. **API Key Issues**: Check that all required environment variables are set
3. **Port Conflicts**: Backend (8000) and Frontend (3000) ports must be available
4. **CORS Errors**: Frontend is configured for localhost:3000, update if needed