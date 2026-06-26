import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def modernize_issue(issue, full_code):
    """
    Takes one deprecated pattern and the full C++ file content,
    runs a 3-stage prompt chain, and returns modernized code.
    """

    print(f"\n  Modernizing: {issue['description']}")

    # ---------- PROMPT 1: Explain the problem ----------
    prompt1 = f"""You are a C++ expert. Look at this deprecated pattern found in C++ code:

Issue type: {issue['type']}
Line number: {issue['line']}
Description: {issue['description']}

Full source code:
```cpp
{full_code}
```

Explain in 2-3 sentences why this pattern is problematic in modern C++."""

    response1 = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt1}],
        max_tokens=200
    )
    explanation = response1.choices[0].message.content
    print(f"  Explanation: {explanation[:120]}...")

    # ---------- PROMPT 2: Generate modernized code ----------
    prompt2 = f"""You are a C++ expert. Here is a C++ file with a deprecated pattern:

Issue: {issue['description']}

Full source code:
```cpp
{full_code}
```

Rewrite the ENTIRE file fixing this specific issue using modern C++17 standards.
Return ONLY the corrected C++ code, no explanations, no markdown, no backticks."""

    response2 = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt2}],
        max_tokens=800
    )
    modernized_code = response2.choices[0].message.content.strip()

    # Strip markdown backticks if model adds them anyway
    if modernized_code.startswith("```"):
        lines = modernized_code.split("\n")
        modernized_code = "\n".join(lines[1:-1])

    # ---------- PROMPT 3: Self-review ----------
    prompt3 = f"""You are a strict C++ code reviewer.

Original code had this issue: {issue['description']}

Here is the modernized version:
```cpp
{modernized_code}
```

Does this fix correctly resolve the issue without breaking anything?
Reply with either:
APPROVED - if the fix is correct
REJECTED: <reason> - if there is a problem"""

    response3 = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt3}],
        max_tokens=100
    )
    review = response3.choices[0].message.content.strip()
    print(f"  Review: {review}")

    if review.startswith("APPROVED"):
        return modernized_code
    else:
        print(f"  Fix rejected, keeping original.")
        return full_code


def modernize_file(issues, filepath):
    """
    Takes all issues found by parser and modernizes them one by one.
    """
    with open(filepath, "r") as f:
        current_code = f.read()

    for issue in issues:
        current_code = modernize_issue(issue, current_code)

    return current_code


if __name__ == "__main__":
    from parser import parse_cpp_file

    filepath = os.path.join(os.path.dirname(__file__), "sample_cpp", "legacy.cpp")
    issues = parse_cpp_file(filepath)

    print(f"Found {len(issues)} issues. Starting modernization...\n")
    modernized = modernize_file(issues, filepath)

    output_path = os.path.join(os.path.dirname(__file__), "sample_cpp", "modern.cpp")
    with open(output_path, "w") as f:
        f.write(modernized)

    print(f"\n Done! Modernized code saved to sample_cpp/modern.cpp")
    print(f"\n--- MODERNIZED CODE PREVIEW ---\n")
    print(modernized)