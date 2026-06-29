from flask import Flask, request, jsonify
from flask_cors import CORS
import tempfile
import os
import glob
import platform
from parser import parse_cpp_file
from modernizer import modernize_file
from validator import validate_cpp

app = Flask(__name__)
CORS(app)


@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "service": "LLM-Powered C++ Code Modernizer API",
        "version": "1.0",
        "status": "running",
        "endpoints": {
            "POST /modernize": "Modernize a C++ code snippet",
            "POST /scan":      "Scan code and return issues only",
            "GET  /health":    "Health check",
            "GET  /debug":     "Debug libclang path"
        }
    })


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy"}), 200


@app.route("/debug", methods=["GET"])
def debug():
    """
    Debug endpoint — shows where libclang is on the server.
    Used to troubleshoot Linux deployment.
    """
    import subprocess

    found_glob = []
    search_patterns = [
        "/usr/**/*clang*.so*",
        "/opt/**/*clang*.so*",
        "/root/**/*clang*.so*",
        "/home/**/*clang*.so*",
    ]
    for pattern in search_patterns:
        matches = glob.glob(pattern, recursive=True)
        found_glob.extend(matches)

    # Check Python package directory
    try:
        import clang
        clang_dir = os.path.dirname(clang.__file__)
        pkg_files = glob.glob(
            os.path.join(clang_dir, "**", "*.so*"), recursive=True
        )
    except Exception as e:
        clang_dir = str(e)
        pkg_files = []

    # Check ldconfig
    try:
        result = subprocess.run(
            ["ldconfig", "-p"],
            capture_output=True, text=True, timeout=10
        )
        ldconfig_clang = [
            line.strip() for line in result.stdout.split("\n")
            if "clang" in line.lower()
        ]
    except Exception as e:
        ldconfig_clang = [str(e)]

    # Check find command
    try:
        result = subprocess.run(
            ["find", "/usr", "-name", "libclang*", "-type", "f"],
            capture_output=True, text=True, timeout=15
        )
        find_results = result.stdout.strip().split("\n")
    except Exception as e:
        find_results = [str(e)]

    return jsonify({
        "platform": platform.system(),
        "clang_package_dir": clang_dir,
        "clang_package_so_files": pkg_files,
        "glob_search_results": found_glob,
        "ldconfig_results": ldconfig_clang,
        "find_results": find_results
    })


@app.route("/scan", methods=["POST"])
def scan():
    data = request.json
    if not data or "code" not in data:
        return jsonify({"error": "Missing 'code' field"}), 400

    cpp_code = data["code"]
    filename  = data.get("filename", "input.cpp")

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".cpp", delete=False
    ) as f:
        f.write(cpp_code)
        temp_path = f.name

    try:
        issues = parse_cpp_file(temp_path)
        return jsonify({
            "filename":    filename,
            "status":      "clean" if not issues else "issues_found",
            "issue_count": len(issues),
            "issues":      issues
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)


@app.route("/modernize", methods=["POST"])
def modernize():
    data = request.json
    if not data or "code" not in data:
        return jsonify({"error": "Missing 'code' field"}), 400

    cpp_code    = data["code"]
    filename    = data.get("filename", "input.cpp")
    modern_path = None

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".cpp", delete=False
    ) as f:
        f.write(cpp_code)
        temp_path = f.name

    modern_path = temp_path.replace(".cpp", "_modern.cpp")

    try:
        issues = parse_cpp_file(temp_path)

        if not issues:
            return jsonify({
                "filename":        filename,
                "status":          "already_modern",
                "message":         "No deprecated patterns found",
                "issues_found":    0,
                "compile_passed":  None,
                "original_code":   cpp_code,
                "modernized_code": cpp_code,
                "issues":          []
            }), 200

        modernized_code, confidence_report = modernize_file(issues, temp_path)

        with open(modern_path, "w") as f:
            f.write(modernized_code)

        compile_passed = validate_cpp(modern_path)

        return jsonify({
            "filename":          filename,
            "status":            "modernized",
            "issues_found":      len(issues),
            "compile_passed":    compile_passed,
            "original_code":     cpp_code,
            "modernized_code":   modernized_code,
            "issues":            issues,
            "confidence_report": confidence_report
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)
        if modern_path and os.path.exists(modern_path):
            os.unlink(modern_path)


if __name__ == "__main__":
    print("\n[INFO] C++ Modernizer API is running!")
    print("[INFO] Open http://localhost:5000 in your browser")
    print("[INFO] Press Ctrl+C to stop\n")
    app.run(debug=True, port=5000)
