"""
Markdown document processing for PageIndex.

Extracts hierarchical structure from markdown headers and builds tree.
"""

import asyncio
import os
import re
from pathlib import Path
from typing import List, Tuple

from .models import DocumentTree, MarkdownHeader, PageIndexConfig, TreeNode
from .utils import assign_node_ids, count_tokens, generate_node_summary


def extract_headers_from_markdown(markdown_content: str) -> Tuple[List[MarkdownHeader], List[str]]:
    """
    Extract all markdown headers from content.

    Args:
        markdown_content: Full markdown document text

    Returns:
        Tuple of (list of headers, list of all lines)
    """
    header_pattern = r"^(#{1,6})\s+(.+)$"
    code_block_pattern = r"^```"
    headers: List[MarkdownHeader] = []

    lines = markdown_content.split("\n")
    in_code_block = False

    for line_num, line in enumerate(lines, 1):
        stripped = line.strip()

        # Toggle code block state
        if re.match(code_block_pattern, stripped):
            in_code_block = not in_code_block
            continue

        # Skip empty lines or lines in code blocks
        if not stripped or in_code_block:
            continue

        # Match headers
        match = re.match(header_pattern, stripped)
        if match:
            level = len(match.group(1))
            title = match.group(2).strip()
            # Create with placeholder text - will be filled in next step
            headers.append(
                MarkdownHeader(title=title, line_num=line_num, level=level, text="")
            )

    return headers, lines


def extract_text_for_headers(
    headers: List[MarkdownHeader], markdown_lines: List[str]
) -> List[MarkdownHeader]:
    """
    Extract text content between headers.

    Args:
        headers: List of headers with line numbers
        markdown_lines: All lines from document

    Returns:
        Headers with text content populated
    """
    for i, header in enumerate(headers):
        start_line = header.line_num - 1

        # End is start of next header, or EOF
        if i + 1 < len(headers):
            end_line = headers[i + 1].line_num - 1
        else:
            end_line = len(markdown_lines)

        header.text = "\n".join(markdown_lines[start_line:end_line]).strip()

    return headers


def calculate_token_counts(headers: List[MarkdownHeader], model: str) -> List[MarkdownHeader]:
    """
    Calculate token count for each header including all its children.

    Args:
        headers: List of headers with text
        model: Model name for tokenization

    Returns:
        Headers with text_token_count populated
    """

    def find_children_indices(parent_idx: int, parent_level: int) -> List[int]:
        """Find all descendant indices."""
        children = []
        for i in range(parent_idx + 1, len(headers)):
            if headers[i].level <= parent_level:
                break
            children.append(i)
        return children

    # Process from end to beginning
    for i in range(len(headers) - 1, -1, -1):
        header = headers[i]
        children_indices = find_children_indices(i, header.level)

        # Combine node's text with all children's text
        combined_text = header.text
        for child_idx in children_indices:
            child_text = headers[child_idx].text
            if child_text:
                combined_text += "\n" + child_text

        header.text_token_count = count_tokens(combined_text, model)

    return headers


def merge_small_nodes(
    headers: List[MarkdownHeader], min_tokens: int, model: str
) -> List[MarkdownHeader]:
    """
    Merge nodes with token count below threshold into parents.

    Args:
        headers: List of headers with token counts
        min_tokens: Minimum tokens before merging
        model: Model name for re-counting

    Returns:
        Filtered list with small nodes merged
    """

    def find_children_indices(parent_idx: int, parent_level: int) -> List[int]:
        """Find all descendant indices."""
        children = []
        for i in range(parent_idx + 1, len(headers)):
            if headers[i].level <= parent_level:
                break
            children.append(i)
        return children

    indices_to_remove = set()

    # Process from end to beginning
    for i in range(len(headers) - 1, -1, -1):
        if i in indices_to_remove:
            continue

        header = headers[i]

        if (header.text_token_count or 0) < min_tokens:
            # Merge children into this node
            children_indices = find_children_indices(i, header.level)

            merged_text = header.text
            for child_idx in sorted(children_indices):
                if child_idx not in indices_to_remove:
                    child_text = headers[child_idx].text
                    if child_text.strip():
                        if merged_text and not merged_text.endswith("\n"):
                            merged_text += "\n\n"
                        merged_text += child_text
                    indices_to_remove.add(child_idx)

            header.text = merged_text
            header.text_token_count = count_tokens(merged_text, model)

    # Filter out removed nodes
    return [h for i, h in enumerate(headers) if i not in indices_to_remove]


