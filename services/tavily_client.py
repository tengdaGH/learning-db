"""
Unified Tavily client with key rotation.
"""

from tavily import TavilyClient
import config

_tavily_client = None


def get_tavily_client():
    """
    Get a working Tavily client, trying keys in order.
    Lazily initialized and cached.

    Returns:
        TavilyClient instance or None if no keys work
    """
    global _tavily_client

    if _tavily_client is not None:
        return _tavily_client

    if not config.TAVILY_KEYS:
        return None

    for key in config.TAVILY_KEYS:
        try:
            client = TavilyClient(api_key=key)
            client.search("test", max_results=1)
            _tavily_client = client
            return client
        except Exception:
            continue

    return None


def reset_tavily_client():
    """Reset the cached Tavily client (useful for testing)."""
    global _tavily_client
    _tavily_client = None
