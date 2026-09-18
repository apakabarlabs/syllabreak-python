.DEFAULT_GOAL := build

.PHONY: install build test-build test docs comments lint format clean

COMMENTCENSOR_VERSION ?= v0.3.2

install:
	python3 -m venv venv
	venv/bin/pip install -q -r requirements.txt
	venv/bin/pip install -q -e .
	venv/bin/pip install -q --upgrade git+https://github.com/botforge-pro/commentcensor.git@$(COMMENTCENSOR_VERSION)

clean:
	rm -rf build dist *.egg-info .pytest_cache .ruff_cache

test-build:
	venv/bin/python -m compileall -q syllabreak test_readme.py

docs:
	venv/bin/pdoc syllabreak -o build/docs

test:
	venv/bin/pytest syllabreak/
	venv/bin/pytest test_readme.py

comments:
	venv/bin/commentcensor .

lint: comments
	venv/bin/ruff check .
	venv/bin/ruff format --check .

format:
	venv/bin/ruff check --fix .
	venv/bin/ruff format .

build: lint test-build test docs
	venv/bin/python -m build --wheel