def build_tree_from_headers(headers: List[MarkdownHeader]) -> List[TreeNode]:
    """
    Build hierarchical tree from flat header list.

    Args:
        headers: Flat list of headers with levels

    Returns:
        Root-level tree nodes
    """
    if not headers:
        return []

    stack: List[Tuple[TreeNode, int]] = []
    root_nodes: List[TreeNode] = []
    node_counter = 1

    for header in headers:
        # Create tree node
        tree_node = TreeNode(
            title=header.title,
            node_id=str(node_counter).zfill(4),
            text=header.text,
            line_num=header.line_num,
            nodes=[],
        )
        node_counter += 1

        # Pop stack until we find the parent
        while stack and stack[-1][1] >= header.level:
            stack.pop()

        # Attach to parent or add to roots
        if not stack:
            root_nodes.append(tree_node)
        else:
            parent_node, _ = stack[-1]
            parent_node.nodes.append(tree_node)

        stack.append((tree_node, header.level))

    return root_nodes


async def generate_summaries_for_tree(
    nodes: List[TreeNode], config: PageIndexConfig
) -> List[TreeNode]:
    """
    Generate AI summaries for all nodes in tree.

    Args:
        nodes: Tree nodes
        config: PageIndex configuration

    Returns:
        Nodes with summaries populated
    """
    tasks = []

    for node in nodes:
        tasks.append(generate_node_summary(node.text, config.model, config.summary_token_threshold))

    summaries = await asyncio.gather(*tasks)

    for node, summary in zip(nodes, summaries):
        if not node.nodes:
            # Leaf node
            node.summary = summary
        else:
            # Parent node
            node.prefix_summary = summary

        # Recursively process children
        if node.nodes:
            node.nodes = await generate_summaries_for_tree(node.nodes, config)

    return nodes


async def markdown_to_tree(
    md_path: Path,
    config: PageIndexConfig,
) -> DocumentTree:
    """
    Convert markdown document to hierarchical tree structure.

    Args:
        md_path: Path to markdown file
        config: PageIndex configuration

    Returns:
        Complete document tree
    """
    # Read markdown
    with open(md_path, "r", encoding="utf-8") as f:
        markdown_content = f.read()

    print("Extracting headers from markdown...")
    headers, markdown_lines = extract_headers_from_markdown(markdown_content)

    print("Extracting text content for headers...")
    headers = extract_text_for_headers(headers, markdown_lines)

    # Optional: thinning (merging small nodes)
    if config.enable_thinning:
        print("Calculating token counts...")
        headers = calculate_token_counts(headers, config.model)

        print("Merging small nodes...")
        headers = merge_small_nodes(headers, config.min_token_threshold, config.model)

    # Build tree
    print("Building tree structure...")
    tree_nodes = build_tree_from_headers(headers)

    # Assign node IDs
    if config.include_node_ids:
        assign_node_ids(tree_nodes)

    # Generate summaries
    if config.generate_summaries:
        print("Generating summaries...")
        tree_nodes = await generate_summaries_for_tree(tree_nodes, config)

    # Remove text if not requested
    if not config.include_text:

        def remove_text(nodes: List[TreeNode]) -> None:
            for node in nodes:
                node.text = ""
                if node.nodes:
                    remove_text(node.nodes)

        remove_text(tree_nodes)

    # Build final document tree
    doc_name = os.path.splitext(os.path.basename(md_path))[0]

    return DocumentTree(
        doc_name=doc_name,
        doc_description=None,  # TODO: implement if config.generate_document_description
        structure=tree_nodes,
    )
