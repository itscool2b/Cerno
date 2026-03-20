import importlib
from pathlib import Path
from tree_sitter import Language, Parser

# Language registry: file extension -> parsing config
# Each config defines:
#   module        - tree-sitter grammar package name
#   top_level     - AST node types to extract as chunks
#   wrappers      - nodes that wrap a target (e.g. decorators, exports)
#   nested        - node types to also extract from inside class-like nodes (Java, C#)
#   ts_dialect    - only for tree-sitter-typescript which has two sub-languages

LANGUAGES = {
    ".py": {
        "module": "tree_sitter_python",
        "top_level": {"function_definition", "class_definition"},
        "wrappers": {"decorated_definition": {"function_definition", "class_definition"}},
        "nested": {"function_definition"},
        "import_types": {"import_statement", "import_from_statement"},
        "call_type": "call",
        "call_name_field": "function",
        "signature_body_type": "block",
    },
    ".js": {
        "module": "tree_sitter_javascript",
        "top_level": {"function_declaration", "class_declaration"},
        "wrappers": {"export_statement": {"function_declaration", "class_declaration"}},
        "nested": {"method_definition"},
        "import_types": {"import_statement"},
        "call_type": "call_expression",
        "call_name_field": "function",
        "signature_body_type": "statement_block",
    },
    ".ts": {
        "module": "tree_sitter_typescript",
        "ts_dialect": "typescript",
        "top_level": {
            "function_declaration", "class_declaration",
            "interface_declaration", "type_alias_declaration",
            "enum_declaration",
        },
        "wrappers": {"export_statement": {
            "function_declaration", "class_declaration",
            "interface_declaration", "type_alias_declaration",
            "enum_declaration",
        }},
        "nested": {"method_definition"},
        "import_types": {"import_statement"},
        "call_type": "call_expression",
        "call_name_field": "function",
        "signature_body_type": "statement_block",
    },
    ".rs": {
        "module": "tree_sitter_rust",
        "top_level": {"function_item", "struct_item", "enum_item", "trait_item", "impl_item"},
        "nested": {"function_item"},
        "import_types": {"use_declaration"},
        "call_type": "call_expression",
        "call_name_field": "function",
        "signature_body_type": "block",
    },
    ".go": {
        "module": "tree_sitter_go",
        "top_level": {"function_declaration", "method_declaration", "type_declaration"},
        "import_types": {"import_declaration"},
        "call_type": "call_expression",
        "call_name_field": "function",
        "signature_body_type": "block",
    },
    ".java": {
        "module": "tree_sitter_java",
        "top_level": {"class_declaration", "interface_declaration", "enum_declaration"},
        "nested": {"method_declaration", "constructor_declaration"},
        "import_types": {"import_declaration"},
        "call_type": "method_invocation",
        "call_name_field": "name",
        "signature_body_type": "block",
    },
    ".c": {
        "module": "tree_sitter_c",
        "top_level": {"function_definition", "struct_specifier", "enum_specifier"},
        "import_types": {"preproc_include"},
        "call_type": "call_expression",
        "call_name_field": "function",
        "signature_body_type": "compound_statement",
    },
    ".cpp": {
        "module": "tree_sitter_cpp",
        "top_level": {"function_definition", "class_specifier", "struct_specifier", "namespace_definition"},
        "nested": {"function_definition"},
        "import_types": {"preproc_include"},
        "call_type": "call_expression",
        "call_name_field": "function",
        "signature_body_type": "compound_statement",
    },
    ".rb": {
        "module": "tree_sitter_ruby",
        "top_level": {"method", "class", "module"},
        "nested": {"method"},
        "import_types": set(),
        "call_type": "call",
        "call_name_field": "method",
        "signature_body_type": "body_statement",
    },
    ".cs": {
        "module": "tree_sitter_c_sharp",
        "top_level": {"class_declaration", "struct_declaration", "interface_declaration", "enum_declaration"},
        "nested": {"method_declaration", "constructor_declaration"},
        "import_types": {"using_directive"},
        "call_type": "invocation_expression",
        "call_name_field": "function",
        "signature_body_type": "block",
    },
}

