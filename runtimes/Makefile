.PHONY: all clean
.PHONY: bin/linux-datarace-wali

all: bin/linux-minimal-wamr bin/profiling-opcodes bin/iwasm bin/wasm3

bin:
	mkdir -p bin

# Aliases for installed runtimes
alias: bin/wasmtime bin/wasmer bin/wasmedge bin/wasmedgec

bin/wasmtime: bin ~/.wasmtime/bin/wasmtime
	cd bin; ln -s ~/.wasmtime/bin/wasmtime wasmtime

bin/wasmedge: bin ~/.wasmedge/bin/wasmedge
	cd bin; ln -s ~/.wasmedge/bin/wasmedge wasmedge

bin/wasmedgec: bin ~/.wasmedge/bin/wasmedgec
	cd bin; ln -s ~/.wasmedge/bin/wasmedgec wasmedgec

bin/wasmer: bin ~/.wasmer/bin/wasmer
	cd bin; ln -s ~/.wasmer/bin/wasmer wasmer

# Minimal WAMR-based runtime
bin/linux-minimal-wamr: bin
	make -C linux-minimal-wamr
	ln -sf ../linux-minimal-wamr/build/runtime bin/linux-minimal-wamr

# Data-race WAMR-WALI runtime
bin/linux-datarace-wali: bin
	make -C linux-datarace-wali
	ln -sf ../linux-datarace-wali/build/runtime-access $@-access
	ln -sf ../linux-datarace-wali/build/runtime-tsvd $@-tsvd

# Opcode profiling runtime
bin/profiling-opcodes: bin 
	make -C profiling-opcodes
	ln -sf ../profiling-opcodes/build/runtime bin/profiling-opcodes

# Wasm3
bin/wasm3: bin wasm3/build/wasm3
	ln -s ../wasm3/build/wasm3 bin/wasm3

wasm3/build/wasm3:
	mkdir -p wasm3/build
	cd wasm3/build; cmake ..
	make -C wasm3/build

# WAMR (WALI edition)
WAMR=wasm-micro-runtime-wali/product-mini/platforms/linux
bin/iwasm: bin $(WAMR)/build/iwasm
	ln -s ../$(WAMR)/build/iwasm bin/iwasm

$(WAMR)/build/iwasm:
	mkdir -p $(WAMR)/build
	cd $(WAMR)/build; cmake .. -DWAMR_BUILD_PLATFORM=linux \
		-DWAMR_BUILD_CUSTOM_NAME_SECTION=1 \
		-DWAMR_BUILD_DUMP_CALL_STACK=1 -DWAMR_BUILD_LIB_WASI_THREADS=1 \
		-DWAMR_BUILD_MEMORY_PROFILING=1 -DWAMR_BUILD_LIBC_WALI=1
	make -C $(WAMR)/build

WAMRC=wasm-micro-runtime/wamr-compiler
bin/wamrc: bin $(WAMRC)
	ln -s ../$(WAMRC)/build/wamrc bin/wamrc

# This step is super not automated. You might have to manually delete the
# build files and retry if it fails the first time. It also may be necessary
# to change -DLLVM_CCACHE_BUILD:BOOL=OFF in
# wasm-micro-runtime/build-scripts/build_llvm.py.
$(WAMRC)/build/wamrc:
	cd $(WAMRC); ./build_llvm.sh
	mkdir -p $(WAMRC)/build
	cd $(WAMRC)/build; cmake ..


clean:
	make -C linux-minimal-wamr clean
	make -C profiling-opcodes clean
	rm -rf $(WAMR)/build
	rm -rf wasm3/build
	rm -rf bin


.PHONY: typecheck
typecheck:
	python -m mypy linux_minimal.py
	python -m mypy linux_benchmarking.py
	python -m mypy linux_benchmarking_interference.py
