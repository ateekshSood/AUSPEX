.PHONY: setup data stats test baselines

setup:
	uv sync --locked 

data: 
	uv run python -m auspex.parser_nasa -j -a
	uv run python -m auspex.sessionize -j -a
	uv run python -m auspex.vocab

baselines:
	uv run python -m auspex.harness.replay -k
	
stats:
	uv run python -m auspex.stats -j -a

test:
	uv run pytest -q