# Aliases for alternate extensions
LANGUAGES[".jsx"] = LANGUAGES[".js"]
LANGUAGES[".mjs"] = LANGUAGES[".js"]
LANGUAGES[".tsx"] = {
    **LANGUAGES[".ts"],
    "ts_dialect": "tsx",
}
LANGUAGES[".h"] = LANGUAGES[".c"]
LANGUAGES[".cc"] = LANGUAGES[".cpp"]
LANGUAGES[".cxx"] = LANGUAGES[".cpp"]
LANGUAGES[".hpp"] = LANGUAGES[".cpp"]

# Cache loaded Language objects to avoid re-importing
_lang_cache = {}
_parser = Parser()


def get_language_config(path):
    """Return language config for a file path, or None if unsupported."""
    ext = Path(path).suffix.lower()
    return LANGUAGES.get(ext)


def _load_language(config):
    """Load and cache a tree-sitter Language from its grammar package."""
    module_name = config["module"]
    cache_key = f"{module_name}:{config.get('ts_dialect', '')}"

    if cache_key not in _lang_cache:
        mod = importlib.import_module(module_name)
        # tree-sitter-typescript exposes language_typescript() and language_tsx()
        dialect = config.get("ts_dialect")
        if dialect == "tsx":
            _lang_cache[cache_key] = Language(mod.language_tsx())
        elif dialect == "typescript":
            _lang_cache[cache_key] = Language(mod.language_typescript())
        else:
            _lang_cache[cache_key] = Language(mod.language())

    return _lang_cache[cache_key]


def parse(path):
    """Parse a file with the correct tree-sitter grammar.
    Returns (tree, source_bytes, config). Raises ValueError if unsupported."""
    config = get_language_config(path)
    if config is None:
        raise ValueError(f"Unsupported file type: {Path(path).suffix}")

    lang = _load_language(config)
    _parser.language = lang

    with open(path, "rb") as f:
        source = f.read()

    return _parser.parse(source), source, config


def extract_imports(tree, source, config):
    """Collect import/include/using/require statements from the root level."""
    import_types = config.get("import_types", set())
    if not import_types:
        return []
    imports = []
    for node in tree.root_node.children:
        if node.type in import_types:
            imports.append(source[node.start_byte:node.end_byte].decode("utf-8"))
    return imports


def extract_signature(node, source, config):
    """Extract everything before the body node (the signature).
    e.g. 'def foo(a: int) -> str' without the body block."""
    body_type = config.get("signature_body_type")
    if not body_type:
        return source[node.start_byte:node.end_byte].decode("utf-8").split("\n")[0]
    for child in node.children:
        if child.type == body_type:
            sig = source[node.start_byte:child.start_byte].decode("utf-8").rstrip().rstrip(":")
            return sig.strip()
    # No body found (e.g. interface methods, abstract) -- use first line
    return source[node.start_byte:node.end_byte].decode("utf-8").split("\n")[0]


def extract_calls(node, source, config):
    """Recursively find call expressions, return called function names."""
    call_type = config.get("call_type")
    call_name_field = config.get("call_name_field")
    if not call_type or not call_name_field:
        return []
    calls = set()
    _collect_calls(node, source, call_type, call_name_field, calls)
    return sorted(calls)


def _collect_calls(node, source, call_type, call_name_field, calls):
    """Recursive helper to gather call names."""
    if node.type == call_type:
        func_node = node.child_by_field_name(call_name_field)
        if func_node:
            name = source[func_node.start_byte:func_node.end_byte].decode("utf-8")
            calls.add(name)
    for child in node.children:
        _collect_calls(child, source, call_type, call_name_field, calls)


def extract_docstring(node, source, config):
    """Extract the first docstring/doc-comment from a function/class body."""
    for child in node.children:
        # Python: expression_statement containing a string
        if child.type == "expression_statement":
            for grandchild in child.children:
                if grandchild.type == "string":
                    return source[grandchild.start_byte:grandchild.end_byte].decode("utf-8")
        # Block-level: look inside the body
        if child.type in ("block", "statement_block", "body_statement", "class_body"):
            for body_child in child.children:
                if body_child.type == "expression_statement":
                    for gc in body_child.children:
                        if gc.type == "string":
                            return source[gc.start_byte:gc.end_byte].decode("utf-8")
                # JS/TS/Java/C-style doc comments
                if body_child.type == "comment":
                    text = source[body_child.start_byte:body_child.end_byte].decode("utf-8")
                    if text.startswith("/**") or text.startswith("///"):
                        return text
                break  # only check first statement in body
        # Doc comments directly before body
        if child.type == "comment":
            text = source[child.start_byte:child.end_byte].decode("utf-8")
            if text.startswith("/**") or text.startswith("///") or text.startswith("#"):
                return text
    return ""


