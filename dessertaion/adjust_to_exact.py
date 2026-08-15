import re

# Exact target texts
p41_1 = "This chapter reports empirical outcomes derived directly from the verified `Run3` experimental database. The research design specifies three model families—DeepSeek R1 1.5B, Gemma 2 2B, and Qwen 2.5 3B—evaluated across BoolQ, DBPedia 14, and Rotten Tomatoes datasets. The experimental matrix spans four main investigation axes: Prompt Structure, Example Count, Example Selection, and Example Ordering. Each valid experimental configuration was scheduled for execution across two repeated runs to evaluate deterministic performance stability across runs."
p41_2 = "Across the complete matrix, 100 execution runs were logged, comprising 92 completed runs and 8 failed runs. Execution coverage encompasses three attributable model-dataset pairs: Rotten Tomatoes with Gemma 2 2B (36 runs: 34 completed, 2 failed), Rotten Tomatoes with Qwen 2.5 3B (42 runs: 38 completed, 4 failed), and DBPedia 14 with DeepSeek R1 1.5B (22 runs: 20 completed, 2 failed). BoolQ has dataset specifications but zero executed result runs in this exported experimental database dataset."

# Let's adjust word by word
def word_count(text):
    return len(text.split())

print("4.1 p1:", word_count(p41_1))
print("4.1 p2:", word_count(p41_2))
