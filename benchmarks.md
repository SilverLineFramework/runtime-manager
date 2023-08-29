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

```sh
hc benchmark -f wasm/python.wasm --engine iwasm-a wasmer-a-ll wasmer-a-cl wasmtime-a --limit 300 --repeat 200 --argfile parametric.json
# interpreters get double time to reduce dataset imbalance.
hc benchmark -f wasm/python.wasm --engine iwasm-i wasm3-i wasmedge-i --limit 600 --repeat 200 --argfile parametric.json
# wasmtime-j can cause system/runtime crashes due to large JIT compilation memory usage. Make sure it's last in case it gets the entire runtime killed!
hc benchmark -f wasm/python.wasm --engine wasmtime-j --limit 300 --repeat 200 --argfile parametric.json
```
