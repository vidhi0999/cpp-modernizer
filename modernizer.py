import os
import re
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def get_confidence_score(issue, original_code, modernized_code):
    """
    Asks the LLM to score its own fix from 0-100.
    Also asks it to explain its confidence level.
    This is called 'self-evaluation' in ML systems.
    """

    prompt = f"""You are a strict C++ code reviewer and quality assessor.

Original issue detected: {issue['description']}

Original code:
{original_code}

Proposed modernized code:
{modernized_code}

Evaluate this fix on these 4 criteria:
1. CORRECTNESS - Does it correctly fix the deprecated pattern? (0-25 points)
2. SAFETY - Does it preserve the original behavior without introducing bugs? (0-25 points)
3. COMPLETENESS - Does it fix ALL instances of this pattern in the file? (0-25 points)
4. STYLE - Does it follow modern C++17 best practices? (0-25 points)

Respond in EXACTLY this format, nothing else:
SCORE: <total score out of 100>
CORRECTNESS: <score out of 25> - <one line reason>
SAFETY: <score out of 25> - <one line reason>
COMPLETENESS: <score out of 25> - <one line reason>
STYLE: <score out of 25> - <one line reason>
SUMMARY: <one sentence overall assessment>"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=300
    )

    return response.choices[0].message.content.strip()


def parse_confidence_response(response_text):
    """
    Parses the structured confidence response from the LLM
    into a clean dictionary we can work with.
    """
    result = {
        "total_score": 0,
        "correctness": 0,
        "safety": 0,
        "completeness": 0,
        "style": 0,
        "summary": "",
        "raw_response": response_text
    }

    try:
        score_match = re.search(r'SCORE:\s*(\d+)', response_text)
        if score_match:
            result["total_score"] = int(score_match.group(1))

        correctness_match = re.search(r'CORRECTNESS:\s*(\d+)', response_text)
        if correctness_match:
            result["correctness"] = int(correctness_match.group(1))

        safety_match = re.search(r'SAFETY:\s*(\d+)', response_text)
        if safety_match:
            result["safety"] = int(safety_match.group(1))

        completeness_match = re.search(r'COMPLETENESS:\s*(\d+)', response_text)
        if completeness_match:
            result["completeness"] = int(completeness_match.group(1))

        style_match = re.search(r'STYLE:\s*(\d+)', response_text)
        if style_match:
            result["style"] = int(style_match.group(1))

        summary_match = re.search(r'SUMMARY:\s*(.+)', response_text)
        if summary_match:
            result["summary"] = summary_match.group(1).strip()

    except Exception as e:
        print(f"  [WARNING] Could not parse confidence response: {e}")

    return result


def get_confidence_label(score):
    """
    Converts a numeric score into a human readable label
    and a decision about what to do with the fix.
    """
    if score >= 85:
        return "HIGH", "auto-apply"
    elif score >= 50:
        return "MEDIUM", "human-review"
    else:
        return "LOW", "rejected"


def modernize_issue(issue, full_code):
    """
    Takes one deprecated pattern and the full C++ file content,
    runs a 3-stage prompt chain with confidence scoring,
    and returns modernized code + confidence report.
    """

    print(f"\n  {'='*45}")
    print(f"  [ISSUE] {issue['description']}")
    print(f"  {'='*45}")

    # ---------- PROMPT 1: Explain the problem ----------
    prompt1 = f"""You are a C++ expert. Look at this deprecated pattern found in C++ code:

Issue type: {issue['type']}
Line number: {issue['line']}
Description: {issue['description']}

Full source code:
{full_code}

Explain in 2-3 sentences why this pattern is problematic in modern C++."""

    response1 = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt1}],
        max_tokens=200
    )
    explanation = response1.choices[0].message.content
    print(f"\n  [EXPLANATION] {explanation[:150]}...")

    # ---------- PROMPT 2: Generate modernized code ----------
    prompt2 = f"""You are a C++ expert. Here is a C++ file with a deprecated pattern:

Issue: {issue['description']}

