in integration/ you maynot mock out services, except for the axiom exorter begin span. this is how we test on the real hardware we are running on
in unit/ you may mock out anything external, such as message passing, external ai calls, but you may NEVER mock database interactions. ever.

## Mocking Patterns for Claude

### How to Mock External Providers/Services
1. **Use context managers in fixtures** - Don't use @patch on class decorators
2. **Mock at import location** - patch where the class is imported, not where it's defined
3. **Use pytest fixtures to create services** - like DocumentService example

Example working pattern:
```python
@pytest.fixture
def document_service(test_db, mock_storage, mock_bloom_filter, mock_search_provider):
    """Create a DocumentService instance with mocked providers."""
    with patch(
        "packages.documents.services.document_service.get_storage",
        return_value=mock_storage,
    ), patch(
        "packages.documents.services.document_service.get_bloom_filter_provider",
        return_value=mock_bloom_filter,
    ), patch(
        "packages.documents.services.document_service.get_document_search_provider",
        return_value=mock_search_provider,
    ):
        return DocumentService(test_db)
```

### For Audio Extractors
- Mock GoogleSpeechToTextProvider and OpenAIWhisperProvider at their import location
- Mock get_storage factory function
- Use context managers in fixtures, not class decorators
