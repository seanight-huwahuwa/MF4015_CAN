import argparse
from pypdf import PdfReader

def pdf_to_txt(pdf_file, txt_file):
    try:
        reader = PdfReader(pdf_file)
        total_pages = len(reader.pages)
        print(f"Converting '{pdf_file}' ({total_pages} pages) to '{txt_file}'...")
        
        with open(txt_file, "w", encoding="utf-8") as f:
            for i in range(total_pages):
                page = reader.pages[i]
                text = page.extract_text()
                if text:
                    f.write(f"\n--- Page {i + 1} ---\n")
                    f.write(text)
                    f.write("\n")
                    
        print(f"Successfully converted to {txt_file}")
        
    except FileNotFoundError:
        print(f"Error: File '{pdf_file}' not found.")
    except Exception as e:
        print(f"Error reading PDF: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert an entire PDF file to a TXT file.")
    parser.add_argument("pdf_file", help="Path to the PDF file")
    parser.add_argument("txt_file", help="Path to the output TXT file")
    
    args = parser.parse_args()
    pdf_to_txt(args.pdf_file, args.txt_file)
