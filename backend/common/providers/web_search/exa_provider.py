from typing import Optional, List

from exa_py import Exa

from common.core.config import settings
from common.core.otel_axiom_exporter import get_logger
from .interface import WebSearchProviderInterface
from .models import SearchResponse, SearchResult

logger = get_logger(__name__)


class ExaProvider(WebSearchProviderInterface):
    """Exa implementation of web search provider."""

    def __init__(self):
        self.client = Exa(api_key=settings.exa_api_key)

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
        Search the web using Exa API.

        Args:
            query: The search query
            num_results: Number of results to return
            include_domains: List of domains to restrict results to
            exclude_domains: List of domains to exclude from results
            start_published_date: Filter results published after this date (ISO 8601)
            end_published_date: Filter results published before this date (ISO 8601)
            category: Category filter (e.g., news, research paper, company, etc.)
            search_type: Type of search (keyword, neural, fast, auto)
            include_text: Whether to include full text content from webpages

        Returns:
            SearchResponse with results
        """
        # Build search parameters
        search_params = {
            "query": query,
            "num_results": num_results,
            "type": search_type or "auto",
        }

        if include_domains:
            search_params["include_domains"] = include_domains
        if exclude_domains:
            search_params["exclude_domains"] = exclude_domains
        if start_published_date:
            search_params["start_published_date"] = start_published_date
        if end_published_date:
            search_params["end_published_date"] = end_published_date
        if category:
            search_params["category"] = category

        # Use search_and_contents if text is requested, otherwise use regular search
        if include_text:
            logger.info(f"Performing Exa search with text content for query: {query}")
            response = self.client.search_and_contents(text=True, **search_params)
            # ResultWithText: url, id, title, published_date, author, text
            results = [
                SearchResult(
                    title=result.title if result.title else "",
                    url=result.url,
                    published_date=result.published_date,
                    author=result.author,
                    score=None,  # Exa Result doesn't have score
                    text=result.text,
                )
                for result in response.results
            ]
        else:
            logger.info(
                f"Performing Exa search without text content for query: {query}"
            )
            response = self.client.search(**search_params)
            # Result: url, id, title, published_date, author
            results = [
                SearchResult(
                    title=result.title if result.title else "",
                    url=result.url,
                    published_date=result.published_date,
                    author=result.author,
                    score=None,  # Exa Result doesn't have score
                    text=None,
                )
                for result in response.results
            ]

        return SearchResponse(
            results=results,
            request_id=None,  # Exa SearchResponse doesn't have request_id
            search_type=None,  # Exa SearchResponse doesn't have search_type
        )

    async def get_page_content(self, url: str) -> str:
        """
        Fetch and extract text content from a specific URL using Exa.

        Args:
            url: The URL to fetch content from

        Returns:
            Extracted text content from the webpage

        Raises:
            Exception: If the URL cannot be fetched or content cannot be extracted
        """
        logger.info(f"Fetching page content for URL: {url}")

        # Use Exa's get_contents to fetch the page
        response = self.client.get_contents([url], text=True)

        # Check if we got a result
        if not response.results or len(response.results) == 0:
            raise Exception(f"No content returned for URL: {url}")

        result = response.results[0]

        # Exa returns text field when text=True
        if not result.text:
            raise Exception(f"No text content available for URL: {url}")

        logger.info(f"Successfully fetched {len(result.text)} characters from {url}")
        return result.text
