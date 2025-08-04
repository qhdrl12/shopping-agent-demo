# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a LangGraph-based shopping agent system that helps users find products on Musinsa (Korean fashion e-commerce platform). The system uses internal scraping tools and multiple AI agents for processing user queries.

## Technology Stack

### Backend
- **Python 3.12** with **uv** for package management
- **LangGraph**: Multi-agent workflow orchestration
- **LangChain**: LLM integration and tool management
- **FastAPI**: Web API server
- **Internal Scraping Tools**: Custom web scraping and data extraction
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
The system uses two workflow implementations:

#### Internal Scrape Workflow (Default)
Uses `backend/workflow/internal_scrape_workflow.py` with specialized processing nodes:

1. **Query Analysis**: Analyzes user queries and classifies intent
2. **Search Query Optimization**: Optimizes queries for internal scraping tools
3. **Internal Product Search**: Uses `search_detailed_products` tool for comprehensive data extraction
4. **Data Compatibility Parsing**: Converts internal format to legacy-compatible format
5. **Response Generation**: Creates final user-friendly responses
6. **Question Suggestions**: Generates contextual follow-up questions

#### Legacy Workflow (Compatibility)
Available in `backend/workflow/unified_workflow.py` for backward compatibility:

1. **Query Nodes** (`backend/nodes/query_nodes.py`): Analyzes user queries and handles general questions
2. **Search Nodes** (`backend/nodes/search_nodes.py`): Performs Musinsa product searches and filtering
3. **Extraction Nodes** (`backend/nodes/extraction_nodes.py`): Extracts and validates product information
4. **Response Nodes** (`backend/nodes/response_nodes.py`): Creates final user-friendly responses
5. **Question Nodes** (`backend/nodes/question_nodes.py`): Generates contextual follow-up questions

### Data Flow

#### Internal Scrape Workflow (Default)
```
User Query → Query Analysis → Search Query Optimization → Internal Product Search → Data Parsing → Final Response → Suggested Questions
```

#### Legacy Workflow 
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
LANGSMITH_API_KEY=your_langsmith_api_key_here
LANGSMITH_PROJECT=musinsa-shopping-agent

# Optional: For legacy workflow compatibility
FIRECRAWL_API_KEY=your_firecrawl_api_key_here
```

### File Structure
```
shopping-demo/
├── backend/
│   ├── api/             # FastAPI endpoints
│   ├── nodes/           # LangGraph processing nodes (for legacy workflow)
│   ├── workflow/        # Workflow orchestration
│   │   ├── internal_scrape_workflow.py  # Main internal workflow (default)
│   │   └── unified_workflow.py          # Legacy workflow (compatibility)
│   ├── prompts/         # System prompts and templates
│   ├── tools/           # Internal scraping tools and integrations
│   │   └── scrape.py    # Internal scraping tools
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

- **Dual Workflow System**: Internal scrape workflow (default) + Legacy workflow (compatibility)
- **Internal Scraping Tools**: Custom scraping with `search_detailed_products` tool
- **Data Compatibility**: Seamless integration between internal and legacy formats
- **Suggested Questions**: AI-generated contextual follow-up questions
- **Real-time Streaming**: Live updates during agent processing with token-level streaming
- **Musinsa Integration**: Specialized for Korean fashion e-commerce
- **Smart Query Handling**: Distinguishes between product searches and general questions
- **Structured Data**: Pydantic schemas for type safety and validation
- **Session Management**: Persistent chat sessions
- **Interactive UI**: Modern chat interface with suggested question cards
- **Error Handling**: Comprehensive error handling and retry logic
- **Environment Variable Management**: Robust configuration loading

## Debugging

- **Backend Logs**: Check console output for agent execution steps
- **Frontend Network**: Use browser dev tools to inspect API calls
- **LangSmith**: Monitor agent performance and traces (if configured)
- **API Documentation**: Visit http://localhost:8000/docs for interactive API docs

## Common Issues

1. **Import Errors**: Ensure you're in the correct directory when running commands
2. **API Key Issues**: Check that all required environment variables are set (OPENAI_API_KEY is required)
3. **Port Conflicts**: Backend (8000) and Frontend (3000) ports must be available
4. **CORS Errors**: Frontend is configured for localhost:3000, update if needed
5. **Environment Variable Loading**: If getting "OPENAI_API_KEY not found", ensure `.env` file exists in root directory

## Recent Updates

### Internal Scrape Workflow Implementation (Latest)
- **New Default Workflow**: `internal_scrape_workflow.py` replaces Firecrawl dependency
- **Custom Scraping Tools**: Uses `search_detailed_products` for comprehensive data extraction
- **Enhanced Query Optimization**: `INTERNAL_SEARCH_QUERY_OPTIMIZATION_PROMPT` with improved JSON handling
- **Bug Fixes**: Resolved JSON parsing errors, environment variable loading, and shoe size inference issues
- **Data Compatibility**: Legacy format support through `_parse_to_legacy_format()` method
- **Structured Outputs**: New Pydantic models (`InternalQueryOptimizationOutput`, `SearchParameters`)

### Migration Notes
- Internal workflow is now the default for all new requests
- Legacy workflow (`unified_workflow.py`) is maintained for backward compatibility
- No API changes - existing clients continue to work without modification
- Environment variables: `FIRECRAWL_API_KEY` is now optional (only needed for legacy workflow)