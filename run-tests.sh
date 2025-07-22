#!/usr/bin/env bash -e

uv run pytest --cov=write_description_metadata --cov-branch --cov-report=term-missing
