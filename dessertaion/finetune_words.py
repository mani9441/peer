import re

def check_counts():
    with open("dessertaion/chapter4_results_corrected.md", "r", encoding="utf-8") as f:
        text = f.read()

    sections = re.split(r'## (4\.\d [^\n]+)', text)
    sec_dict = {}
    for i in range(1, len(sections), 2):
        sec_dict[sections[i].strip()] = sections[i+1].strip()

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

    for title, target in targets.items():
        content = sec_dict[title]
        paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
        p_counts = [len(p.split()) for p in paragraphs]
        total = sum(p_counts)
        print(f"[{title}] Total: {total} / Target: {target} (Diff: {total - target:+d}) | Paras: {p_counts}")

check_counts()
