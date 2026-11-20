"""Smoke tests for the Python binding.

They run against both tree-sitter API generations, because the package
supports both and the two differ in how a parser is built. `language()`
already answers a `tree_sitter.Language` on either line, so the tests do not
wrap its result again -- `tree_sitter.Language(language())` raises on 0.20.x
(that constructor wants `(path, name)`) and on 0.21+ (it wants the capsule,
not a Language), which is how this file used to fail on both.
"""

from unittest import TestCase

import tree_sitter
import tree_sitter_opencl


def make_parser(language):
    """Build a parser for `language` on either tree-sitter generation."""
    if hasattr(tree_sitter.Parser, "set_language"):
        parser = tree_sitter.Parser()
        parser.set_language(language)
    else:
        parser = tree_sitter.Parser(language)
    return parser


class TestLanguage(TestCase):
    def test_can_load_grammar(self):
        self.assertIsInstance(tree_sitter_opencl.language(), tree_sitter.Language)

    def test_parse(self):
        parser = make_parser(tree_sitter_opencl.language())
        tree = parser.parse(b"int main() { return 0; }")
        self.assertIsNotNone(tree)
        self.assertFalse(tree.root_node.has_error)

    def test_parses_an_opencl_kernel(self):
        """The grammar is OpenCL C, so a kernel and its qualifiers must read."""
        parser = make_parser(tree_sitter_opencl.language())
        source = (
            b"__kernel void saxpy(__global const float* x, __global float* y, float a)\n"
            b"{\n"
            b"    int gid = get_global_id(0);\n"
            b"    y[gid] = a * x[gid] + y[gid];\n"
            b"}\n"
        )
        tree = parser.parse(source)
        self.assertFalse(tree.root_node.has_error)

        kernel = tree.root_node.named_children[0]
        self.assertEqual(kernel.type, "function_definition")
        # The kernel qualifier is its own node, not a bare token.
        self.assertEqual(kernel.named_children[0].type, "function_qualifier")

        parameters = kernel.child_by_field_name("declarator").child_by_field_name(
            "parameters"
        )
        declarations = [c for c in parameters.named_children]
        self.assertEqual({c.type for c in declarations}, {"parameter_declaration"})
        # `__global` is an address-space qualifier; `const` is a type qualifier.
        self.assertEqual(
            [c.type for c in declarations[0].named_children],
            ["address_space_qualifier", "type_qualifier", "scalar_type", "pointer_declarator"],
        )

    def test_vector_types_are_one_node(self):
        parser = make_parser(tree_sitter_opencl.language())
        tree = parser.parse(b"__kernel void k(__global float4* v) { v[0] = (float4)(1.0f); }")
        self.assertFalse(tree.root_node.has_error)
        types = []

        def walk(node):
            if node.type == "vector_type":
                types.append(node.type)
            for child in node.children:
                walk(child)

        walk(tree.root_node)
        self.assertEqual(types, ["vector_type", "vector_type"])
