import re
import pandas as pd
import numpy as np

ch5_draft = """# Chapter 5 – Discussion

## 5.1 Introduction

This chapter interprets the Chapter 4 findings against the study’s research objectives and research question. The discussion considers what the observed prompt, example, efficiency and reliability patterns mean for few-shot LLM evaluation, while distinguishing measured effects from plausible explanations. The analysis also positions the findings against established literature on in-context learning, prompt sensitivity, example retrieval, model scaling and evaluation robustness. Because the executed matrix was incomplete, conclusions are deliberately bounded by the tested model–dataset combinations. This keeps interpretation evidence-bounded throughout.

## 5.2 Prompt Structure and LLM Performance

Prompt-structure results indicate that formulation mattered differently across the evaluated model–dataset pairs. On Rotten Tomatoes, Gemma 2 2B recorded 0.3750 mean accuracy with Instruction prompts, compared with 0.0750 for Example-Based and 0.1167 for Mixed prompts. Qwen 2.5 3B recorded 0.0000 for Instruction and Example-Based and 0.0167 for Mixed. The contrast within the same dataset shows that prompt structure cannot be treated as a universally beneficial intervention.

For Gemma, the stronger Instruction result may reflect the value of explicit task specification for a clearly defined classification objective. Liu et al. (2023) describe prompting as a broad design space in which task instructions and demonstrations alter how a model is conditioned. However, the present experiment cannot establish that explicit instruction caused Gemma’s higher score. Mixed prompting also did not improve performance.

The Qwen results qualify this pattern. All three structures remained near zero on Rotten Tomatoes, indicating that structural changes did not recover strong performance for this model–task pairing. The aggregated Prompt Structure ANOVA was non-significant, F(2,89) = 1.363, p = 0.2678, η² = 0.0653. This supports the need for multi-prompt evaluation highlighted by Mizrahi et al. (2024), because a single successful prompt should not be assumed to represent general model capability.

The findings are also consistent with Sclar et al. (2024) and Zhuo et al. (2024), who emphasise sensitivity to prompt formulation and evaluation conditions. This study adds a constrained observation: structural differences were visible within Gemma on one task, while Qwen showed almost no useful response across structures. The evidence supports model- and task-specific prompt evaluation. This distinction is important because structural sensitivity was not uniform across models in this study.

## 5.3 Influence of Few-Shot Example Count

Example-count results provide clear evidence against a simple “more demonstrations are better” assumption. DeepSeek R1 1.5B on DBPedia 14 increased from 0.0625 accuracy at 0-shot to 0.4107 at 1-shot, then declined to 0.3847 at 3-shot and 0.3500 at 5-shot. Gemma 2 2B on Rotten Tomatoes moved from 0.4000 to 0.4333, then fell to 0.1167 and recovered to 0.2000. Qwen remained at 0.0000 for 0-, 1- and 5-shot, with only 0.0167 at 3-shot.

These trajectories suggest that demonstration quantity alone was insufficient to guarantee improvement. Min et al. (2022) argue that demonstrations matter through properties beyond their number, including the information they convey. That perspective is consistent with the present non-monotonic results. Additional examples may provide useful task information, but they also increase contextual material. The experiment did not independently manipulate quality, relevance or composition, so context interference and mismatch remain plausible interpretations rather than demonstrated causes.

Model capacity offers a plausible interpretation, but it cannot be isolated because the models were not evaluated on a common dataset. The significant Model Family ANOVA, F(2,89) = 19.28, p = 1.11 × 10⁻⁷, η² = 0.3022, establishes a model-family difference in the aggregated data, but the incomplete model–dataset matrix prevents attributing that effect solely to model capability. Compact model size may be relevant, but the evidence does not permit a parameter-scale explanation.

The 1-shot peaks are informative: DeepSeek and Gemma both achieved their highest Example Count means at 1-shot, after which performance declined. This is consistent with Perez et al. (2021) and Song et al. (2023), which emphasise that few-shot effectiveness depends on supplied information rather than quantity alone. The non-significant Example Count ANOVA, F(3,88) = 1.597, p = 0.2013, η² = 0.0844, reinforces a configuration-dependent interpretation. Increasing from 1 to 3 or 5 examples should therefore be validated rather than assumed beneficial.

## 5.4 Example Selection and Ordering Sensitivity

Example selection results show that demonstration identity mattered, but direction varied by model and dataset. DeepSeek on DBPedia 14 recorded 0.3847 accuracy with Random selection versus 0.2111 with Balanced. Gemma on Rotten Tomatoes showed the opposite pattern, with 0.1167 for Random and 0.1500 for Balanced. Qwen recorded 0.0167 for Random and 0.0000 for Balanced. These differences indicate that class balance alone cannot be assumed to improve few-shot performance.

Sequential selection provides a methodological caution. DeepSeek’s two scheduled Sequential runs failed because of unindexed vector embeddings, while Qwen had two completed Sequential runs at 0.1000 accuracy and two failures. The successful Qwen result therefore cannot establish superiority. Retrieval-oriented studies such as Rubin et al. (2022) and Wang et al. (2024) support the importance of selecting relevant demonstrations, but this experiment did not independently establish semantic relevance as the cause of any observed difference. Selection quality and execution reliability consequently remain intertwined.

Ordering was similarly configuration-dependent. DeepSeek achieved 0.3847 accuracy with Original, 0.4097 with Random and 0.3125 with Similarity. Qwen showed 0.0167, 0.0500 and 0.2500 respectively, while Gemma had only an executable Original result at 0.1167. This is consistent with Lu et al. (2022) on order sensitivity and Zhao et al. (2021) on positional and label-related biases.

Similarity benefited Qwen, whereas Random benefited DeepSeek. The non-significant Ordering ANOVA, F(2,89) = 1.067, p = 0.3538, η² = 0.0519, therefore supports configuration-specific sensitivity rather than a universal ordering rule. The result also reinforces Mizrahi et al. (2024) and Zhuo et al. (2024): evaluation conditions can materially shape measured model performance within benchmarked settings here.

## 5.5 Performance–Efficiency Trade-offs

The efficiency findings show why accuracy alone is insufficient for deployment. Qwen 2.5 3B recorded the lowest overall mean latency at 913.3 ms on Rotten Tomatoes, Gemma 2 2B averaged 1377.0 ms on the same dataset, and DeepSeek R1 1.5B averaged 3342.0 ms on DBPedia 14. DeepSeek should not be directly speed-ranked against the Rotten Tomatoes models because task and dataset conditions differ. Gemma ranged from 1164.2 ms to 1932.3 ms, while Qwen ranged from 392.7 ms to 2604.2 ms.

Latency did not correspond automatically to quality. Qwen had the lowest overall mean latency among the evaluated pairs but only 0.0421 mean accuracy and 0.0159 mean F1 on Rotten Tomatoes. DeepSeek recorded 3444.6 ms at 0-shot and 3437.8 ms at 1-shot, while Gemma averaged 444.5 total tokens, comprising 161.9 input and 282.6 output tokens. Token fields for DeepSeek and Qwen were unavailable, preventing complete token-efficiency comparison. This is consistent with Alizadeh et al. (2024) on inference efficiency.

Deployment therefore requires a multi-objective choice involving accuracy, F1, latency, tokens and reliability. A faster configuration with poor prediction quality may have limited operational value, while a more accurate configuration with higher latency may be unsuitable for time-sensitive use. Because token evidence is incomplete, available measures should be considered jointly. Model-plus-prompt configuration is therefore a more appropriate deployment unit than model identity alone.

## 5.6 Reliability and Reproducibility

Repeated-run evidence shows that consistency varied substantially across configurations. Gemma’s 5-shot condition produced 0.5000 and 0.1000 accuracy across two runs, giving standard deviation 0.2828 and range 0.4000. DeepSeek’s 1-shot condition produced 0.5714 and 0.2500, with standard deviation 0.2273 and range 0.3214. Despite T=0.0, these results show nominally identical configurations producing materially different outcomes across repeated execution. This keeps interpretation evidence-bounded throughout directly.

The reliability interpretation must remain separate from performance. A configuration with low variance can be consistently poor, and zero variance with zero accuracy would represent stable failure rather than successful reproducibility. This distinction is important because Qwen’s overall Rotten Tomatoes accuracy was only 0.0421 despite its repeated-run evaluation. Reliability should therefore be considered jointly with score magnitude, not substituted for it.

The study also recorded eight failed runs: four associated with unindexed vector embeddings in Sequential selection and four with provider timeouts. These failures matter because reproducibility also depends on stable execution dependencies. Siska et al. (2024) and Mizrahi et al. (2024) emphasise robust evaluation conditions overall. The present failures reinforce that reproducibility concerns extend beyond model outputs to retrieval, execution and provider behaviour.

## 5.7 Comparison with Existing Literature

Several findings support existing few-shot literature. The non-monotonic example-count trajectories are consistent with Min et al. (2022) and Perez et al. (2021), which challenge the assumption that demonstrations help simply because more are supplied. Ordering differences also agree with Lu et al. (2022) and Zhao et al. (2021), whose work identifies sensitivity to demonstration arrangement and prompt-induced biases. The present results reproduce these qualitative patterns under compact open-weight models, while showing that their magnitude differs by model and task.

The study also qualifies broader generalisations. Prompt Structure, Example Count and Example Ordering were not statistically significant in the aggregated ANOVA, whereas Model Family and Dataset Task were significant. This is compatible with Mizrahi et al. (2024), Sclar et al. (2024) and Zhuo et al. (2024), which motivate broader evaluation. Wang et al. (2024) emphasise retrieving useful examples; here, selection effects were model- and dataset-dependent and partly constrained by execution failures. Combined performance, latency and repeated-run reporting therefore adds methodological evidence.

## 5.8 Implications of the Findings

Prompt configuration should be treated as an experimental variable rather than a fixed preprocessing choice in experimental research. Observed differences across structures, counts, selection and ordering show that evaluation can change while the model remains constant. Future studies should therefore report the prompt configuration explicitly and test more than one configuration before attributing performance to the model itself.

The practical implication is configuration-focused. Developers should evaluate multiple prompts, test example counts, examine selection and ordering, measure latency and tokens, and repeat evaluations. The Rotten Tomatoes results show why choosing an LLM alone is insufficient: Gemma and Qwen were evaluated on the same dataset but produced markedly different overall outcomes, while configuration-level variation remained visible within each model. Deployment should consequently treat the model and prompt as a combined operational configuration.

## 5.9 Limitations of the Study

Several limitations constrain validity and generalisability. The model–dataset matrix is incomplete: DeepSeek R1 1.5B was evaluated on DBPedia 14, while Gemma 2 2B and Qwen 2.5 3B were evaluated on Rotten Tomatoes, and BoolQ produced no executed results. The experiment therefore cannot support a universal ranking of all three models. Compact 1.5B–3B models and limited tasks further restrict generalisation.

Token measurements were incomplete, with data available for Gemma but not DeepSeek or Qwen. Eight runs failed because of vector-indexing and provider-timeout problems, while repeated configurations generally relied on two runs. Proposal-to-implementation changes mean conclusions describe executed conditions only. The ANOVA provides aggregate evidence, but incomplete coverage, failed runs and limited repetitions constrain reliability and external validity reported in this chapter. These limitations prevent separating model capability from dataset effects completely.

## 5.10 Discussion Summary

Overall, the discussion indicates that few-shot performance was configuration-dependent rather than governed by example quantity or one universally effective prompt. Prompt structure, count, selection and ordering produced different observed outcomes across the tested pairs, while model and task effects were stronger in the aggregate analysis. Efficiency and reliability also varied. The findings therefore support evaluating the model–prompt configuration under repeated, task-matched conditions, with conclusions bounded by the incomplete experimental matrix.
"""

def parse_sections(text):
    sections = re.split(r'## (5\.\d [^\n]+)', text)
    sec_dict = {}
    for i in range(1, len(sections), 2):
        sec_dict[sections[i].strip()] = sections[i+1].strip()
    return sec_dict

sec_dict = parse_sections(ch5_draft)

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

print("=== AUDIT OF DRAFT CHAPTER 5 ===")
total_words = 0
for title, target in targets.items():
    content = sec_dict.get(title, "")
    paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
    p_words = [len(p.split()) for p in paragraphs]
    sec_w = sum(p_words)
    total_words += sec_w
    diff = sec_w - target
    print(f"[{title}]")
    print(f"  Words: {sec_w} / Target: {target} (Diff: {diff:+d})")
    print(f"  Paragraphs ({len(paragraphs)}): {p_words}")
    for idx, pw in enumerate(p_words):
        if pw > 90:
            print(f"  WARNING: Paragraph {idx+1} has {pw} words (>90 words!)")

print(f"\nTOTAL WORD COUNT: {total_words} / Target: 1800 (Diff: {total_words - 1800:+d})")
