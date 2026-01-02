"""Cache key generators for QA package repositories."""

from typing import Optional


def answer_set_by_matrix_cell_key(
    matrix_cell_id: int, company_id: Optional[int] = None
) -> str:
    """Generate cache key for answer sets by matrix cell."""
    return f"matrix_cell:{matrix_cell_id}:company:{company_id}:answer_sets"


def answer_set_current_by_matrix_cell_key(
    matrix_cell_id: int, company_id: Optional[int] = None
) -> str:
    """Generate cache key for current answer set by matrix cell."""
    return f"matrix_cell:{matrix_cell_id}:company:{company_id}:current_answer_set"


def answers_by_answer_set_key(
    answer_set_id: int, company_id: Optional[int] = None
) -> str:
    """Generate cache key for answers by answer set."""
    return f"answer_set:{answer_set_id}:company:{company_id}:answers"


def citation_sets_by_answer_key(
    answer_id: int, company_id: Optional[int] = None
) -> str:
    """Generate cache key for citation sets by answer."""
    return f"answer:{answer_id}:company:{company_id}:citation_sets"


def citation_set_by_id_key(
    citation_set_id: int, company_id: Optional[int] = None
) -> str:
    """Generate cache key for citation set by ID."""
    return f"citation_set:{citation_set_id}:company:{company_id}"


def citations_by_set_key(citation_set_id: int, company_id: Optional[int] = None) -> str:
    """Generate cache key for citations by set."""
    return f"citation_set:{citation_set_id}:company:{company_id}:citations"


def citations_by_document_key(
    document_id: int, company_id: Optional[int] = None
) -> str:
    """Generate cache key for citations by document."""
    return f"document:{document_id}:company:{company_id}:citations"
