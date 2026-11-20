from os.path import dirname, isdir, join
from platform import system

from setuptools import Extension, find_packages, setup
from distutils.command.build import build
try:
    from wheel.bdist_wheel import bdist_wheel  # noqa: F401  (registers the command)
except ImportError:  # pragma: no cover - a build without wheel cannot bdist_wheel
    bdist_wheel = None

HERE = dirname(__file__) or "."


def read_readme():
    """Return README.md, which is the text PyPI shows on the project page.

    The markup has to be named explicitly. Without
    ``long_description_content_type`` twine warns that it is defaulting to
    ``text/x-rst``, and Markdown rendered as reStructuredText collapses into
    one wall of text -- every heading, table and list marker is lost.

    The read is ``utf-8`` and guarded because setup.py is imported by
    ``sdist``, ``egg_info`` and a plain source install on every interpreter in
    the matrix, including CPython 3.7 whose default encoding is the console
    codepage. A build that cannot read its own README should still produce a
    usable package, so the failure is an empty description rather than an
    ImportError out of setup.py.
    """
    path = join(HERE, "README.md")
    try:
        with open(path, encoding="utf-8") as handle:
            return handle.read()
    except OSError:  # pragma: no cover - the sdist always carries the README
        return ""


class Build(build):
    def run(self):
        if isdir("queries"):
            dest = join(self.build_lib, "tree_sitter_opencl", "queries")
            self.copy_tree("queries", dest)
        super().run()


setup(
    name="tree-sitter-opencl",
    version="0.0.4",
    description="An OpenCL C grammar for tree-sitter, with Python bindings",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    url="https://github.com/Time-Coder/tree-sitter-opencl",
    project_urls={
        "Source": "https://github.com/Time-Coder/tree-sitter-opencl",
        "Upstream grammar": "https://github.com/lefp/tree-sitter-opencl",
        "Tracker": "https://github.com/Time-Coder/tree-sitter-opencl/issues",
    },
    author="Bing-Hui WANG",
    author_email="binghui.wang@foxmail.com",
    license="MIT",
    keywords=["tree-sitter", "opencl", "parser", "grammar", "gpgpu"],
    python_requires=">=3.7",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: POSIX :: Linux",
        "Operating System :: MacOS",
        "Programming Language :: C",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Programming Language :: Python :: 3.14",
        "Programming Language :: Python :: 3.15",
        "Topic :: Software Development :: Compilers",
        "Topic :: Text Editors :: Syntax Highlighting",
        "Typing :: Typed",
    ],
    packages=find_packages("bindings/python"),
    package_dir={"": "bindings/python"},
    package_data={
        "tree_sitter_opencl": ["*.pyi", "py.typed"],
        "tree_sitter_opencl.queries": ["*.scm"],
    },
    ext_package="tree_sitter_opencl",
    ext_modules=[
        Extension(
            name="_binding",
            sources=[
                "bindings/python/tree_sitter_opencl/binding.c",
                "src/parser.c",
                # NOTE: if your language uses an external scanner, add it here.
            ],
            extra_compile_args=(
                ["-std=c11"] if system() != 'Windows' else []
            ),
            define_macros=[
                ("Py_LIMITED_API", "0x03070000"),
                ("PY_SSIZE_T_CLEAN", None)
            ],
            include_dirs=["src"],
            py_limited_api=True,
        )
    ],
    cmdclass={
        "build": Build
    },
    install_requires=["tree-sitter>=0.20.0"],
    zip_safe=False
)