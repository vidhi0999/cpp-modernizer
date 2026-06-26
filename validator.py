import subprocess
import os

def validate_cpp(filepath):
    """
    Tries to compile the C++ file using g++.
    Returns True if it compiles successfully, False if there are errors.
    """
    print(f"\n  Validating: {filepath}")

    result = subprocess.run(
        ["g++", "-std=c++17", "-o", "/tmp/test_output", filepath],
        capture_output=True,
        text=True
    )

    if result.returncode == 0:
        print(f"  Compile check: PASSED")
        return True
    else:
        print(f"  Compile check: FAILED")
        print(f"  Errors:\n{result.stderr}")
        return False


if __name__ == "__main__":
    filepath = os.path.join(os.path.dirname(__file__), "sample_cpp", "modern.cpp")
    validate_cpp(filepath)