# tree-sitter-opencl

An [OpenCL C](https://registry.khronos.org/OpenCL/) grammar for
[tree-sitter](https://tree-sitter.github.io/tree-sitter/), with Python
bindings published as wheels.

```python
import tree_sitter, tree_sitter_opencl

language = tree_sitter_opencl.language()          # a tree_sitter.Language
parser = tree_sitter.Parser(language)             # tree-sitter 0.23+
tree = parser.parse(b"__kernel void k(__global float* o) { o[0] = 1.0f; }")
tree.root_node.type                               # 'translation_unit'
```

On tree-sitter 0.20.x through 0.22.x the parser is built the other way round —
`parser = tree_sitter.Parser(); parser.set_language(language)` — see
[Compatibility](#tree-sitter-version-compatibility).

The grammar is a fork of [`lefp/tree-sitter-opencl`](https://github.com/lefp/tree-sitter-opencl)
(itself derived from `tree-sitter-c`), rebuilt so that the Python binding
works across the whole tree-sitter range this package supports.

## Installation

```console
pip install tree-sitter-opencl
```

`tree-sitter` is a declared dependency and is installed automatically. The
grammar itself is a sibling of the runtime, so it also works alongside an
existing `tree-sitter` pin — `language()` adapts to the installed release from
0.20.4 through 0.26.x, see [Compatibility](#tree-sitter-version-compatibility).

Prebuilt wheels are published for CPython 3.7 through 3.15 on 64-bit and
32-bit Windows. Each wheel carries a `_binding.pyd` compiled against its own
interpreter, so the wheel tags are `cp37`…`cp315` rather than `abi3`.

On Linux and macOS there is no current wheel: `pip` builds the extension from
the source distribution, which needs a C compiler. That path was verified by
building this sdist in a bare virtual environment, importing it and parsing a
kernel.

## Usage

### Parsing

`language()` returns a native `tree_sitter.Language`. Hand it to a parser; the
constructors differ between tree-sitter generations, see below.

```python
import tree_sitter
import tree_sitter_opencl

language = tree_sitter_opencl.language()
```

### Queries

```python
import tree_sitter
import tree_sitter_opencl

language = tree_sitter_opencl.language()

# 0.22 and newer take (language, source); 0.20 and 0.21 want an empty Query
# filled in through language.query(source).
try:
    query = tree_sitter.Query(language, "(function_definition) @fn")
except TypeError:
    query = language.query("(function_definition) @fn")
```

### Highlights

A standard `highlights.scm` ships with the grammar in a `queries/` directory
beside the package's `__init__.py`:

```python
import os
import tree_sitter_opencl

highlights = os.path.join(
    os.path.dirname(tree_sitter_opencl.__file__), "queries", "highlights.scm"
)
```

`queries/` is data, not a module — there is no `__init__.py` in it, so it is a
namespace package rather than a regular one. `os.path.dirname` is the portable
way to find the file; `importlib.resources` spells this differently before and
after Python 3.9 (`path`/`read_text` versus `files`), and the package still
supports 3.7.

## Tree-sitter version compatibility

The grammar is generated at **ABI 13**, which every tree-sitter from 0.20.x
onwards accepts, so one binding serves every supported release. The *Python*
API around it is not stable, though, and the two entry points changed in
different releases — a test for `set_language` decides the parser, but not the
query.

| tree-sitter | parser construction | query construction |
| --- | --- | --- |
| 0.20.x – 0.22.x | `p = Parser(); p.set_language(lang)` | `lang.query(src)` |
| 0.23+ | `Parser(lang)` | `Query(lang, src)` |

0.22.x straddles the two columns: it still has `set_language` (so the parser
side belongs on the left) but already accepts `Query(language, source)`
(so the query side belongs on the right). Both query spellings work there; only
`lang.query` exists on 0.20 and 0.21, and only `Query(lang, source)` works from
0.23 on. Probe the two capabilities separately rather than deriving one from
the other — the snippet in [Queries](#queries) tries the modern call and falls
back on `TypeError`.

### The 0.22 `Language` constructor

0.22.x is the release this package could not load at all until its `language()`
learned the third constructor shape:

| tree-sitter | what `Language(...)` accepts |
| --- | --- |
| 0.20.x | `Language(path, name)` — loads the shared object itself |
| 0.22.x | `Language(ptr)` — the **integer** address of the `TSLanguage` |
| 0.23+ | `Language(capsule)` — the `PyCapsule` `_binding.language()` returns |

On 0.22 `Language(path, name)` no longer exists and the capsule is not
coerced, so passing it raises `TypeError: an integer is required`. `language()`
therefore tries the capsule first, then unwraps the capsule's pointer through
`PyCapsule_GetPointer` and passes the integer. Every release 0.20.4, 0.21.3,
0.22.3 and 0.26.1 is exercised on each release of this package.

`language()` returns a `tree_sitter.Language` on all three, so callers never
branch on the version — only the constructors above do.

Do not wrap the result again. `Language(language())` looks harmless but raises
on every line: the constructors want a path/pointer/capsule, never a
`Language`. Assign it and pass it on:

```python
language = tree_sitter_opencl.language()
parser = tree_sitter.Parser(language)      # 0.23+
```

## Grammar coverage

The grammar tracks OpenCL C rather than plain C. The parts that differ from
`tree-sitter-c` are:

**Kernel and address-space qualifiers**

- `kernel` and `__kernel`
- `global`/`__global`, `local`/`__local`, `constant`/`__constant`,
  `private`/`__private`, `generic`/`__generic`
- `read_only`/`__read_only`, `write_only`/`__write_only`,
  `read_write`/`__read_write`
- `pipe` as a type qualifier

**Types**

- Scalars: `bool`, `char`, `uchar`, `ushort`, `int`, `uint`, `ulong`, `float`,
  `double`, `half`, `void`, plus `size_t`, `ptrdiff_t`, `intptr_t`,
  `uintptr_t`
- Vectors at widths 2, 3, 4, 8 and 16 over `char`, `uchar`, `short`, `ushort`,
  `int`, `uint`, `long`, `ulong`, `float` and `double` — 50 type names in all
- Opaque types: the `image*_t` family, `sampler_t`, `queue_t`, `ndrange_t`,
  `clk_event_t`, `reserve_id_t`, `event_t`, `cl_mem_fence_flags`

**Constructs**

- `__attribute__((...))`, including `vec_type_hint` and
  `reqd_work_group_size`
- Vector casts and compound literals: `(float4)(1, 2, 3, 4)` and
  `(float4){1, 2, 3, 4}`
- Swizzles as ordinary field access (`.x`, `.s0`, `.s01`)
- The C preprocessor, including `#define`, function-like macros and
  `#include`
- `struct`, `union`, `enum`, `typedef`, designated initializers, `do`/`while`,
  `switch`, `goto`

## Node reference

The node names are the ones the queries use. For a kernel parameter, the
qualifiers, the type and the declarator are siblings of each other:

```c
__kernel void saxpy(__global const float* x, __global float* y, float a)
//                 ^^^^^^^^^ ^^^^^ ^^^^^ ^^^^^^    ^^^^^^^^^ ^^^^^ ^^^
//                 address   type  scalar pointer  address  scalar identifier
//                 space     qualifier                          type
```

```
translation_unit
└── function_definition        fields: declarator, type, body
    ├── function_qualifier     the `__kernel`
    ├── scalar_type            `void`
    ├── function_declarator    fields: declarator, parameters
    │   ├── identifier         `saxpy`
    │   └── parameter_list
    │       └── parameter_declaration   fields: declarator, type
    └── compound_statement
```

Expressions use the usual tree-sitter-c names and fields:
`assignment_expression` (`left`, `right`, `operator`), `binary_expression`
(`left`, `right`, `operator`), `call_expression` (`function`, `arguments`),
`subscript_expression` (`argument`, `index`), `cast_expression` (`type`,
`value`), `field_expression`, `sizeof_expression`, `conditional_expression`.

Note that `address_space_qualifier`, `type_qualifier` and `access_qualifier`
are separate node types rather than being folded into one `type_qualifier`
list, so a query can tell `__global` from `const` without inspecting the text.

### `short` and `long` are `sized_type_specifier`, not `scalar_type`

This is the one node-name detail that bites a tool. Most scalar spellings land
in `scalar_type`:

| spelling | node type |
| --- | --- |
| `bool`, `char`, `uchar`, `int`, `uint`, `float`, `double`, `half`, `void` | `scalar_type` |
| `ushort`, `ulong`, `size_t`, `ptrdiff_t`, `intptr_t`, `uintptr_t` | `scalar_type` |
| `short`, `long` | **`sized_type_specifier`** |
| `unsigned int`, `signed long`, ... | `sized_type_specifier` with a `type:` field |

`short` and `long` are modifiers in C, so the grammar keeps them as
`sized_type_specifier` even when they stand alone — a node's *text* is then the
whole spelling (`long`), with no `type` field child. The OpenCL explicit-width
names `ushort` and `ulong` are single tokens and so are plain `scalar_type`.
A query that matches only `scalar_type` silently misses `short` and `long`;
match `(scalar_type) (sized_type_specifier)` together when collecting
declared types.

## Known limitations

Two constructs an OpenCL compiler accepts are rejected by this grammar today.
Both fail as an `ERROR` node rather than as a wrong tree, so a tool can detect
them, but they do parse as errors:

- **An address space on a cast's type.** `(global uint*)&x[0]` is an `ERROR`;
  the qualifier is accepted in a declaration (`global uint* p = ...`) but not
  in a cast.
- **The `h` suffix on a floating literal.** `1.0h` is an `ERROR`;
  `(half)1.0` is the spelling that parses.

## Development

The repository holds the generators and the release tooling, all driven from
the checkout:

| file | what it does |
| --- | --- |
| `build_matrix.py` | builds the sdist and one wheel per interpreter, CPython 3.7–3.15 × 32/64-bit Windows |
| `verify_dist.py` | checks every wheel's tag and that it carries a `.pyd` |
| `test_wheels.py` | installs each wheel into its matching interpreter and parses a kernel |
| `upload.py` | uploads the wheels *and* the sdist with `twine` |

The binding's own tests live at
`bindings/python/tree_sitter_opencl/tests/test_binding.py` and run on both
generations:

```console
python -m unittest discover -s bindings/python/tree_sitter_opencl/tests -v
```

They run against an **installed** copy of the package, not the source tree:
`tree_sitter_opencl/_binding` is a compiled extension that only exists after a
build, so a checkout without one fails with `No module named
tree_sitter_opencl._binding`. Install the wheel for the interpreter you are
testing first — that is exactly what `test_wheels.py` does.

The parser is generated by the tree-sitter CLI from `grammar.js`; `src/parser.c`
is checked in, so building the package does not need Node.js or the CLI. See
`binding.gyp` and `bindings/rust/` for the Node and Rust bindings the upstream
grammar ships.

## License

MIT. The C grammar this one descends from is Copyright (c) 2014 Max Brunsfeld;
the OpenCL C modifications are Copyright (c) 2023 Peter Lef. See
[LICENSE](LICENSE).

## Related

- [`github.com/lefp/tree-sitter-opencl`](https://github.com/lefp/tree-sitter-opencl) — the grammar this package is forked from
- [`PyGPGPU`](https://github.com/Time-Coder/PyGPGPU) — uses this grammar to read OpenCL kernels
