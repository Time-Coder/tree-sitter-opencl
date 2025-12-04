import subprocess
import sys

subprocess.call([sys.executable, "-m", "twine", "upload", "dist/tree-sitter-opencl-*.tar.gz", "dist/tree_sitter_opencl-*.whl", "--verbose"])