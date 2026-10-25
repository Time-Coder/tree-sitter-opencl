"""OpenCL C grammar for tree-sitter

``language()`` returns a native ``tree_sitter.Language`` object that is
compatible with both the legacy tree-sitter 0.20.x line (the last line that
ships CPython 3.7+ wheels) and the modern tree-sitter 0.21+ line.
"""

import os

import tree_sitter


def _library():
    """Resolve the shared-extension file backing this package."""
    from . import _binding

    return _binding.__file__


def language():
    """Return a tree-sitter Language object for OpenCL C.

    On the legacy tree-sitter 0.20.x line the grammar module exports the raw
    ``tree_sitter_opencl`` symbol, so the shared extension is loaded directly
    through ``ctypes``. On the modern line the ``_binding`` module returns a
    ``PyCapsule`` that ``tree_sitter.Language`` wraps. Both forms return the
    same native ``tree_sitter.Language`` stream so callers can hand it to a
    ``tree_sitter.Parser`` regardless of the installed tree-sitter version.
    """
    try:
        # Modern path: _binding.language() returns a PyCapsule.
        from ._binding import language as _lang_capsule
    except AttributeError:  # pragma: no cover - defensive
        _lang_capsule = None

    if _lang_capsule is not None:
        # 0.21+ wraps the capsule with Language(capsule).
        try:
            return tree_sitter.Language(_lang_capsule())
        except (TypeError, ValueError):
            pass

    # Legacy path: tree-sitter 0.20.x Language(library_path, name) loads the
    # dynamic library and looks up the tree_sitter_<name> symbol.
    lib = _library()
    return tree_sitter.Language(lib, "opencl")