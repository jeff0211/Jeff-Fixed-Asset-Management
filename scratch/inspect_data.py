import os
import pandas as pd

BASE_DIR = r"c:\Users\User\Documents\Python AG"

def find_xls():
    print(f"Listing directory: {BASE_DIR}")
    files = os.listdir(BASE_DIR)
    found = []
    for f in files:
        if f.lower().endswith(".xls"):
            found.append(f)
            print(f"Found Excel: '{f}' (length: {len(f)})")
            for char in f:
                print(f"{char}: {ord(char)}")
    return found[0] if found else None

def inspect_xls(filename):
    if not filename: return
    file_path = os.path.join(BASE_DIR, filename)
    print(f"\n--- Inspecting: {file_path} ---")
    try:
        xl = pd.ExcelFile(file_path)
        print(f"Sheet names: {xl.sheet_names}")
        # Focus on sheets that look important
        for sheet in xl.sheet_names:
            df = pd.read_excel(file_path, sheet_name=sheet, nrows=50)
            print(f"\n--- Sheet: {sheet} (Shape: {df.shape}) ---")
            print(df.head(20).to_string())
    except Exception as e:
        print(f"Error reading XLS: {e}")

if __name__ == "__main__":
    xls = find_xls()
    if xls:
        inspect_xls(xls)
    else:
        print("No XLS file found.")
