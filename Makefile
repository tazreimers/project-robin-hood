.PHONY: bootstrap dev test lint format reset seed docs

bootstrap:
	@./scripts/bootstrap.sh

dev:
	@./scripts/dev.sh

test:
	@./scripts/test.sh

lint:
	@./scripts/lint.sh

format:
	@./scripts/format.sh

reset:
	@./scripts/reset_local.sh

seed:
	@./scripts/seed_local.sh

docs:
	@printf "Documentation index:\n"
	@printf "  docs/getting-started.md\n"
	@printf "  docs/architecture.md\n"
	@printf "  docs/backend.md\n"
	@printf "  docs/frontend.md\n"
	@printf "  docs/testing.md\n"
