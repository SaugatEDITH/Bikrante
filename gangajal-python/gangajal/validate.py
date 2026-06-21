from __future__ import annotations
 
from pathlib import Path
 
from wasmtime import Engine, Store, Module, Linker, Func, FuncType, ValType
 
 
_HERE = Path(__file__).resolve().parent
_ASSETS = _HERE / "assets"
_WASM = _HERE / "gangajal.wasm"
 
 
class _Gangajal:
    def __init__(self):
        self.engine = Engine()
        self.store = Store(self.engine)
        self.module = Module.from_file(self.engine, str(_WASM))
 
        linker = Linker(self.engine)
 
        def _wbindgen_describe(_: int) -> None:
            return None
 
        def _externref_table_set_null(_: int) -> None:
            return None
 
        def _externref_table_grow(_: int) -> int:
            return 0
 
        linker.define(
            self.store,
            "__wbindgen_placeholder__",
            "__wbindgen_describe",
            Func(self.store, FuncType([ValType.i32()], []), _wbindgen_describe),
        )
        linker.define(
            self.store,
            "__wbindgen_externref_xform__",
            "__wbindgen_externref_table_set_null",
            Func(self.store, FuncType([ValType.i32()], []), _externref_table_set_null),
        )
        linker.define(
            self.store,
            "__wbindgen_externref_xform__",
            "__wbindgen_externref_table_grow",
            Func(self.store, FuncType([ValType.i32()], [ValType.i32()]), _externref_table_grow),
        )
 
        self.instance = linker.instantiate(self.store, self.module)
        exports = self.instance.exports(self.store)
 
        self.memory = exports["memory"]
        self.gangajal_raw = exports["gangajal_raw"]
        self.alloc = exports["alloc"]
        self.dealloc = exports["dealloc"]

        self.bloom_ptr = 0
        self.bloom_len = 0
        self.hash_ptr = 0
        self.hash_len = 0
        self._assets_loaded = False
        self.reload_assets()

    def reload_assets(self) -> None:
        bloom = (_ASSETS / "badwords.bloom").read_bytes()
        hashes = (_ASSETS / "badwords.hash.bin").read_bytes()

        if self._assets_loaded:
            self.dealloc(self.store, self.bloom_ptr, self.bloom_len)
            self.dealloc(self.store, self.hash_ptr, self.hash_len)

        self.bloom_ptr = self.alloc(self.store, len(bloom))
        self.memory.write(self.store, bloom, self.bloom_ptr)
        self.bloom_len = len(bloom)

        self.hash_ptr = self.alloc(self.store, len(hashes))
        self.memory.write(self.store, hashes, self.hash_ptr)
        self.hash_len = len(hashes)
        self._assets_loaded = True

    def validate(self, text: str, mode: int = 0) -> str:
        data = text.encode("utf-8")
        text_ptr = self.alloc(self.store, len(data))
        self.memory.write(self.store, data, text_ptr)

        packed = self.gangajal_raw(
            self.store,
            text_ptr,
            len(data),
            int(mode),
            self.bloom_ptr,
            self.bloom_len,
            self.hash_ptr,
            self.hash_len,
        )
 
        out_ptr = (packed >> 32) & 0xFFFFFFFF
        out_len = packed & 0xFFFFFFFF
        out = bytes(self.memory.read(self.store, out_ptr, out_ptr + out_len)).decode("utf-8", errors="replace")
 
        self.dealloc(self.store, text_ptr, len(data))
        self.dealloc(self.store, out_ptr, out_len + 1)
        return out
 
 
_gj = None
 
 
def validate(text: str, mode: int = 0) -> str:
    global _gj
    if _gj is None:
        _gj = _Gangajal()
    return _gj.validate(text, mode)


def reload_assets() -> None:
    global _gj
    if _gj is None:
        _gj = _Gangajal()
        return
    _gj.reload_assets()
