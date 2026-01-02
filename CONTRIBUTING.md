# Contributing to Corpus

Thanks for your interest in contributing to Corpus.

## Getting Started

1. Fork the repository
2. Clone your fork
3. Create a branch for your changes
4. Make your changes
5. Run tests and linting
6. Submit a pull request

## Development Setup

See [README.md](README.md) for local development setup.

## Code Style

### Python (Backend)

- Use [Ruff](https://github.com/astral-sh/ruff) for linting and formatting
- Follow existing code patterns
- Add type hints

```bash
cd backend
poetry run ruff check .
poetry run ruff format .
```

### TypeScript (Frontend)

- Use ESLint and Prettier
- Follow existing component patterns

```bash
cd vite
npm run lint
npm run format
```

## Testing

```bash
# Backend tests
cd backend
poetry run pytest

# Frontend tests
cd vite
npm run test
```

## Pull Requests

- Keep PRs focused on a single change
- Include tests for new functionality
- Update documentation if needed
- Reference any related issues

## Issues

- Search existing issues before creating new ones
- Use issue templates when available
- Provide reproduction steps for bugs

## License

By contributing, you agree that your contributions will be licensed under AGPL-3.0.
