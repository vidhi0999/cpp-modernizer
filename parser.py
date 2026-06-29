import clang.cindex
import os
import platform


def setup_libclang():
    """
    Sets up the libclang library path based on the operating system.
    Mac uses Homebrew, Linux uses the bundled libclang Python package.
    """
    if platform.system() == "Darwin":
        # Mac — libclang installed via Homebrew
        clang.cindex.Config.set_library_path("/opt/homebrew/opt/llvm/lib")

    elif platform.system() == "Linux":
        # Linux (Render) — use libclang Python package which bundles libclang
        try:
            import ctypes.util
            import glob

            # Try common Linux paths first
            linux_paths = [
                "/usr/lib/llvm-14/lib",
                "/usr/lib/llvm-13/lib",
                "/usr/lib/llvm-12/lib",
                "/usr/lib/x86_64-linux-gnu",
                "/usr/lib64",
                "/usr/lib",
            ]

            for path in linux_paths:
                pattern = os.path.join(path, "libclang*.so*")
                matches = glob.glob(pattern)
                if matches:
                    clang.cindex.Config.set_library_file(matches[0])
                    return

            # Fallback — find libclang from the installed Python package
            import site
            for site_path in site.getsitepackages():
                pattern = os.path.join(site_path, "**", "libclang*.so*")
                matches = glob.glob(pattern, recursive=True)
                if matches:
                    clang.cindex.Config.set_library_file(matches[0])
                    return

        except Exception as e:
            print(f"[WARNING] Could not auto-detect libclang path: {e}")


# Run setup when module is imported
setup_libclang()


def parse_cpp_file(filepath):
    """
    Reads a C++ file and returns a list of deprecated patterns found.
    Each result has the pattern type, line number, and the actual code.
    """
    index = clang.cindex.Index.create()
    translation_unit = index.parse(filepath)

    issues = []

    def walk_ast(node):
        # Only look at code in our actual file, not included headers
        if node.location.file and node.location.file.name == filepath:

            # Check 1: Raw pointer in function return type or variable
            if node.kind == clang.cindex.CursorKind.VAR_DECL:
                if node.type.spelling.endswith("*"):
                    issues.append({
                        "type": "raw_pointer",
                        "line": node.location.line,
                        "code": list(node.get_tokens())[0].spelling if list(node.get_tokens()) else "",
                        "description": f"Raw pointer '{node.spelling}' at line {node.location.line} — consider using std::unique_ptr or std::shared_ptr"
                    })

            # Check 2: NULL usage (should be nullptr in modern C++)
            if node.kind == clang.cindex.CursorKind.MACRO_INSTANTIATION:
                if node.spelling == "NULL":
                    issues.append({
                        "type": "null_usage",
                        "line": node.location.line,
                        "code": "NULL",
                        "description": f"NULL used at line {node.location.line} — replace with nullptr"
                    })

            # Check 3: C-style cast
            if node.kind == clang.cindex.CursorKind.CSTYLE_CAST_EXPR:
                tokens = list(node.get_tokens())
                code_snippet = " ".join(t.spelling for t in tokens[:4])
                issues.append({
                    "type": "c_style_cast",
                    "line": node.location.line,
                    "code": code_snippet,
                    "description": f"C-style cast at line {node.location.line} — replace with static_cast<>"
                })

        # Keep walking the rest of the tree
        for child in node.get_children():
            walk_ast(child)

    walk_ast(translation_unit.cursor)
    return issues


if __name__ == "__main__":
    filepath = os.path.join(os.path.dirname(__file__), "sample_cpp", "legacy.cpp")
    issues = parse_cpp_file(filepath)

    if issues:
        print(f"\n Found {len(issues)} deprecated pattern(s):\n")
        for i, issue in enumerate(issues, 1):
            print(f"  [{i}] {issue['description']}")
    else:
        print("No deprecated patterns found.")