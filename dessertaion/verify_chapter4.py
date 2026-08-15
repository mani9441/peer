import re
import sys

def verify_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        text = f.read()

    sections = re.split(r'## (4\.\d [^\n]+)', text)
    if len(sections) < 19:
        print(f"Error: expected 9 sections, found {len(sections)//2}")
        return False

    sec_dict = {}
    for i in range(1, len(sections), 2):
        sec_title = sections[i].strip()
        sec_content = sections[i+1].strip()
        sec_dict[sec_title] = sec_content

    targets = {
        "4.1 Introduction and Experimental Coverage": 150,
        "4.2 Overall Performance": 220,
        "4.3 Effect of Prompt Structure": 200,
        "4.4 Effect of Example Count": 220,
        "4.5 Effect of Example Selection": 160,
        "4.6 Effect of Example Ordering": 160,
        "4.7 Efficiency Results": 170,
        "4.8 Reliability and Consistency": 160,
        "4.9 Summary of Findings": 160
    }

    total_words = 0
    all_ok = True

    print("=== VERIFICATION REPORT FOR:", filepath, "===")
    for title, target in targets.items():
        content = sec_dict.get(title, "")
        words = len(content.split())
        total_words += words
        paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
        para_word_counts = [len(p.split()) for p in paragraphs]
        
        diff = words - target
        status = "OK" if diff == 0 else f"MISMATCH ({diff:+d})"
        if diff != 0:
            all_ok = False
            
        print(f"[{title}]")
        print(f"  Words: {words} / Target: {target} -> {status}")
        print(f"  Paragraphs ({len(paragraphs)}): {para_word_counts}")
        
        for idx, pwc in enumerate(para_word_counts):
            if pwc > 90:
                print(f"  FAILED: Paragraph {idx+1} has {pwc} words (Limit: 90)")
                all_ok = False
            elif pwc < 40 or pwc > 85:
                print(f"  NOTE: Paragraph {idx+1} has {pwc} words (Target range: 60-85)")

    print(f"\nTOTAL WORD COUNT: {total_words} / Target: 1600")
    if total_words != 1600:
        print(f"FAILED: Total word count mismatch ({total_words - 1600:+d} words)")
        all_ok = False
    else:
        print("SUCCESS: Total word count is EXACTLY 1,600 words!")

    return all_ok

if __name__ == "__main__":
    filepath = sys.argv[1] if len(sys.argv) > 1 else "dessertaion/chapter4_results_corrected.md"
    verify_file(filepath)
