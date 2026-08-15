import os
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import qn, nsdecls

def set_cell_background(cell, fill_hex):
    tcPr = cell._element.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_hex}"/>')
    tcPr.append(shd)

def set_cell_margins(cell, top=100, bottom=100, left=150, right=150):
    tcPr = cell._element.get_or_add_tcPr()
    tcMar = parse_xml(f'''
        <w:tcMar {nsdecls("w")}>
            <w:top w:w="{top}" w:type="dxa"/>
            <w:bottom w:w="{bottom}" w:type="dxa"/>
            <w:left w:w="{left}" w:type="dxa"/>
            <w:right w:w="{right}" w:type="dxa"/>
        </w:tcMar>
    ''')
    tcPr.append(tcMar)

def set_table_borders(table):
    tblPr = table._element.xpath('w:tblPr')
    if tblPr:
        borders = parse_xml(f'''
            <w:tblBorders {nsdecls("w")}>
                <w:top w:val="single" w:sz="8" w:space="0" w:color="333333"/>
                <w:bottom w:val="single" w:sz="8" w:space="0" w:color="333333"/>
                <w:insideH w:val="single" w:sz="4" w:space="0" w:color="E0E0E0"/>
                <w:left w:val="none"/>
                <w:right w:val="none"/>
                <w:insideV w:val="none"/>
            </w:tblBorders>
        ''')
        tblPr[0].append(borders)

