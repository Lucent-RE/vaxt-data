SHELL := /bin/bash
.DEFAULT_GOAL := help

## help — show this help
help:
	@grep -E '^## ' $(MAKEFILE_LIST) | sed 's/^## //' | column -t -s '—'

## bootstrap — create venv, install deps, copy .env template
bootstrap:
	python3 -m venv .venv
	.venv/bin/pip install --upgrade pip
	.venv/bin/pip install -r requirements.txt
	@if [ ! -f .env ]; then cp .env.example .env; echo ".env created — fill in API keys"; fi
	@echo "bootstrap complete"

## doctor — verify dev environment health
doctor:
	@echo "==> Checking python3..."
	@command -v python3 >/dev/null 2>&1 || { echo "FAIL: python3 not found"; exit 1; }
	@python3 --version
	@echo "==> Checking git..."
	@command -v git >/dev/null 2>&1 || { echo "FAIL: git not found"; exit 1; }
	@git --version
	@echo "==> Checking .env..."
	@test -f .env || { echo "WARN: .env not found — run 'cp .env.example .env'"; }
	@echo "==> All checks passed"

## validate — run all validators (exits non-zero on failure)
validate:
	@fail=0; \
	for f in scripts/validate_*.py; do \
		echo "==> $$f"; \
		python3 "$$f" || fail=1; \
	done; \
	exit $$fail

## etl — run full ETL pipeline
etl:
	python3 scripts/vaxt_runner.py

## load — load static CSVs into DuckDB
load:
	python3 scripts/load_heritage_grain.py

## export — export Airtable data to output/
export:
	python3 scripts/export_airtable_varieties.py
	python3 scripts/export_website_data.py --output-dir output

## sync — sync Airtable <-> Notion
sync:
	python3 scripts/sync_airtable_notion.py

## clean — remove generated artifacts
clean:
	rm -rf .venv
	find . -name '*.duckdb' -delete
	find . -name '*.duckdb.wal' -delete
	find . -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true
	@echo "clean complete"

.PHONY: help bootstrap doctor validate etl load export sync clean
