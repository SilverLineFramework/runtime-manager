DIR=$(shell pwd)
PYTHON_SYS=python3
PYTHON=$(DIR)/env/bin/python
PIP=$(DIR)/env/bin/pip

ORCHESTRATOR=./services/orchestrator/manage.py

.PHONY: all env

all: env

env: env/bin/activate

env/bin/activate:
	test -d env || $(PYTHON_SYS) -m venv env
	$(PIP) install ./libsilverline
	$(PIP) install -r requirements.txt
	touch env/bin/activate

.PHONY: orchestrator
orchestrator:
	$(PYTHON) $(ORCHESTRATOR) makemigrations
	$(PYTHON) $(ORCHESTRATOR) migrate
	$(PYTHON) $(ORCHESTRATOR) runserver

.PHONY: reset
reset:
	rm -f services/orchestrator/db.sqlite3
