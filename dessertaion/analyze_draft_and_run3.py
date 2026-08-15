import re
import pandas as pd
import numpy as np

draft_text = """# Chapter 4 – Results

## 4.1 Introduction and Experimental Coverage

This chapter reports outcomes from the supplied implementation and exported experimental records. The implementation defines three models—qwen2.5:3b, gemma2:2b and deepseek-r1:1.5b—and three datasets: BoolQ, DBPedia 14 and Rotten Tomatoes. The matrix defines four study types: Prompt Structure, Example Count, Example Selection and Example Ordering, with two runs each. However, the export is not a complete joined matrix.

The experiments file contains 100 experiment definitions, whereas the run export contains 50 experiment identifiers and 100 run records; 34 run records refer to experiment identifiers absent from the definition export. Across 100 run records, 92 completed and eight failed; among 66 attributable runs, 62 completed and four failed. These attributable results cover DBPedia 14 with DeepSeek R1 1.5B, and Rotten Tomatoes with Qwen 2.5 3B and Gemma 2 2B. BoolQ has dataset information but no attributable result runs in the supplied export. Therefore, comparisons are restricted to matched dataset, model and configuration conditions.

## 4.2 Overall Performance

The directly attributable results show substantial differences across the matched dataset-model conditions. On DBPedia 14, DeepSeek R1 1.5B achieved mean accuracy values from 0.0625 to 0.4444 across completed configuration pairs, with corresponding mean F1 values ranging from 0.0370 to 0.3077. The highest directly attributable mean accuracy was 0.4444 for the 1-shot Example Count condition and also for the 3-shot Example Count condition. On Rotten Tomatoes, Qwen 2.5 3B reached 0.4097 mean accuracy under Example-Based 3-shot prompting, while its Instruction 3-shot condition reached 0.3722. Gemma 2 2B reached 0.7000 for 3-shot Example Count, the highest attributable mean accuracy in the exported matched set.

For DBPedia, the directly attributable completed configurations also included ordering and selection variants, permitting condition-level comparisons without mixing datasets. The Random 3-shot Original selection result had mean accuracy 0.0625 in its Example Selection study, whereas the corresponding Balanced condition reached 0.4107. The Ordering study produced 0.3500 for Original, 0.3889 for Random and 0.2111 for Similarity. These values are repeated-run means from two runs and should not be interpreted as a global model ranking. For Rotten Tomatoes, Qwen's attributable results ranged from 0.0000 to 0.4097, while Gemma's ranged from 0.0000 to 0.7000. The difference is reported only within the same dataset because the experiments do not provide identical cross-dataset task conditions.

All reported means use the two recorded runs.

## 4.3 Effect of Prompt Structure

Prompt Structure comparisons are available for all three matched model-dataset combinations, although the results should not be pooled across datasets. On Rotten Tomatoes, Qwen 2.5 3B produced mean accuracies of 0.3722 for Instruction, 0.4097 for Example-Based, and 0.3125 for Mixed 3-shot prompts. Their corresponding mean F1-scores were 0.2308, 0.1935 and 0.1409. For that dataset, Gemma 2 2B recorded 0.0000 accuracy and 0.0000 F1 for all three structures. On DBPedia 14, DeepSeek R1 1.5B recorded 0.1000 accuracy and 0.0909 F1 for the Mixed 3-shot Prompt Structure configuration. Direct structural comparisons are therefore strongest for Rotten Tomatoes Qwen, where the three structures were executed under the same nominal 3-shot condition.

The latency measurements associated with the Qwen Rotten Tomatoes structural comparison differed: Instruction averaged 3,273.8 ms, Example-Based 3,263.0 ms and Mixed 3,561.3 ms. Thus, the structure that recorded the highest accuracy was not the structure with the lowest recorded latency. For Gemma, the structural comparison recorded 480.6 ms for Instruction, 733.7 ms for Example-Based and 345.1 ms for Mixed, while all three accuracy values were zero. DeepSeek's DBPedia Mixed condition averaged 419.5 ms. No significance test was performed, so the observed differences are reported descriptively rather than as statistically significant effects.

## 4.4 Effect of Example Count

Example Count experiments explicitly define 0-, 1-, 3- and 5-shot Mixed configurations with Random selection and Original ordering. For DBPedia 14 with DeepSeek R1 1.5B, mean accuracy was 0.1500 at 0-shot, 0.4444 at 1-shot, 0.4444 at 3-shot, and 0.3889 at 5-shot. Mean F1 values were 0.1288, 0.3077, 0.3077 and 0.2788 respectively. For Rotten Tomatoes, Qwen 2.5 3B recorded 0.0000 accuracy across all four counts, with 0.0000 F1 throughout. Gemma 2 2B recorded 0.0000 at 0-, 1-, 3-shot and 0.5000 at 5-shot, with F1 values of 0.0000, 0.0000, 0.4118 and 0.3333 respectively. These results show that increasing example count did not produce a uniform performance progression across the matched conditions.

The repeated runs show different count effects between the two Rotten Tomatoes models. Gemma's 0-shot and 1-shot conditions both produced 0.0000 accuracy, whereas 3-shot increased to 0.7000 and 5-shot decreased to 0.5000. Qwen remained at 0.0000 for all four counts. DeepSeek on DBPedia increased from 0-shot to 1-shot, remained at the same mean accuracy at 3-shot, and then declined at 5-shot. Latency did not simply increase with example count. For DeepSeek, mean latency was 566.2 ms, 3,417.3 ms, 3,352.8 ms and 3,376.6 ms for 0-, 1-, 3- and 5-shot conditions respectively. For Qwen, the corresponding means were 482.8, 496.8, 473.2 and 472.2 ms. Gemma recorded 335.5, 342.6, 338.1 and 359.3 ms.

## 4.5 Effect of Example Selection

Example Selection comparisons use Random, Balanced and Sequential selection at 3-shot with Original ordering. On DBPedia with DeepSeek R1 1.5B, Random selection produced mean accuracy 0.0625, Balanced 0.4107, while Sequential runs were both failed and therefore have no valid accuracy. F1 values for the completed Random and Balanced conditions were 0.0370 and 0.2485. On Rotten Tomatoes, Qwen 2.5 3B produced 0.0000 accuracy for both Random and Balanced, while Sequential runs failed. Gemma produced 0.0000 for Random and 0.1000 for Balanced. Because Sequential execution failed in both matched DBPedia and Rotten Tomatoes Qwen conditions, no performance comparison can be made for that selection strategy.

Selection results show that accuracy and consistency did not move together. DeepSeek's Balanced DBPedia condition had the highest selection-study mean accuracy, 0.4107, but its consistency was 0.6339, below Random's 0.8125. Qwen's Random and Balanced Rotten Tomatoes conditions both had zero accuracy, while their mean consistency values were 0.9500 and 1.0000 respectively. Gemma's Balanced condition reached 0.1000 accuracy with consistency 1.0000.

## 4.6 Effect of Example Ordering

Example Ordering was evaluated through Original, Random and Similarity ordering at 3-shot, with Random selection. For DBPedia 14 with DeepSeek R1 1.5B, mean accuracy was 0.3500 for Original, 0.3889 for Random, and 0.2111 for Similarity. Mean F1 values were 0.1291, 0.2788 and 0.1162 respectively. For Rotten Tomatoes, Qwen 2.5 3B recorded 0.0000 accuracy and 0.0000 F1 for all three ordering conditions. The DBPedia results therefore provide a direct within-condition ordering comparison, whereas the Rotten Tomatoes Qwen results show no recorded accuracy separation. Gemma 2 2B has no attributable completed Ordering configurations in the export.

Latency differed across ordering for DeepSeek on DBPedia: Original averaged 3,089.2 ms, Random 3,426.8 ms and Similarity 3,231.7 ms. For Qwen on Rotten Tomatoes, ordering means were 483.0, 453.8 and 478.1 ms respectively. The Similarity condition therefore did not provide the lowest latency in either directly attributable ordering set. Because Gemma ordering results are absent from the attributable export, no ordering comparison is reported for that model.

## 4.7 Efficiency Results

Latency was recorded in milliseconds and averaged across two repeated runs for configurations. DBPedia 14 DeepSeek R1 1.5B showed mean latency from 419.5 ms for its Mixed 3-shot Prompt Structure configuration to 3,444.6 ms for Random selection. Its 0-shot Example Count condition averaged 566.2 ms. Rotten Tomatoes Qwen 2.5 3B ranged from 437.3 ms for Balanced selection to 3,561.3 ms for Mixed Prompt Structure; the Instruction and Example-Based structures averaged 3,273.8 ms and 3,263.0 ms. Reported values are completed-run means.

Gemma 2 2B remained between 335.5 and 733.7 ms across attributable conditions. Token measurements are incomplete: only ten raw DeepSeek Rotten Tomatoes runs contain token counts, with input totals from 1,589 to 1,619 and output totals from 2,688 to 3,123 tokens. The matched run export contains no corresponding token fields. The response export records latency and input/output tokens for ten DeepSeek Rotten Tomatoes runs, but these reference identifiers absent from the definition table. Consequently, those token values are reported as raw evidence rather than assigned to a configuration.

## 4.8 Reliability and Consistency

Each attributable configuration was evaluated using two repeated runs for direct comparison. Across 33 attributable configurations, mean accuracy standard deviation was 0.0287, with a maximum of 0.2273; the mean accuracy range was 0.0406 and the maximum range was 0.3214. The largest accuracy variation occurred for DBPedia 14 DeepSeek R1 1.5B Balanced selection, where the runs averaged 0.4107 but differed by 0.3214. Consistency values also varied: the Balanced configuration averaged 0.6339, while many Rotten Tomatoes Gemma configurations recorded 1.0000.

Four attributable runs failed, all belonging to Sequential selection conditions. The export therefore demonstrates repeated-run stability in many conditions and variability in selected conditions, without supporting significance testing.

For the 33 attributable configurations, latency standard deviation between the two runs averaged 68.78 ms, while the maximum was 698.36 ms. The corresponding maximum latency range was 987.63 ms. These values indicate that timing repeatability was less uniform than accuracy repeatability in some configurations, especially within the Qwen Rotten Tomatoes Mixed Prompt Structure condition.

## 4.9 Summary of Findings

The exported evidence establishes a partial experimental result set rather than the factorial design defined by the implementation. Directly attributable results cover DBPedia 14 with DeepSeek R1 1.5B and Rotten Tomatoes with Qwen 2.5 3B and Gemma 2 2B; BoolQ is registered but has no attributable result runs. Within comparable conditions, prompt structure, example count, selection and ordering produced different recorded outcomes.

The clearest structural separation occurred for Rotten Tomatoes Qwen, where Example-Based 3-shot reached 0.4097 accuracy compared with 0.3722 for Instruction and 0.3125 for Mixed. Example count was non-monotonic for DBPedia DeepSeek and Gemma Rotten Tomatoes. Selection and ordering results were dataset-model dependent, while Sequential selection failed in both matched DBPedia and Rotten Tomatoes Qwen conditions. Latency also varied substantially, and token evidence remained incomplete. These findings define the empirical boundaries for the interpretation developed in Chapter 5.

The results therefore support descriptive comparisons, but not a complete factorial conclusion or significance claim. These remain purely descriptive results only.
"""

def parse_sections(text):
    sections = re.split(r'## (4\.\d [^\n]+)', text)
    sec_dict = {}
    for i in range(1, len(sections), 2):
        sec_title = sections[i].strip()
        sec_content = sections[i+1].strip()
        sec_dict[sec_title] = sec_content
    return sec_dict

sec_dict = parse_sections(draft_text)

print("=== WORD COUNT AND PARAGRAPH ANALYSIS OF DRAFT ===")
total_words = 0
target_counts = {
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

for title, content in sec_dict.items():
    words = len(content.split())
    total_words += words
    paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
    para_word_counts = [len(p.split()) for p in paragraphs]
    target = target_counts.get(title, 0)
    print(f"[{title}]")
    print(f"  Word count: {words} (Target: {target}, Diff: {words - target})")
    print(f"  Paragraph count: {len(paragraphs)}")
    print(f"  Paragraph word counts: {para_word_counts}")
    max_p = max(para_word_counts) if para_word_counts else 0
    if max_p > 90:
        print(f"  WARNING: Paragraph exceeds 90 words threshold! ({max_p} words)")
    print()

print(f"TOTAL WORD COUNT OF DRAFT: {total_words} (Target: 1600, Diff: {total_words - 1600})")
