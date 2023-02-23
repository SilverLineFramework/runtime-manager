DIR=$(shell pwd)
SYS_PYTHON=python3

export SL_CONFIG=$(realpath config.json)
export SL_PIP=$(DIR)/env/bin/pip
export SL_PYTHON=$(DIR)/env/bin/python
export SL_DATA=$(DIR)/data

.PHONY: all env

all: env

env: env/bin/activate

env/bin/activate:
	test -d env || $(SYS_PYTHON) -m venv env
	$(SL_PIP) install ./libsilverline
	$(SL_PIP) install -r requirements.txt
	make -C services deps
	touch env/bin/activate

orchestrator:
	make -C services/orchestrator

profile:
	make -C services/profile

start:
	make -C services start

stop:
	make -C services stop

WAMRC_PATH=runtimes/common/wasm-micro-runtime/wamr-compiler
wamrc: 
	ln -s $(WAMRC_PATH)/build/wamrc .
