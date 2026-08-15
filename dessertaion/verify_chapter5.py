import os
import re

def verify_chapter5(filepath="dessertaion/chapter5_discussion_corrected.md"):
    if not os.path.exists(filepath):
        print(f"ERROR: File '{filepath}' does not exist.")
        return

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    targets = {
        "5.1 Introduction": 80,
        "5.2 Prompt Structure and LLM Performance": 270,
        "5.3 Influence of Few-Shot Example Count": 300,
        "5.4 Example Selection and Ordering Sensitivity": 260,
        "5.5 Performance–Efficiency Trade-offs": 220,
        "5.6 Reliability and Reproducibility": 180,
        "5.7 Comparison with Existing Literature": 160,
        "5.8 Implications of the Findings": 130,
        "5.9 Limitations of the Study": 130,
        "5.10 Discussion Summary": 70
    }

    sec_blocks = re.split(r'## (5\.\d+ [^\n]+)', content)
    sec_dict = {}
    for i in range(1, len(sec_blocks), 2):
        sec_dict[sec_blocks[i].strip()] = sec_blocks[i+1].strip()

    total_words = 0
    all_ok = True

    print(f"=== VERIFICATION REPORT FOR: {filepath} ===")
    for title, target in targets.items():
        text = sec_dict.get(title, "")
        paras = [p.strip() for p in text.split("\n\n") if p.strip()]
        p_counts = [len(p.split()) for p in paras]
        sec_w = sum(p_counts)
        total_words += sec_w
        status = "OK" if sec_w == target else f"MISMATCH ({sec_w - target:+d})"
        if sec_w != target:
            all_ok = False
        print(f"[{title}]")
        print(f"  Words: {sec_w} / Target: {target} -> {status}")
        print(f"  Paragraphs ({len(paras)}): {p_counts}")
        for idx, pw in enumerate(p_counts):
            if pw > 90:
                print(f"  WARNING: Paragraph {idx+1} has {pw} words (Exceeds 90 words limit!)")
                all_ok = False

    print(f"\nTOTAL WORD COUNT: {total_words} / Target: 1800")
    if total_words == 1800 and all_ok:
        print("SUCCESS: Total word count is EXACTLY 1,800 words and all sections match targets!")
    else:
        print(f"FAILED: Word count or paragraph length discrepancy detected.")

if __name__ == "__main__":
    verify_chapter5()
