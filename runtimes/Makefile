.PHONY: all clean

all: bin bin/linux-minimal-wamr bin/profiling-opcodes bin/iwasm bin/wasm3 bin/iwasm-wali


bin:
	mkdir -p bin


bin/linux-minimal-wamr: linux-minimal-wamr/build/runtime
	ln -s ../linux-minimal-wamr/build/runtime bin/linux-minimal-wamr

linux-minimal-wamr/build/runtime:
	make -C linux-minimal-wamr


bin/profiling-opcodes: profiling-opcodes/build/runtime
	ln -s ../profiling-opcodes/build/runtime bin/profiling-opcodes

profiling-opcodes/build/runtime:
	make -C profiling-opcodes


bin/wasm3: common/wasm3/build/wasm3
	ln -s ../common/wasm3/build/wasm3 bin/wasm3

common/wasm3/build/wasm3:
	mkdir -p common/wasm3/build
	cd common/wasm3/build; cmake ..
	make -C common/wasm3/build


WAMR_IWASM=common/wasm-micro-runtime/product-mini/platforms/linux
bin/iwasm: $(WAMR_IWASM)/build/iwasm
	ln -s ../$(WAMR_IWASM)/build/iwasm bin/iwasm

$(WAMR_IWASM)/build/iwasm:
	mkdir -p $(WAMR_IWASM)/build
	cd $(WAMR_IWASM)/build; cmake ..
	make -C $(WAMR_IWASM)/build


WAMR_WALI=common/wasm-micro-runtime-wali/product-mini/platforms/linux
bin/iwasm-wali: $(WAMR_WALI)/build/iwasm
	ln -s ../$(WAMR_WALI)/build/iwasm bin/iwasm-wali

$(WAMR_WALI)/build/iwasm:
	mkdir -p $(WAMR_WALI)/build
	cd $(WAMR_WALI)/build; cmake .. -DWAMR_BUILD_PLATFORM=linux \
		-DWAMR_BUILD_CUSTOM_NAME_SECTION=1 \
		-DWAMR_BUILD_DUMP_CALL_STACK=1 -DWAMR_BUILD_LIB_WASI_THREADS=1 \
		-DWAMR_BUILD_MEMORY_PROFILING=1 -DWAMR_BUILD_LIBC_WALI=1
	make -C $(WAMR_WALI)/build


clean:
	make -C linux-minimal-wamr clean
	make -C profiling-opcodes clean
	rm -r $(WAMR_IWASM)/build

	rm -r bin


.PHONY: typecheck
typecheck:
	python -m mypy linux_minimal.py
	python -m mypy linux_benchmarking.py
	python -m mypy linux_benchmarking_interference.py
