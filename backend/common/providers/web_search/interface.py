from abc import ABC, abstractmethod
from typing import Optional, List

from .models import SearchResponse


class WebSearchProviderInterface(ABC):
    """Interface for web search providers."""

    @abstractmethod
    async def search(
        self,
        query: str,
        num_results: int = 10,
        include_domains: Optional[List[str]] = None,
        exclude_domains: Optional[List[str]] = None,
        start_published_date: Optional[str] = None,
        end_published_date: Optional[str] = None,
        category: Optional[str] = None,
        search_type: Optional[str] = None,
        include_text: bool = False,
    ) -> SearchResponse:
        """
        Search the web for the given query.

        Args:
            query: The search query
            num_results: Number of results to return
            include_domains: List of domains to restrict results to
            exclude_domains: List of domains to exclude from results
            start_published_date: Filter results published after this date (ISO 8601)
            end_published_date: Filter results published before this date (ISO 8601)
            category: Category filter (e.g., news, research paper, company, etc.)
            search_type: Type of search (e.g., keyword, neural, auto)
            include_text: Whether to include full text content from webpages

        Returns:
            SearchResponse with results
        """
        pass

    @abstractmethod
    async def get_page_content(self, url: str) -> str:
        """
        Fetch and extract text content from a specific URL.

        Args:
            url: The URL to fetch content from

        Returns:
            Extracted text content from the webpage

        Raises:
            Exception: If the URL cannot be fetched or content cannot be extracted
        """
        pass
