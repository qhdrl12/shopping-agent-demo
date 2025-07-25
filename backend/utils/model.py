import os
from langchain_core.language_models import BaseChatModel
from langchain.chat_models import init_chat_model

def load_chat_model(fully_specified_name: str, temperature: float = 0.7, streaming: bool = False) -> BaseChatModel:
    """Load a chat model from a fully specified name.
    
    Supports both OpenAI and OpenRouter models with automatic API key handling.
    
    Args:
        fully_specified_name (str): String in the format 'provider/model'.
        
    Examples:
        - "openai/gpt-4.1-mini"
        - "openrouter/anthropic/claude-3.5-sonnet"
        
    Raises:
        ValueError: If required API key is not found in environment variables.
    """
    print(f"fully_specified_name: {fully_specified_name}")
    provider, model = fully_specified_name.split("/", maxsplit=1)
    
    kwargs = {}

    # Check for required API keys
    if provider == "openrouter":
        if not os.getenv("OPENROUTER_API_KEY"):
            raise ValueError("OPENROUTER_API_KEY not found in environment variables")
        print(f"Loading OpenRouter model: {model}")
        provider = "openai"
        kwargs["base_url"] = "https://openrouter.ai/api/v1"
        kwargs["openai_api_key"] = os.getenv("OPENROUTER_API_KEY")

    elif provider == "openai":
        if not os.getenv("OPENAI_API_KEY"):
            raise ValueError("OPENAI_API_KEY not found in environment variables")
        print(f"Loading OpenAI model: {model}")
    
    if streaming:
        kwargs["streaming"] = True
    
    return init_chat_model(model, model_provider=provider, temperature=temperature, **kwargs)