Full source code:
{full_code}

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
{modernized_code}

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
    print(f"  [REVIEW] {review}")

    # ---------- PROMPT 4: Confidence scoring ----------
    print(f"\n  [SCORING] Calculating confidence score...")
    confidence_raw = get_confidence_score(issue, full_code, modernized_code)
    confidence = parse_confidence_response(confidence_raw)

    score = confidence["total_score"]
    label, decision = get_confidence_label(score)

    print(f"\n  [SCORE]  {score}/100 ({label})")
    print(f"           Correctness  : {confidence['correctness']}/25")
    print(f"           Safety       : {confidence['safety']}/25")
    print(f"           Completeness : {confidence['completeness']}/25")
    print(f"           Style        : {confidence['style']}/25")
    print(f"           Summary      : {confidence['summary']}")
    print(f"  [DECISION] {decision.upper()}")

    # ---------- Make decision based on confidence ----------
    if review.startswith("APPROVED") and decision == "auto-apply":
        print(f"  [APPLIED] Fix automatically applied (high confidence)")
        return modernized_code, confidence, decision

    elif decision == "human-review":
        print(f"  [REVIEW NEEDED] Fix flagged for human review (medium confidence)")
        return modernized_code, confidence, decision

    else:
        print(f"  [REJECTED] Fix rejected (low confidence or review failed)")
        return full_code, confidence, decision


def modernize_file(issues, filepath):
    """
    Takes all issues found by parser and modernizes them one by one.
    Returns modernized code AND a full confidence report.
    """
    with open(filepath, "r") as f:
        current_code = f.read()

    confidence_report = []

    for issue in issues:
        current_code, confidence, decision = modernize_issue(
            issue, current_code
        )
        confidence_report.append({
            "issue": issue["description"],
            "score": confidence["total_score"],
            "label": get_confidence_label(confidence["total_score"])[0],
            "decision": decision,
            "breakdown": {
                "correctness": confidence["correctness"],
                "safety": confidence["safety"],
                "completeness": confidence["completeness"],
                "style": confidence["style"]
            },
            "summary": confidence["summary"]
        })

    return current_code, confidence_report


def print_final_report(confidence_report):
    """
    Prints a clean summary report of all fixes and their confidence scores.
    """
    print("\n" + "="*50)
    print("  CONFIDENCE REPORT")
    print("="*50)

    auto_applied  = [r for r in confidence_report if r["decision"] == "auto-apply"]
    needs_review  = [r for r in confidence_report if r["decision"] == "human-review"]
    rejected      = [r for r in confidence_report if r["decision"] == "rejected"]

    print(f"\n  [PASS]  Auto-applied  : {len(auto_applied)} fix(es)")
    print(f"  [WARN]  Needs review  : {len(needs_review)} fix(es)")
    print(f"  [FAIL]  Rejected      : {len(rejected)} fix(es)")

    print(f"\n  Detailed breakdown:")
    for i, r in enumerate(confidence_report, 1):
        if r["decision"] == "auto-apply":
            tag = "[PASS]"
        elif r["decision"] == "human-review":
            tag = "[WARN]"
        else:
            tag = "[FAIL]"

        print(f"\n  [{i}] {tag} Score: {r['score']}/100 ({r['label']})")
        print(f"       Issue    : {r['issue']}")
        print(f"       Decision : {r['decision'].upper()}")
        print(f"       Summary  : {r['summary']}")

    avg_score = sum(r["score"] for r in confidence_report) / len(confidence_report)
    print(f"\n  Average confidence score : {avg_score:.1f}/100")
    print("="*50)


if __name__ == "__main__":
    from parser import parse_cpp_file

    filepath = os.path.join(os.path.dirname(__file__), "sample_cpp", "legacy.cpp")
    issues = parse_cpp_file(filepath)

    print(f"Found {len(issues)} issues. Starting modernization...\n")
    modernized, confidence_report = modernize_file(issues, filepath)

    output_path = os.path.join(
        os.path.dirname(__file__), "sample_cpp", "modern.cpp"
    )
    with open(output_path, "w") as f:
        f.write(modernized)

    print(f"\n  [SAVED] Modernized code saved to sample_cpp/modern.cpp")
    print_final_report(confidence_report)