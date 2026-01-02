from .interface import WebSearchProviderInterface
from .exa_provider import ExaProvider
from .provider_enum import WebSearchProviderType


def get_web_search_provider(
    provider_type: str = WebSearchProviderType.EXA,
) -> WebSearchProviderInterface:
    """
    Get web search provider instance.

    Args:
        provider_type: Type of provider ('exa'). Defaults to 'exa'.

    Returns:
        An instance of the requested web search provider.
    """
    provider_type = provider_type.lower()

    match provider_type:
        case WebSearchProviderType.EXA:
            return ExaProvider()
        case _:
            raise ValueError(f"Unknown web search provider type: {provider_type}")
