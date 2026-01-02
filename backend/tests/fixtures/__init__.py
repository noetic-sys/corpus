# Test data and fixtures


SAMPLE_COMPANY_DATA = {
    "name": "Test Company",
}
# Sample workspace data
SAMPLE_WORKSPACE_DATA = {
    "name": "Test Workspace",
    "description": "A test workspace for organizing matrices",
}

# Sample matrix data (Note: workspace_id will be added dynamically in tests)
SAMPLE_MATRIX_DATA = {
    "name": "Test Matrix",
    "description": "A test matrix for document Q&A",
}

# Sample question data
SAMPLE_QUESTION_DATA = {"question_text": "What is the main topic of this document?"}

# Sample PDF content for testing
SAMPLE_PDF_CONTENT = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\nendobj\nxref\n0 4\n0000000000 65535 f\n0000000009 00000 n\n0000000058 00000 n\n0000000115 00000 n\ntrailer\n<< /Size 4 /Root 1 0 R >>\nstartxref\n174\n%%EOF"
