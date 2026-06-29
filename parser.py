import clang.cindex
import os
import platform
import glob


def setup_libclang():
    """
    Sets up the libclang library path based on the operating system.
    Mac uses Homebrew. Linux searches multiple locations automatically.
    """
    if platform.system() == "Darwin":
        # Mac — libclang installed via Homebrew
        clang.cindex.Config.set_library_path("/opt/homebrew/opt/llvm/lib")
        return

    if platform.system() == "Linux":
        import subprocess

        # Step 1 — Search inside the clang Python package directory
        try:
            import clang as clang_pkg
            clang_dir = os.path.dirname(clang_pkg.__file__)
            matches = glob.glob(
                os.path.join(clang_dir, "**", "*.so*"), recursive=True
            )
            if matches:
                print(f"[INFO] libclang found in package: {matches[0]}")
                clang.cindex.Config.set_library_file(matches[0])
                return
        except Exception as e:
            print(f"[INFO] Package search failed: {e}")

        # Step 2 — Search via ldconfig
        try:
            result = subprocess.run(
                ["ldconfig", "-p"],
                capture_output=True, text=True, timeout=10
            )
            for line in result.stdout.split("\n"):
                if "libclang" in line and "=>" in line:
                    path = line.split("=>")[-1].strip()
                    print(f"[INFO] libclang found via ldconfig: {path}")
                    clang.cindex.Config.set_library_file(path)
                    return
        except Exception as e:
            print(f"[INFO] ldconfig failed: {e}")

        # Step 3 — Search via find command
        try:
            result = subprocess.run(
                ["find", "/usr", "-name", "libclang*.so*", "-type", "f"],
                capture_output=True, text=True, timeout=15
            )
            paths = [p for p in result.stdout.strip().split("\n") if p]
            if paths:
                print(f"[INFO] libclang found via find: {paths[0]}")
                clang.cindex.Config.set_library_file(paths[0])
                return
        except Exception as e:
            print(f"[INFO] find command failed: {e}")

        # Step 4 — Try hardcoded common paths
        common_paths = [
            "/usr/lib/x86_64-linux-gnu/libclang-14.so.1",
            "/usr/lib/x86_64-linux-gnu/libclang-13.so.1",
            "/usr/lib/x86_64-linux-gnu/libclang-12.so.1",
            "/usr/lib/x86_64-linux-gnu/libclang.so",
            "/usr/lib/llvm-14/lib/libclang.so",
            "/usr/lib/llvm-13/lib/libclang.so",
            "/usr/lib/llvm-12/lib/libclang.so",
            "/usr/local/lib/libclang.so",
        ]
        for path in common_paths:
            if os.path.exists(path):
                print(f"[INFO] libclang found at hardcoded path: {path}")
                clang.cindex.Config.set_library_file(path)
                return

        print("[ERROR] Could not find libclang.so on this system")


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
