import tree_sitter_python as tspython
from tree_sitter import Language, Parser

PY_LANGUAGE = Language(tspython.language())
parser = Parser(PY_LANGUAGE)

def parse(path):

    with open(path, "rb") as f:
        source = f.read()

    return parser.parse(source)

def chunk(tree, source):
    chunks = []
    for node in tree.root_node.children:
        target = node
        if node.type == "decorated_definition":
            for child in node.children:
                if child.type in ("function_definition", "class_definition"):
                    target = child
                    break
        if target.type in ("function_definition", "class_definition"):
            chunks.append({
                "text": source[node.start_byte:node.end_byte].decode("utf-8"),
                "start_line": node.start_point[0],
                "end_line": node.end_point[0],
                "type": target.type,
            })
    return chunks
