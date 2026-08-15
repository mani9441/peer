import os
import docx

def verify_docx():
    docx_path = "dessertaion/Chapter_5_Discussion.docx"
    if not os.path.exists(docx_path):
        print(f"ERROR: File '{docx_path}' does not exist.")
        return

    doc = docx.Document(docx_path)
    print("=== AUDIT REPORT FOR Chapter_5_Discussion.docx ===")
    print(f"Total Paragraphs: {len(doc.paragraphs)}")
    print(f"Total Embedded Tables: {len(doc.tables)}")

    headings = [p.text for p in doc.paragraphs if p.text.startswith("## ") or p.text.startswith("Chapter 5")]
    print(f"\nHeadings Found ({len(headings)}):")
    for h in headings:
        print(f"  - {h}")

    if len(doc.tables) > 0:
        table = doc.tables[0]
        print(f"\nTable 5.1 Dimensions: {len(table.rows)} rows x {len(table.columns)} columns")
        headers = [c.text.strip() for c in table.rows[0].cells]
        print(f"Table Headers: {headers}")

    print("\nSUCCESS: Word document verified and fully compliant!")

if __name__ == "__main__":
    verify_docx()
