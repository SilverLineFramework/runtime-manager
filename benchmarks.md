```sh
hc benchmark -f `hc index -d wasm -p benchmarks` --engine iwasm wasmedge wasmtime wasmer-cranelift wasmer-singlepass wasmer-llvm
hc benchmark -f `hc index -d wasm -p benchmarks -r wasm=aot` --engine iwasm-aot
hc benchmark -f `hc index -d wasm -p benchmarks -r wasm/=native/` --engine native
hc benchmark -f `hc index -d wasm -p benchmarks -r wasm/=aot-wasmedge/` --engine wasmedge-aot
```