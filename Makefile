DIR=$(shell pwd)
SYS_PYTHON=python3

ifdef MINIMAL
REQUIREMENTS=requirements-runtime.txt
else
REQUIREMENTS=requirements.txt; \
make -C services/orchestrator deps; \
make -C services/profile deps
endif

export SL_CONFIG=$(realpath config.json)
export SL_PIP=$(DIR)/env/bin/pip
export DEV_PIP=pip
export SL_PYTHON=$(DIR)/env/bin/python
export SL_DATA=$(DIR)/data

.PHONY: all env env-dev

all: env

env: env/bin/activate

env/bin/activate:
	test -d env || $(SYS_PYTHON) -m venv env
	$(SL_PIP) install ./libsilverline
	$(SL_PIP) install -r $(REQUIREMENTS)
	touch env/bin/activate

orchestrator:
	make -C services/orchestrator

profile:
	make -C services/profile

start:
	make -C services/orchestrator start
	make -C services/profile start

stop:
	make -C services/orchestrator stop
	make -C services/profile stop

reset:
	make -C services/orchestrator reset

typecheck:
	python -m mypy start.py
	python -m mypy manage.py
	python -m mypy services/profile/profile.py
	cd services/orchestrator; python -m mypy .
	make -C runtimes typecheck
