import fitz
import sys
import os

def combine_pdfs(pdf1_path, pdf2_path, output_path):
    try:
        print(f"Combining '{pdf1_path}' and '{pdf2_path}'...")
        
        if not os.path.exists(pdf1_path):
            print(f"Error: Could not find first PDF file: '{pdf1_path}'")
            return
            
        if not os.path.exists(pdf2_path):
            print(f"Error: Could not find second PDF file: '{pdf2_path}'")
            return

        doc1 = fitz.open(pdf1_path)
        doc2 = fitz.open(pdf2_path)
        
        # Append all pages from the second PDF into the first
        doc1.insert_pdf(doc2)
        
        doc1.save(output_path)
        
        doc1.close()
        doc2.close()
        
        print(f"Successfully saved combined PDF to: '{output_path}'")
        
    except Exception as e:
        print(f"An error occurred while combining PDFs: {str(e)}")

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python combine.py <pdf1_path> <pdf2_path> <output_pdf_path>")
        print("Example: python combine.py doc1.pdf doc2.pdf merged.pdf")
    else:
        file1 = sys.argv[1]
        file2 = sys.argv[2]
        output_file = sys.argv[3]
        combine_pdfs(file1, file2, output_file)
