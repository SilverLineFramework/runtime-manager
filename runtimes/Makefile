.PHONY: all clean

all: bin bin/linux-minimal-wamr bin/profiling-opcodes bin/iwasm


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


WAMR_IWASM=common/wasm-micro-runtime/product-mini/platforms/linux
bin/iwasm: $(WAMR_IWASM)/build/iwasm
	ln -s ../$(WAMR_IWASM)/build/iwasm bin/iwasm

$(WAMR_IWASM)/build/iwasm:
	mkdir -p $(WAMR_IWASM)/build
	cd $(WAMR_IWASM)/build; cmake ..
	make -C $(WAMR_IWASM)/build


clean:
	make -C linux-minimal-wamr clean
	make -C profiling-opcodes clean
	rm -r $(WAMR_IWASM)/build

	rm -r bin
