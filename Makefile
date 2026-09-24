.PHONY: setup up down test lint seed e2e plan apply destroy cost cost-phase quota whats-running

# ---- P0-P2: local dev -----------------------------------------------------

setup: ## Install local toolchain via mise and pre-commit hooks
	mise install
	pre-commit install
	cd apps/api && uv sync

up: ## Start the full local stack
	docker compose up --build

down: ## Stop the local stack
	docker compose down

test: ## Run unit + integration tests
	cd apps/api && uv run pytest tests/ -v

lint: ## Run all linters
	cd apps/api && uv run ruff check .
	terraform -chdir=infra/terraform/envs/dev fmt -check -recursive || true

seed: ## Generate the synthetic TRF corpus
	cd apps/api && uv run python ../../tools/generate_reports.py

e2e: ## Run Playwright E2E against local stack
	uv run pytest tests/e2e/ -v

# ---- P3+: cloud / FinOps ---------------------------------------------------

plan: ## terraform plan against dev env
	terraform -chdir=infra/terraform/envs/dev plan

apply: ## terraform apply against dev env
	terraform -chdir=infra/terraform/envs/dev apply

destroy: ## terraform destroy dev env (Tier 2/3 teardown)
	terraform -chdir=infra/terraform/envs/dev destroy

cost: ## Month-to-date spend, grouped by resource group
	az costmanagement query \
		--type ActualCost \
		--timeframe MonthToDate \
		--dataset-aggregation '{"totalCost":{"name":"PreTaxCost","function":"Sum"}}' \
		--dataset-grouping name=ResourceGroupName type=Dimension \
		--scope "/subscriptions/$$(az account show --query id -o tsv)" \
		-o table

cost-phase: ## Month-to-date spend, grouped by the `phase` tag
	az costmanagement query \
		--type ActualCost \
		--timeframe MonthToDate \
		--dataset-aggregation '{"totalCost":{"name":"PreTaxCost","function":"Sum"}}' \
		--dataset-grouping name=phase type=TagKey \
		--scope "/subscriptions/$$(az account show --query id -o tsv)" \
		-o table

quota: ## vCPU usage vs limit in westeurope
	az vm list-usage -l westeurope -o table

whats-running: ## Every project=tad resource, flagging anything that's compute
	@echo "== All project=tad resources =="
	az resource list --tag project=tad -o table
	@echo ""
	@echo "== Live AKS clusters (the dominant cost risk) =="
	az aks list -o table 2>/dev/null || echo "  (none, or not yet installed)"
