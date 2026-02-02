---
description: Run all checks (linting, tests, types) to ensure code quality.
---

// turbo-all
1. Run ruff check
```bash
ruff check .
```

2. Check formatting
```bash
black --check .
```

3. Run type checking
```bash
mypy src tests
```

4. Run tests
```bash
pytest -q
```

5. Or Run all
```bash
ruff check . && black --check . && mypy src tests && pytest -q
```