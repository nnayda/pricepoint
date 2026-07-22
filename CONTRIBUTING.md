# Contributing to PricePoint

Thanks for your interest! This is a personal project, but issues and PRs are
welcome.

## Before you start

- For anything beyond a small fix, **open an issue first** so we can agree on
  the approach before you invest time.

## Development setup

```sh
uv sync --frozen                 # backend deps (Python 3.12 via uv)
make frontend-install            # frontend deps
cp .env.example .env
make up-all                      # full local stack via Docker Compose
```

See the [README](README.md#development) for the day-to-day commands.

## Pull requests

- Keep PRs focused: one logical change per PR.
- PR titles must follow [Conventional Commits](https://www.conventionalcommits.org/)
  (`feat: …`, `fix: …`, `docs: …`, `chore: …`, `refactor: …`, `test: …`,
  `ci: …`, `perf: …`, `build: …`). CI enforces this; PRs are squash-merged, so
  the PR title becomes the commit message and drives
  [release-please](https://github.com/googleapis/release-please) versioning.
- Add tests for behavior you add or change.
- CI must be green. Run everything locally before pushing:

```sh
make lint && uv run mypy src/ && make test-unit
cd frontend && npm run lint && npm run format:check && npm test && npm run build
helm lint helm/pricepoint/
```

Integration tests (`make test-integration`) use Docker/testcontainers and run
locally rather than in CI.

## Code style

- **Python:** Ruff for lint + format (100-char lines, py311 target), mypy for
  types. No manual style debates — Ruff is the arbiter.
- **TypeScript:** ESLint + Prettier (`npm run lint`, `npm run format`).
- **Migrations:** generated with `make migration MSG="..."`; never edit an
  applied migration.

## Reporting bugs and requesting features

Use the issue templates. For security vulnerabilities, follow
[SECURITY.md](SECURITY.md) instead of opening a public issue.

## Licensing of contributions

PricePoint is [MIT-licensed](LICENSE). By submitting a contribution you agree
it is your own work and licensed under the same terms.

## Code of conduct

This project follows the [Contributor Covenant](CODE_OF_CONDUCT.md). Be kind.
