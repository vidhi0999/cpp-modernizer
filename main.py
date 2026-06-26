import os
from parser import parse_cpp_file
from modernizer import modernize_file
from validator import validate_cpp

def run(filepath):
    print("=" * 50)
    print(" LLM-Powered C++ Code Modernizer")
    print("=" * 50)
    print(f"\n Input file: {filepath}\n")

    # Step 1: Parse
    print("Step 1 — Scanning for deprecated patterns...")
    issues = parse_cpp_file(filepath)

    if not issues:
        print("No deprecated patterns found. Code is already modern!")
        return

    print(f"Found {len(issues)} issue(s):")
    for i, issue in enumerate(issues, 1):
        print(f"  [{i}] {issue['description']}")

    # Step 2: Modernize
    print("\nStep 2 — Modernizing with LLM prompt chain...")
    modernized_code = modernize_file(issues, filepath)

    # Step 3: Save output
    output_path = filepath.replace(".cpp", "_modern.cpp")
    with open(output_path, "w") as f:
        f.write(modernized_code)
    print(f"\n  Saved to: {output_path}")

    # Step 4: Validate
    print("\nStep 3 — Validating modernized code compiles...")
    success = validate_cpp(output_path)

    # Final summary
    print("\n" + "=" * 50)
    if success:
        print(" SUCCESS — Code modernized and verified!")
        print(f" Output: {output_path}")
    else:
        print(" WARNING — Code modernized but failed to compile.")
        print(" Review the output file manually.")
    print("=" * 50)


if __name__ == "__main__":
    filepath = os.path.join(os.path.dirname(__file__), "sample_cpp", "legacy.cpp")
    run(filepath)