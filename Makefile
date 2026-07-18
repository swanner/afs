.PHONY: init validate test docs publish clean tree

init:
	python3 -m venv .venv
	.venv/bin/pip install -e .

validate:
	.venv/bin/afs validate

test:
	.venv/bin/python -m unittest discover -s tests

docs:
	@echo "Documentation build is not implemented yet."

publish:
	git status
	git add .
	git commit -m "chore: phase 2 repository structure"
	git push

tree:
	tree -a -I '.git|.venv|__pycache__|*.egg-info'

clean:
	rm -rf .venv build dist *.egg-info
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
