.PHONY: setup data stats test

setup:
	uv sync --locked 

data: 
	uv run python -m auspex.parser_nasa -j -a
	uv run python -m auspex.sessionize -j -a

stats:
	uv run python -m auspex.stats -j -a

test:
	uv run pytest -q