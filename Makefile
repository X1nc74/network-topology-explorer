PYTHON ?= python3
VENV ?= .venv
VENV_PYTHON = $(VENV)/bin/python

install:
	$(PYTHON) -m venv $(VENV)
	$(VENV_PYTHON) -m pip install -r requirements.txt

run:
	sudo $(VENV_PYTHON) main.py targets.txt

serve:
	$(VENV_PYTHON) -m http.server 8000 --bind 127.0.0.1

test:
	$(VENV_PYTHON) -m unittest discover -s tests -p 'test_*.py' -v
	node --test tests/frontend.test.mjs

clean:
	rm -f output/*.json output/*.txt

.PHONY: install run serve test clean
