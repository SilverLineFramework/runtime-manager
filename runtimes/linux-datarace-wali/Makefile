.PHONY: all build clean
all: build/runtime

build/runtime: build
	make -C build

build:
	mkdir -p build
	cmake -S . -B build

clean:
	rm -rf build
