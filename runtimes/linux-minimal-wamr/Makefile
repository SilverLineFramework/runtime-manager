.PHONY: all clean
all: build/runtime

build/runtime: build
	make -C build

build:
	mkdir build
	cmake -S . -B build

clean:
	rm -rf build
