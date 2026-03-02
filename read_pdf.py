import argparse
from pypdf import PdfReader
import sys

def read_pdf(file_path, page_num=None, search_term=None):
    try:
        reader = PdfReader(file_path)
        total_pages = len(reader.pages)
        print(f"Total pages in document: {total_pages}")

        if page_num is not None:
            if 1 <= page_num <= total_pages:
                page = reader.pages[page_num - 1]
                print(f"\n--- Page {page_num} ---")
                print(page.extract_text())
            else:
                print(f"Error: Page number must be between 1 and {total_pages}.")
            return

        if search_term:
            print(f"Searching for '{search_term}'...")
            found = False
            for i in range(total_pages):
                text = reader.pages[i].extract_text()
                if text and search_term.lower() in text.lower():
                    found = True
                    print(f"\n--- Found on Page {i + 1} ---")
                    # 인접한 문맥만 간략히 보여줍니다.
                    idx = text.lower().find(search_term.lower())
                    start = max(0, idx - 100)
                    end = min(len(text), idx + 100)
                    print(f"...{text[start:end]}...")
            if not found:
                print("Search term not found in the document.")
            return
        
        # 페이지 번호나 검색어가 없으면 1페이지 미리보기 제공
        print("\n--- Page 1 (Preview) ---")
        preview_text = reader.pages[0].extract_text()
        print(preview_text[:1000] if preview_text else "No extractable text on page 1.")
        print("\n[!] Please specify a --page number or a --search keyword to read more.")
        
    except FileNotFoundError:
        print(f"Error: File '{file_path}' not found.")
    except Exception as e:
        print(f"Error reading PDF: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract text from a PDF file.")
    parser.add_argument("file", help="Path to the PDF file")
    parser.add_argument("-p", "--page", type=int, help="Specific page number to read (1-based)")
    parser.add_argument("-s", "--search", type=str, help="Keyword to search for in the PDF text")
    
    args = parser.parse_args()
    read_pdf(args.file, args.page, args.search)
