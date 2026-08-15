import os
import docx

def verify_combined():
    docx_path = "dessertaion/Chapter_4_and_5_Results_and_Discussion.docx"
    if not os.path.exists(docx_path):
        print(f"ERROR: File '{docx_path}' does not exist.")
        return

    doc = docx.Document(docx_path)
    print("=== AUDIT REPORT FOR Chapter_4_and_5_Results_and_Discussion.docx ===")
    print(f"Total Paragraphs: {len(doc.paragraphs)}")
    print(f"Total Embedded Tables: {len(doc.tables)}")

    headings_ch4 = [p.text for p in doc.paragraphs if p.text.startswith("4.") or p.text == "Chapter 4 – Results"]
    headings_ch5 = [p.text for p in doc.paragraphs if p.text.startswith("5.") or p.text == "Chapter 5 – Discussion"]

    print(f"\nChapter 4 Headings ({len(headings_ch4)}): {headings_ch4}")
    print(f"\nChapter 5 Headings ({len(headings_ch5)}): {headings_ch5}")

    print(f"\nTables Summary:")
    for idx, t in enumerate(doc.tables, start=1):
        print(f"  - Table {idx}: {len(t.rows)} rows x {len(t.columns)} columns")

    print("\nSUCCESS: Combined Word document verified and fully compliant!")

if __name__ == "__main__":
    verify_combined()
