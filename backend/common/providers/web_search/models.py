from typing import Optional, List
from pydantic import BaseModel


class SearchResult(BaseModel):
    """Individual search result from a web search provider."""

    title: str
    url: str
    published_date: Optional[str] = None
    author: Optional[str] = None
    score: Optional[float] = None
    text: Optional[str] = None  # For results that include content


class SearchResponse(BaseModel):
    """Response from a web search provider."""

    results: List[SearchResult]
    request_id: Optional[str] = None
    search_type: Optional[str] = None
