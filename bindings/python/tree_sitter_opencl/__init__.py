"""OpenCL C grammar for tree-sitter.

``language()`` returns a native ``tree_sitter.Language`` object for whatever
tree-sitter release is installed. Three constructor shapes exist across the
supported range, and this module's only job is to pick the right one:

* **0.20.x** -- ``Language(path, name)`` loads the shared extension and looks
  up ``tree_sitter_opencl``. ``Parser`` is built empty and filled in with
  ``set_language``.
* **0.22.x** -- ``Language(ptr)``, where ``ptr`` is the *integer* address of
  the ``TSLanguage``. This is the awkward one: ``Language(path, name)`` no
  longer exists, and passing the ``PyCapsule`` that ``_binding.language()``
  answers raises ``TypeError: an integer is required`` because the capsule is
  not coerced. The capsule's pointer is unwrapped through
  ``PyCapsule_GetPointer`` instead. This package could not load its grammar at
  all on 0.22 before that branch existed.
* **0.23+** -- ``Language(capsule)``, the form ``_binding.language()`` was
  written for. ``Parser(language)`` replaces the old two-step construction.

The three are probed in that order, most specific first, because a wrong
``Language`` call is a ``TypeError`` rather than a wrong answer -- so a failed
probe says nothing about which release this is, and the success of the *next*
one does.
"""

import ctypes

import tree_sitter

# `__version__` is the one place the release number is written. pyproject.toml
# reads it from here with `attr` -- setuptools parses the literal with an AST
# reader rather than importing this module, which is required here because the
# module needs `_binding` and that extension does not exist until after the
# build. The published metadata and this attribute therefore cannot disagree.
__version__ = "0.0.5"

# The capsule name ``binding.c`` hands to ``PyCapsule_New``. ``GetPointer``
# checks it, so a capsule from some other grammar is refused instead of being
# reinterpreted as this one's TSLanguage.
_CAPSULE_NAME = b"tree_sitter.Language"


def _library():
    """Resolve the shared-extension file backing this package."""
    from . import _binding

    return _binding.__file__


def _capsule_pointer(capsule):
    """Return the integer TSLanguage address held by ``capsule``'s PyCapsule.

    tree-sitter 0.22 wants that address rather than the capsule. Only 0.22
    needs this, and only 0.22 is where it can run -- ``ctypes.pythonapi``
    always has ``PyCapsule_GetPointer``, but the pointer is useless to the
    other lines, which is why the caller tries the capsule first.
    """
    get_pointer = ctypes.pythonapi.PyCapsule_GetPointer
    get_pointer.restype = ctypes.c_void_p
    get_pointer.argtypes = [ctypes.py_object, ctypes.c_char_p]
    return get_pointer(capsule, _CAPSULE_NAME)


def language():
    """Return a ``tree_sitter.Language`` for OpenCL C.

    Exactly one of the three branches returns; the others raise ``TypeError``
    or ``ValueError`` from tree-sitter's own constructor and are skipped. The
    last branch is unconditional so that a genuinely broken install still fails
    with tree-sitter's message rather than this module's.
    """
    from ._binding import language as _lang_capsule

    capsule = _lang_capsule()

    # 0.23+: the capsule itself is the argument.
    try:
        return tree_sitter.Language(capsule)
    except (TypeError, ValueError):
        pass

    # 0.22.x: the integer address behind the capsule.
    try:
        return tree_sitter.Language(_capsule_pointer(capsule))
    except (TypeError, ValueError):
        pass

    # 0.20.x: no capsule support at all; load the shared object by path.
    return tree_sitter.Language(_library(), "opencl")
