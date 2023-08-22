## Pitot

Matrix:
```sh
hc benchmark -f `hc index -d wasm -p benchmarks` --engine iwasm wasmedge wasmtime wasmer-cranelift wasmer-singlepass wasmer-llvm
hc benchmark -f `hc index -d wasm -p benchmarks -r wasm=aot` --engine iwasm-aot
hc benchmark -f `hc index -d wasm -p benchmarks -r wasm/=native/` --engine native
hc benchmark -f `hc index -d wasm -p benchmarks -r wasm/=aot-wasmedge/` --engine wasmedge-aot
```

Interference:
```sh
hc benchmark -f `hc index -d wasm -p benchmarks -s -t 2` --limit 30 --engine iwasm wasmedge wasmtime wasmer-cranelift wasmer-singlepass wasmer-llvm
```

Note:
- Change:
    - iwasm -> iwasm-i; iwasm-aot -> iwasm-a;
    - wasmtime -> wasmtime-j
    - wasmer-cranelift -> wasmer-j-cl; wasmer-llvm -> wasmer-j-ll; wasmer-singlepass -> wasmer-j-sp;
    - wasmedge -> wasmedge-i; wasmedge-aot -> wasmedge-a

## Anemos

Data dependent:


hc benchmark -f wasm/python.wasm --engine iwasm-a wasmer-a-ll wasmer-a-cl wasmtime-a --limit 300 --repeat 10000 --argv data/python/parametric/b_array.py
