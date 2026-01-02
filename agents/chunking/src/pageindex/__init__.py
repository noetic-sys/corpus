"""
PageIndex package for hierarchical markdown document processing.

Adapted from VectifyAI/PageIndex for use with Anthropic Claude.
Original: https://github.com/VectifyAI/PageIndex
"""

from .models import (
    DocumentTree,
    MarkdownHeader,
    PageIndexConfig,
    TreeNode,
)
from .page_index_md import markdown_to_tree
from .utils import (
    assign_node_ids,
    count_tokens,
    flatten_tree,
    get_leaf_nodes,
    print_tree_toc,
)

__all__ = [
    # Main function
    "markdown_to_tree",
    # Models
    "DocumentTree",
    "MarkdownHeader",
    "PageIndexConfig",
    "TreeNode",
    # Utils
    "assign_node_ids",
    "count_tokens",
    "flatten_tree",
    "get_leaf_nodes",
    "print_tree_toc",
]
