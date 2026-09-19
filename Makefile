.DEFAULT_GOAL := build

.PHONY: install install-tools install-analysis-tools analyze-english-endings build test-build test docs comments lint format clean

COMMENTCENSOR_VERSION ?= v0.3.2
COMMENTCENSOR_ENV = .tools/commentcensor
COMMENTCENSOR = $(COMMENTCENSOR_ENV)/bin/commentcensor
ENGLISH_ANALYSIS_ENV = .tools/english-analysis
CMUDICT_COMMIT = 74790861f652b15e4ac49015a90074ad62a27690
CMUDICT_PATH = build/cmudict-$(CMUDICT_COMMIT).dict

install:
	python3 -m venv venv
	venv/bin/pip install -q -r requirements.txt
	venv/bin/pip install -q -e .

install-tools:
	python3 -m venv $(COMMENTCENSOR_ENV)
	$(COMMENTCENSOR_ENV)/bin/pip install -q --upgrade git+https://github.com/botforge-pro/commentcensor.git@$(COMMENTCENSOR_VERSION)

install-analysis-tools:
	python3 -m venv $(ENGLISH_ANALYSIS_ENV)
	$(ENGLISH_ANALYSIS_ENV)/bin/pip install -q -r tools/requirements.txt

$(CMUDICT_PATH):
	mkdir -p build
	curl -fsSL https://raw.githubusercontent.com/cmusphinx/cmudict/$(CMUDICT_COMMIT)/cmudict.dict -o $@

analyze-english-endings: install-analysis-tools $(CMUDICT_PATH)
	PYTHONPATH=. $(ENGLISH_ANALYSIS_ENV)/bin/python tools/analyze_english_endings.py $(CMUDICT_PATH) --include-lexicon

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
	$(COMMENTCENSOR) .

lint: comments
	venv/bin/ruff check .
	venv/bin/ruff format --check .

format:
	venv/bin/ruff check --fix .
	venv/bin/ruff format .

build: lint test-build test docs
	venv/bin/python -m build
	venv/bin/python -m twine check dist/*
