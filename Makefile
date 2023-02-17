DIR=$(shell pwd)
PYTHON_SYS=python3
PYTHON=$(DIR)/env/bin/python
PIP=$(DIR)/env/bin/pip

.PHONY: all env

all: env

env: env/bin/activate

env/bin/activate:
	test -d env || $(PYTHON_SYS) -m venv env
	$(PIP) install ./libsilverline
	$(PIP) install -r requirements.txt
	touch env/bin/activate