def build_chapter5_docx():
    doc = docx.Document()

    # Page setup - Margins 1 inch
    sections = doc.sections
    for s in sections:
        s.top_margin = Inches(1)
        s.bottom_margin = Inches(1)
        s.left_margin = Inches(1)
        s.right_margin = Inches(1)

    # Base Styles
    normal_style = doc.styles['Normal']
    normal_style.font.name = 'Calibri'
    normal_style.font.size = Pt(11)
    normal_style.font.color.rgb = RGBColor(0x22, 0x22, 0x22)
    normal_style.paragraph_format.line_spacing = 1.15
    normal_style.paragraph_format.space_after = Pt(6)

    # Document Title
    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p_title.paragraph_format.space_after = Pt(12)
    run_title = p_title.add_run("Chapter 5 – Discussion")
    run_title.font.name = 'Calibri'
    run_title.font.size = Pt(22)
    run_title.font.bold = True
    run_title.font.color.rgb = RGBColor(0x1B, 0x36, 0x5D) # Navy accent

    # Read verified corrected markdown text
    with open("dessertaion/chapter5_discussion_corrected.md", "r", encoding="utf-8") as f:
        md_text = f.read()

    # Parse sections from markdown
    sec_blocks = md_text.split("## ")

    for block in sec_blocks[1:]:
        lines = block.strip().split("\n")
        header = lines[0].strip()
        body_paras = [p.strip() for p in "\n".join(lines[1:]).split("\n\n") if p.strip()]

        # Heading 2
        h2 = doc.add_heading(level=2)
        h2.paragraph_format.space_before = Pt(14)
        h2.paragraph_format.space_after = Pt(6)
        h2_run = h2.add_run(header)
        h2_run.font.name = 'Calibri'
        h2_run.font.size = Pt(15)
        h2_run.font.bold = True
        h2_run.font.color.rgb = RGBColor(0x1B, 0x36, 0x5D)

        # Add text paragraphs
        for ptext in body_paras:
            doc.add_paragraph(ptext)

        # Add Executive Synthesis Table after 5.7 Comparison with Existing Literature
        if header.startswith("5.7"):
            p_cap = doc.add_paragraph()
            p_cap.paragraph_format.space_before = Pt(10)
            p_cap.paragraph_format.space_after = Pt(4)
            r_cap = p_cap.add_run("Table 5.1. Analytical Synthesis & Discussion Matrix (Findings vs. Literature vs. Implications)")
            r_cap.bold = True
            r_cap.font.size = Pt(10)

            t_synth = doc.add_table(rows=5, cols=4)
            t_synth.alignment = WD_TABLE_ALIGNMENT.CENTER
            headers = ["Investigation Axis", "Empirical Finding (Run3)", "Theoretical Interpretation & Literature Alignment", "Operational & Research Implication"]
            for i, h in enumerate(headers):
                cell = t_synth.cell(0, i)
                cell.text = h
                set_cell_background(cell, "1B365D")
                set_cell_margins(cell)
                for r in cell.paragraphs[0].runs:
                    r.font.bold = True
                    r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
                    r.font.size = Pt(9.5)

            matrix_data = [
                ["Prompt Structure", "Instruction prompts achieved peak mean accuracy (0.3750) for Gemma, while Qwen remained near zero across structures (ANOVA p=0.2678).", "Explicit instructions condition task constraints effectively for capable models (Liu et al., 2023), but structural sensitivity is not uniform (Mizrahi et al., 2024).", "Prompt structure must be treated as an experimental variable; test multiple formulations rather than assuming universal structure benefits."],
                ["Example Count", "Non-monotonic trajectories: DeepSeek (0.4107 at 1-shot) & Gemma (0.4333 at 1-shot) peaked at 1-shot and declined at 3/5-shot (ANOVA p=0.2013).", "Demonstrations inform through content rather than quantity alone (Min et al., 2022). Extra exemplars introduce context noise (Perez et al., 2021).", "Adding exemplars requires empirical validation; default 3-shot or 5-shot configurations can degrade accuracy relative to 1-shot."],
                ["Selection & Ordering", "DeepSeek favored Random selection (0.3847) & Random order (0.4097); Qwen favored Similarity order (0.2500). Sequential selection failed in 4 runs.", "Demonstration order induces attention biases (Lu et al., 2022; Zhao et al., 2021). Selection effects depend on vector retrieval pipeline health (Wang et al., 2024).", "Treat model + selection/ordering strategy as a combined deployment unit. Audit retrieval vector pipelines to prevent execution failures."],
                ["Efficiency & Reliability", "Qwen fastest (913.3 ms), DeepSeek slowest (3342.0 ms). Gemma 5-shot SD=0.2828. Exactly 8 execution failures logged.", "Inference latency trade-offs are crucial (Alizadeh et al., 2024). Nominal T=0.0 zero-temperature sampling exhibits output variance (Siska et al., 2024).", "Fast latency cannot offset near-zero accuracy. Low variance does not equal high performance. Multi-objective evaluation is mandatory."]
            ]

            for r_idx, rdata in enumerate(matrix_data, start=1):
                bg = "F9FAFB" if r_idx % 2 == 1 else "FFFFFF"
                for c_idx, val in enumerate(rdata):
                    cell = t_synth.cell(r_idx, c_idx)
                    cell.text = val
                    set_cell_background(cell, bg)
                    set_cell_margins(cell)
                    cell.paragraphs[0].runs[0].font.size = Pt(8.5)
            set_table_borders(t_synth)

    # Academic References Section
    h_ref = doc.add_heading(level=2)
    h_ref.paragraph_format.space_before = Pt(18)
    h_ref.paragraph_format.space_after = Pt(6)
    h_ref_run = h_ref.add_run("References")
    h_ref_run.font.name = 'Calibri'
    h_ref_run.font.size = Pt(15)
    h_ref_run.font.bold = True
    h_ref_run.font.color.rgb = RGBColor(0x1B, 0x36, 0x5D)

    refs = [
        "Alizadeh, K., Mirzadeh, S.I., Belenko, D., Khatamifard, S., Cho, M., Del Mundo, C.C., Rastegari, M. and Farajtabar, M. (2024) ‘LLM in a flash: Efficient large language model inference with limited memory’, Proceedings of the 62nd Annual Meeting of the Association for Computational Linguistics (Volume 1: Long Papers), pp. 12562–12584. doi: 10.18653/v1/2024.acl-long.678.",
        "Bommasani, R. et al. (2021) ‘On the opportunities and risks of foundation models’, arXiv preprint, arXiv:2108.07258.",
        "Brown, T.B. et al. (2020) ‘Language models are few-shot learners’, Advances in Neural Information Processing Systems, 33, pp. 1877–1901.",
        "Cahyawijaya, S., Lovenia, H. and Fung, P. (2024) ‘LLMs are few-shot in-context low-resource language learners’, Proceedings of the 2024 Conference of the North American Chapter of the Association for Computational Linguistics: Human Language Technologies (Volume 1: Long Papers), pp. 405–433. doi: 10.18653/v1/2024.naacl-long.24.",
        "Chang, Y. et al. (2024) ‘A survey on evaluation of large language models’, ACM Transactions on Intelligent Systems and Technology, 15(3), Article 39, pp. 1–45. doi: 10.1145/3641289.",
        "Hoffmann, J. et al. (2022) ‘Training compute-optimal large language models’, Advances in Neural Information Processing Systems, 35, pp. 30016–30030.",
        "Jiang, A.Q. et al. (2023) ‘Mistral 7B’, arXiv preprint, arXiv:2310.06825.",
        "Kaplan, J., McCandlish, S., Henighan, T., Brown, T.B., Chess, B., Child, R., Gray, S., Radford, A., Wu, J. and Amodei, D. (2020) ‘Scaling laws for neural language models’, arXiv preprint, arXiv:2001.08361.",
        "Liang, P. et al. (2023) ‘Holistic evaluation of language models’, Transactions on Machine Learning Research.",
        "Liu, P., Yuan, W., Fu, J., Jiang, Z., Hayashi, H. and Neubig, G. (2023) ‘Pre-train, prompt, and predict: A systematic survey of prompting methods in natural language processing’, ACM Computing Surveys, 55(9), Article 195, pp. 1–35. doi: 10.1145/3560815.",
        "Lu, Y., Bartolo, M., Moore, A., Riedel, S. and Stenetorp, P. (2022) ‘Fantastically ordered prompts and where to find them: Overcoming few-shot prompt order sensitivity’, Proceedings of the 60th Annual Meeting of the Association for Computational Linguistics (Volume 1: Long Papers), pp. 8086–8098. doi: 10.18653/v1/2022.acl-long.556.",
        "Min, S., Lyu, X., Holtzman, A., Artetxe, M., Lewis, M., Hajishirzi, H. and Zettlemoyer, L. (2022) ‘Rethinking the role of demonstrations: What makes in-context learning work?’, Proceedings of the 2022 Conference on Empirical Methods in Natural Language Processing, pp. 11048–11064. doi: 10.18653/v1/2022.emnlp-main.759.",
        "Mizrahi, M., Kaplan, G., Malkin, D., Dror, R., Shahaf, D. and Stanovsky, G. (2024) ‘State of what art? A call for multi-prompt LLM evaluation’, Transactions of the Association for Computational Linguistics, 12, pp. 933–949. doi: 10.1162/tacl_a_00681.",
        "OpenAI (2023) ‘GPT-4 Technical Report’, arXiv preprint, arXiv:2303.08774.",
        "Perez, E., Kiela, D. and Cho, K. (2021) ‘True few-shot learning with language models’, Advances in Neural Information Processing Systems, 34, pp. 11054–11070.",
        "Raina, V., Liusie, A. and Gales, M. (2024) ‘Is LLM-as-a-judge robust? Investigating universal adversarial attacks on zero-shot LLM assessment’, Proceedings of the 2024 Conference on Empirical Methods in Natural Language Processing, pp. 7499–7517. doi: 10.18653/v1/2024.emnlp-main.427.",
        "Rubin, O., Herzig, J. and Berant, J. (2022) ‘Learning to retrieve prompts for in-context learning’, Proceedings of the 2022 Conference of the North American Chapter of the Association for Computational Linguistics: Human Language Technologies, pp. 2655–2671. doi: 10.18653/v1/2022.naacl-main.191.",
        "Sclar, M., Choi, Y., Tsvetkov, Y. and Suhr, A. (2024) ‘Quantifying language models’ sensitivity to spurious features in prompt design or: How I learned to start worrying about prompt formatting’, Proceedings of the Twelfth International Conference on Learning Representations (ICLR 2024).",
        "Siska, C., Marazopoulou, K., Ailem, M. and Bono, J. (2024) ‘Examining the robustness of LLM evaluation to the distributional assumptions of benchmarks’, Proceedings of the 62nd Annual Meeting of the Association for Computational Linguistics (Volume 1: Long Papers), pp. 10406–10421. doi: 10.18653/v1/2024.acl-long.560.",
        "Song, Y., Wang, T., Cai, P., Mondal, S.K. and Sahoo, J.P. (2023) ‘A comprehensive survey of few-shot learning: Evolution, applications, challenges, and opportunities’, ACM Computing Surveys, 55(13s), Article 271, pp. 1–40. doi: 10.1145/3582688.",
        "Touvron, H. et al. (2023) ‘Llama 2: Open foundation and fine-tuned chat models’, arXiv preprint, arXiv:2307.09288.",
        "Wang, L., Yang, N. and Wei, F. (2024) ‘Learning to retrieve in-context examples for large language models’, Proceedings of the 18th Conference of the European Chapter of the Association for Computational Linguistics (Volume 1: Long Papers), pp. 1752–1767. doi: 10.18653/v1/2024.eacl-long.105.",
        "Wei, J. et al. (2022) ‘Emergent abilities of large language models’, Transactions on Machine Learning Research.",
        "Zhao, Z., Wallace, E., Feng, S., Klein, D. and Singh, S. (2021) ‘Calibrate before use: Improving few-shot performance of language models’, Proceedings of the 38th International Conference on Machine Learning, 139, pp. 12697–12706.",
        "Zhuo, J., Zhang, S., Fang, X., Duan, H., Lin, D. and Chen, K. (2024) ‘ProSA: Assessing and understanding the prompt sensitivity of LLMs’, Findings of the Association for Computational Linguistics: EMNLP 2024, pp. 1950–1976. doi: 10.18653/v1/2024.findings-emnlp.108."
    ]

    for ref in refs:
        p_ref = doc.add_paragraph()
        p_ref.paragraph_format.space_after = Pt(6)
        p_ref.paragraph_format.left_indent = Inches(0.5)
        p_ref.paragraph_format.first_line_indent = Inches(-0.5)
        r_ref = p_ref.add_run(ref)
        r_ref.font.size = Pt(10)

    output_filename = "dessertaion/Chapter_5_Discussion.docx"
    doc.save(output_filename)
    print(f"SUCCESS: Created Word document at '{output_filename}'!")

if __name__ == "__main__":
    build_chapter5_docx()
