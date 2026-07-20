# Contributing Guidelines

## Commit message convention

All commits must follow the Conventional Commits format in English:

- `feat(scope): short summary`
- `fix(scope): short summary`
- `docs(scope): short summary`
- `refactor(scope): short summary`
- `chore(scope): short summary`

Examples:
- `feat(storage): add database-backed storage bootstrap`
- `fix(api): handle storage initialization fallback`
- `docs(openspec): add migration proposal for qdrant and postgres`

## Pull request convention

Pull requests should be opened with the following structure in English:

### Title
`feat(scope): short summary`

### Description
- What changed
- Why it changed
- How it was verified
- Any follow-up items

### Checklist
- [ ] Code compiles or relevant checks passed
- [ ] Documentation updated where needed
- [ ] Changes are scoped and reversible

## Documentation convention

All project documentation and developer-facing docs should be written in English.
This includes:
- README files
- OpenSpec proposal/design/spec/task documents
- inline comments for new developer-facing code where practical

## Working rules

- Keep changes focused and atomic.
- Prefer small, reviewable commits.
- Update documentation when behavior or setup changes.
- Use English for commit messages, PR titles, and documentation.
- Always checkout to a feature branch (e.g. `feature/...`) before making any code changes or generating proposals. Never work directly on `main`.
