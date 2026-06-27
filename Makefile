.PHONY: install test lint run benchmark

install:
	pip install -r requirements.txt

test:
	pytest tests/ -v

lint:
	python -m py_compile src/graph/currency_graph.py

run:
	python -m src

benchmark:
	python -m src.benchmark.runner