def _get_node_name(node, source):
    """Get the name of a definition node (function, class, etc.)."""
    name_node = node.child_by_field_name("name")
    if name_node:
        return source[name_node.start_byte:name_node.end_byte].decode("utf-8")
    return ""


def _get_superclasses(node, source):
    """Get superclass names from a class definition."""
    for child in node.children:
        if child.type in ("argument_list", "superclass", "class_heritage",
                          "superclasses", "type_parameter_list"):
            return source[child.start_byte:child.end_byte].decode("utf-8")
    return ""


def extract_file_metadata(path):
    """Parse a file and return complete file-level metadata: imports, definitions."""
    tree, source, config = parse(path)
    imports = extract_imports(tree, source, config)

    definitions = []
    top_level = config["top_level"]
    wrappers = config.get("wrappers", {})
    nested = config.get("nested", set())

    for node in tree.root_node.children:
        target = node
        if node.type in wrappers:
            inner_types = wrappers[node.type]
            for child in node.children:
                if child.type in inner_types:
                    target = child
                    break
            if target is node and node.type not in top_level:
                continue

        if target.type in top_level:
            definitions.append({
                "name": _get_node_name(target, source),
                "signature": extract_signature(target, source, config),
                "type": target.type,
                "calls": extract_calls(target, source, config),
                "docstring": extract_docstring(target, source, config),
                "start_line": target.start_point[0],
                "end_line": target.end_point[0],
            })

            # Nested definitions (Java/C# methods inside classes)
            if nested:
                _extract_nested_metadata(target, source, config, nested, definitions)

    return {"path": path, "imports": imports, "definitions": definitions}


def _extract_nested_metadata(parent, source, config, target_types, definitions):
    """Extract metadata for nested definitions (methods, constructors)."""
    for child in parent.children:
        if child.type in target_types:
            definitions.append({
                "name": _get_node_name(child, source),
                "signature": extract_signature(child, source, config),
                "type": child.type,
                "calls": extract_calls(child, source, config),
                "docstring": extract_docstring(child, source, config),
                "start_line": child.start_point[0],
                "end_line": child.end_point[0],
            })
        elif child.type in ("class_body", "declaration_list", "block", "body_statement"):
            _extract_nested_metadata(child, source, config, target_types, definitions)


def chunk(tree, source, config):
    """Extract semantic chunks from a parsed AST."""
    chunks = []
    top_level = config["top_level"]
    wrappers = config.get("wrappers", {})
    nested = config.get("nested", set())

    for node in tree.root_node.children:
        target = node

        # Unwrap wrapper nodes (decorators, export statements, etc.)
        if node.type in wrappers:
            inner_types = wrappers[node.type]
            for child in node.children:
                if child.type in inner_types:
                    target = child
                    break
            if target is node and node.type not in top_level:
                continue

        if target.type in top_level:
            chunks.append({
                "text": source[node.start_byte:node.end_byte].decode("utf-8"),
                "start_line": node.start_point[0],
                "end_line": node.end_point[0],
                "type": target.type,
                "name": _get_node_name(target, source),
                "signature": extract_signature(target, source, config),
                "calls": extract_calls(target, source, config),
                "docstring": extract_docstring(target, source, config),
                "superclasses": _get_superclasses(target, source),
            })

            # For Java/C#: also extract methods from inside classes
            if nested:
                _extract_nested(node, source, config, nested, chunks)

    return chunks


def _extract_nested(parent, source, config, target_types, chunks):
    """Pull out nested definitions (methods, constructors) from class-like nodes."""
    for child in parent.children:
        if child.type in target_types:
            chunks.append({
                "text": source[child.start_byte:child.end_byte].decode("utf-8"),
                "start_line": child.start_point[0],
                "end_line": child.end_point[0],
                "type": child.type,
                "name": _get_node_name(child, source),
                "signature": extract_signature(child, source, config),
                "calls": extract_calls(child, source, config),
                "docstring": extract_docstring(child, source, config),
                "superclasses": "",
            })
        # Recurse into body blocks to find methods
        elif child.type in ("class_body", "declaration_list", "block", "body_statement"):
            _extract_nested(child, source, config, target_types, chunks)
