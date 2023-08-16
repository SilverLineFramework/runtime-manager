.PHONY: all clean
all: build/runtime

build/runtime: build
	make -C build

build:
	mkdir build
	cmake -S . -B build -DWAMR_BUILD_PLATFORM=linux -DWAMR_BUILD_CUSTOM_NAME_SECTION=1 \
		-DWAMR_BUILD_DUMP_CALL_STACK=1 -DWAMR_BUILD_LIB_WASI_THREADS=1 \
		-DWAMR_BUILD_MEMORY_PROFILING=1 -DWAMR_BUILD_LIBC_WALI=1

clean:
	rm -r build
