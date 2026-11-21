"""Build the tree-sitter-opencl extension.

Only the Extension lives here. Every piece of *metadata* -- name, version,
readme, dependencies, classifiers, package discovery, package data -- is in
``pyproject.toml``, which is the single source for all of it.

Why an Extension cannot move into pyproject.toml as well: the declarative
``[[tool.setuptools.ext-modules]]`` table arrived in setuptools 74, and
setuptools 68 is the last release that installs on Python 3.7 -- an interpreter
this package still supports (tree-sitter 0.20.x is the last line with 3.7
wheels, and the grammar is built at ABI 13 for exactly that reason). Moving the
extension declaring into the toml would either drop 3.7 or force every 3.7
build to fail with "``tool.setuptools`` must not contain {'ext-modules'}".
So the split is: metadata declarative, extension imperative.

The version is not spelled here either -- ``pyproject.toml`` reads it out of
``tree_sitter_opencl/__init__.py`` with ``attr``, and setuptools parses that
with an AST reader rather than importing the package (which would fail: it
needs ``_binding``, the very extension this file builds).
"""

from os import name as os_name
from os.path import isdir, join

from setuptools import Extension, setup
from distutils.command.build import build

# `wheel` backs only bdist_wheel. This module is also imported for sdist,
# egg_info and a plain source install, none of which a bare venv can satisfy.
try:
    from wheel.bdist_wheel import bdist_wheel  # noqa: F401  (registers the command)
except ImportError:  # pragma: no cover - a build without wheel cannot bdist_wheel
    bdist_wheel = None


class Build(build):
    """Copy the query files next to the package.

    `queries/` sits at the repository root, outside `bindings/python`, so
    package-data cannot find it -- its source path is not inside the package
    directory. Copying it into the built package is the only way it ships.
    """

    def run(self):
        if isdir("queries"):
            destination = join(self.build_lib, "tree_sitter_opencl", "queries")
            self.copy_tree("queries", destination)
        super().run()


setup(
    ext_package="tree_sitter_opencl",
    ext_modules=[
        Extension(
            name="_binding",
            sources=[
                "bindings/python/tree_sitter_opencl/binding.c",
                "src/parser.c",
                # NOTE: if this language used an external scanner, add it here.
            ],
            extra_compile_args=(
                # `/std:c11` for MSVC, which rejects the C11 syntax the generated
                # parser uses without it; `-std=c11` plus hidden symbols elsewhere.
                # TREE_SITTER_HIDE_SYMBOLS keeps the grammar's helper symbols out
                # of the dynamic symbol table, so two grammars loaded in one
                # process cannot collide on them.
                (["/std:c11", "/utf-8"] if os_name == "nt" else ["-std=c11", "-fvisibility=hidden"])
            ),
            define_macros=[
                # The limited API floor is 3.7 and the tag is abi3, so one wheel
                # serves 3.7 through 3.15. `binding.c` uses only PyModuleDef,
                # PyModuleDef_Init and PyCapsule_New, all of which are stable ABI.
                ("Py_LIMITED_API", "0x03070000"),
                ("PY_SSIZE_T_CLEAN", None),
                ("TREE_SITTER_HIDE_SYMBOLS", None),
            ],
            include_dirs=["src"],
            py_limited_api=True,
        )
    ],
    # The abi3 *tag* comes from this option, not from `py_limited_api` alone:
    # `py_limited_api=True` only changes how the extension is built, and a plain
    # `bdist_wheel` would still tag the wheel `cp37-cp37m`. Set here so every
    # build front end -- `build`, `pip wheel`, cibuildwheel -- produces abi3
    # without being told to, which is what makes target-size a single wheel.
    options={"bdist_wheel": {"py_limited_api": "cp37"}},
    cmdclass={"build": Build},
)
