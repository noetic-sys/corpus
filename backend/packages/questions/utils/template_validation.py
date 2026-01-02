import re
from typing import List
from packages.matrices.models.domain.matrix_enums import MatrixType


class TemplateValidationResult:
    def __init__(
        self,
        is_valid: bool = True,
        errors: List[str] = None,
        warnings: List[str] = None,
    ):
        self.is_valid = is_valid
        self.errors = errors or []
        self.warnings = warnings or []


def validate_template_variables(
    text: str, matrix_type: MatrixType, available_variables: List[str] = None
) -> TemplateValidationResult:
    """
    Validate template variables in text to ensure they are properly formed.

    Args:
        text: The text containing potential template variables
        matrix_type: Type of matrix (determines if document placeholders are allowed)
        available_variables: List of available variable names to check against

    Returns:
        TemplateValidationResult with validation status and any errors/warnings
    """
    errors = []
    warnings = []
    available_variables = available_variables or []

    # First, find all valid template variables to exclude them from error checking
    # Pattern for name-based template variables: ${{variable_name}}
    name_template_pattern = r"\$\{\{([a-zA-Z_][a-zA-Z0-9_]*)\}\}"
    # Pattern for ID-based template variables: #{{123}}
    id_template_pattern = r"#\{\{(\d+)\}\}"
    # Pattern for document placeholder variables: @{{LEFT}}, @{{RIGHT}}
    doc_placeholder_pattern = r"@\{\{(LEFT|RIGHT)\}\}"

    name_matches = list(re.finditer(name_template_pattern, text))
    id_matches = list(re.finditer(id_template_pattern, text))
    doc_placeholder_matches = list(re.finditer(doc_placeholder_pattern, text))

    valid_template_strings = (
        [match.group(0) for match in name_matches]
        + [match.group(0) for match in id_matches]
        + [match.group(0) for match in doc_placeholder_matches]
    )

    # Create a version of text with valid templates replaced with placeholders
    text_for_validation = text
    for i, valid_template in enumerate(valid_template_strings):
        text_for_validation = text_for_validation.replace(
            valid_template, f"__VALID_TEMPLATE_{i}__", 1
        )

    # Now check for any remaining invalid patterns involving $ and {}
    invalid_patterns = [
        # Any $ followed by non-digit, non-space (but not forming valid template syntax)
        (
            r"\$[^0-9\s#{]",
            lambda m: f'Invalid dollar sign usage: "{m}" - use "${{{{variable}}}}" or "#{{{{id}}}}" for template variables or "$123" for currency',
        ),
        # Specific malformed patterns
        (
            r"\$[a-zA-Z_][a-zA-Z0-9_]*\}",
            lambda m: f'Invalid template syntax: "{m}" - use "${{{{ {m[1:-1]} }}}}" instead',
        ),
        (
            r"\$\{[a-zA-Z_][a-zA-Z0-9_]*\}",
            lambda m: f'Invalid template syntax: "{m}" - use "${{{{ {m[2:-1]} }}}}" instead',
        ),
        (
            r"\$\{[a-zA-Z_][a-zA-Z0-9_]*$",
            lambda m: f'Incomplete template variable: "{m}" - should be "${{{{ {m[2:]} }}}}"',
        ),
        (
            r"\$\{\{[a-zA-Z_][a-zA-Z0-9_]*$",
            lambda m: f'Incomplete template variable: "{m}" - missing closing "}}}}"',
        ),
        (
            r"\$\{\{[a-zA-Z_][a-zA-Z0-9_]*\}$",
            lambda m: f'Malformed template variable: "{m}" - should end with "}}}}" not "}}"',
        ),
        (
            r"\{\{[a-zA-Z_][a-zA-Z0-9_]*\}\}",
            lambda m: f'Missing dollar sign: "{m}" - should be "${m}"',
        ),
        # Any remaining $ followed by {
        (
            r"\$\{",
            lambda m: f'Invalid template syntax: "{m}" - use "${{{{variable}}}}" or "#{{{{id}}}}" for template variables',
        ),
        # Any } that might be stray (not preceded by }})
        (
            r"(?<!\}\})\}(?!\})",
            lambda m: 'Stray closing brace "}" - check your template variable syntax',
        ),
    ]

    for pattern, message_func in invalid_patterns:
        matches = re.findall(pattern, text_for_validation)
        for match in matches:
            errors.append(message_func(match))

    # Check if valid name-based variables exist in available variables - treat as ERROR not warning
    # Note: We don't validate ID-based variables as they reference IDs directly
    if available_variables:
        for match in name_matches:
            variable_name = match.group(1)
            if variable_name not in available_variables:
                errors.append(
                    f'Template variable "{variable_name}" is not defined in this matrix'
                )

    # Validate document placeholders based on matrix type
    placeholders = [match.group(1) for match in doc_placeholder_matches]
    has_left = "LEFT" in placeholders
    has_right = "RIGHT" in placeholders
    has_any_placeholder = has_left or has_right

    is_correlation = matrix_type in (
        MatrixType.CROSS_CORRELATION,
        MatrixType.GENERIC_CORRELATION,
    )

    if not is_correlation and has_any_placeholder:
        # Standard matrix cannot have document placeholders
        errors.append(
            "Document placeholders @{{LEFT}} and @{{RIGHT}} can only be used in correlation matrices"
        )
    elif is_correlation:
        # Correlation matrix must have BOTH placeholders
        if not has_left or not has_right:
            errors.append(
                "Correlation matrix questions must contain both @{{LEFT}} and @{{RIGHT}} placeholders"
            )

    return TemplateValidationResult(
        is_valid=len(errors) == 0, errors=errors, warnings=warnings
    )


def extract_template_variable_names(text: str) -> List[str]:
    """Extract all valid template variable names from text."""
    valid_template_pattern = r"\$\{\{([a-zA-Z_][a-zA-Z0-9_]*)\}\}"
    return re.findall(valid_template_pattern, text)


def extract_template_variable_ids(text: str) -> List[int]:
    """Extract all valid template variable IDs from text."""
    id_template_pattern = r"#\{\{(\d+)\}\}"
    matches = re.findall(id_template_pattern, text)
    return [int(match) for match in matches]


def extract_document_placeholders(text: str) -> List[str]:
    """Extract all document placeholder roles from text (LEFT, RIGHT)."""
    doc_placeholder_pattern = r"@\{\{(LEFT|RIGHT)\}\}"
    return re.findall(doc_placeholder_pattern, text)


def has_document_placeholders(text: str) -> bool:
    """Check if text contains any document placeholders."""
    doc_placeholder_pattern = r"@\{\{(LEFT|RIGHT)\}\}"
    return bool(re.search(doc_placeholder_pattern, text))
