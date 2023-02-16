.PHONY: all clean

all: linux-minimal-wamr profiling-opcodes

.PHONY: linux-minimal-wamr
linux-minimal-wamr: linux-minimal-wamr/build/runtime
linux-minimal-wamr/build/runtime:
	make -C linux-minimal-wamr

.PHONY: profiling-opcodes
profiling-opcodes: profiling-opcodes/build/runtime
profiling-opcodes/build/runtime:
	make -C profiling-opcodes

clean:
	make -C linux-minimal-wamr clean
	make -C profiling-opcodes clean
