PYTHON ?= python3

.PHONY: compile test example examples validate validate-docker docs-lint

compile:
	$(PYTHON) -m py_compile app.py fea_engine/*.py templates/*.py tests/*.py tools/*.py validation/public_formula_checks/*.py validation/mesh_convergence/*.py validation/roark_formulas/*.py

docs-lint:
	$(PYTHON) tools/check_markdown_links.py

test: compile
	pytest -q
	$(MAKE) docs-lint

example:
	./examples/minimal/run.sh

examples:
	./examples/smoke_test.sh

validate:
	$(PYTHON) tools/run_validation.py

validate-docker:
	$(PYTHON) tools/run_validation.py --include-docker
