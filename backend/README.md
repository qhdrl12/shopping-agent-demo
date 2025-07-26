# Backend - Shopping Agent API

LangGraph-based multi-agent system for Musinsa fashion shopping assistance.

## 🏗️ Architecture

### Agent Workflow
```
User Query → Search → Scrape → Analysis → Response → Output
```

### Agents
- **Search Agent** (`agents/search_agent.py`): Query processing & Musinsa search
- **Scrape Agent** (`agents/scrape_agent.py`): Product data extraction via Firecrawl
- **Analysis Agent** (`agents/analysis_agent.py`): Data analysis & insights
- **Response Agent** (`agents/response_agent.py`): Final response generation

## 📂 Project Structure

```
backend/
├── agents/           # AI agent implementations
├── api/             # FastAPI endpoints
│   └── main.py      # API routes & CORS setup
├── models/          # Pydantic schemas
│   └── schemas.py   # Data models & validation
├── nodes/           # LangGraph node implementations
├── services/        # External service integrations
├── tools/           # External tool integrations
│   └── firecrawl_tools.py    # Web scraping tools
├── workflow/        # LangGraph workflow definitions
└── utils/          # Shared utilities
```

## 🚀 Getting Started

### Installation
```bash
# From project root
uv sync
```

### Environment Setup
```env
OPENAI_API_KEY=your_openai_api_key
FIRECRAWL_API_KEY=your_firecrawl_api_key
LANGSMITH_API_KEY=your_langsmith_api_key
LANGSMITH_PROJECT=musinsa-shopping-agent
```

### Run Server
```bash
# Option 1: Direct Python
uv run python main.py

# Option 2: Uvicorn
uv run uvicorn backend.api.main:app --reload --host 0.0.0.0 --port 8000
```

## 🔌 API Endpoints

### Chat Endpoints
- `POST /chat` - Non-streaming chat
- `POST /chat/stream` - Streaming chat responses

### Health Check
- `GET /health` - Service health status

### API Documentation
Visit http://localhost:8000/docs for interactive Swagger documentation.

## 🧠 Agent Details

### Search Agent
- Analyzes user fashion queries
- Performs Musinsa product searches
- Handles brand-specific searches (Nike support)

### Scrape Agent
- Extracts detailed product information
- Uses Firecrawl for reliable data extraction
- Handles dynamic content & JavaScript

### Analysis Agent
- Processes scraped product data
- Generates insights & comparisons
- Filters & ranks products

### Response Agent
- Creates user-friendly responses
- Formats product information
- Handles error states gracefully

## 🔧 Tools & Services

### Firecrawl Integration
- Web scraping with JavaScript support
- Structured data extraction
- Rate limiting & error handling

### LangSmith Integration
- Agent execution tracing
- Performance monitoring
- Debug & optimization insights

## 📋 Data Models

### Core Schemas (`models/schemas.py`)
- `ChatRequest`: User input validation
- `ChatResponse`: API response format
- `ProductInfo`: Product data structure

## 🚦 Error Handling

- Comprehensive exception handling
- Graceful degradation for API failures
- Detailed error logging
- User-friendly error messages

## 🔍 Debugging

### Logs
Check console output for agent execution steps and errors.

### LangSmith Traces
Monitor agent performance and decision-making in LangSmith dashboard.

### API Testing
Use `/docs` endpoint for interactive API testing.

## 📊 Performance

- Streaming responses for real-time updates
- Efficient agent orchestration
- Optimized Firecrawl usage

## 🔒 Security

- API key validation
- Request sanitization
- CORS configuration