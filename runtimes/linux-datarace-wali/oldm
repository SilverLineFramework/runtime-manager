.PHONY: clean

SRC_CPP := access.cpp tsvd.cpp
SRC_C := optable.c
SRC_O := $(SRC_CPP:.cpp=.o)

all: $(SRC_O)

optable.o: optable.c
	gcc -O3 -c $< -o $@ 

tsvd.o: tsvd.cpp optable.o
	g++ -std=c++2a -O3 -c -fPIC $< -o $@
	g++ -std=c++2a -O3 -shared -o lib$*.so optable.o $@ libvmlib.a

access.o: access.cpp optable.o
	g++ -std=c++2a -O3 -c -fPIC $< -o $@
	g++ -std=c++2a -O3 -shared -o lib$*.so optable.o $@ libvmlib.a

%.o: %.cpp
	g++ -O3 -c -fPIC $< -o $@
	g++ -O3 -shared -o lib$*.so $@ libvmlib.a

clean:
	rm -f *.o *.so
