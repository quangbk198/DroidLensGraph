import tree_sitter_kotlin as tskotlin
from tree_sitter import Language, Parser

KOTLIN_LANGUAGE = Language(tskotlin.language())
parser = Parser(KOTLIN_LANGUAGE)
src = b"fun main() { validateInfo(); viewModel.validateInfo() }"
tree = parser.parse(src)

def print_tree(node, src, depth=0):
    text = src[node.start_byte:node.end_byte].decode('utf-8')
    print("  " * depth + f"{node.type} '{text}'")
    for child in node.children:
        print_tree(child, src, depth + 1)

print_tree(tree.root_node, src)
