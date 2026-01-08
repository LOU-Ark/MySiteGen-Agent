import os
import sys
import bs4

def fix_links(project_root):
    docs_root = os.path.join(project_root, "docs")
    if not os.path.exists(docs_root):
        print(f"Error: {docs_root} が見つかりません。")
        return

    print(f"Fixing links in {docs_root}...")
    html_files = []
    for root, dirs, files in os.walk(docs_root):
        for file in files:
            if file.endswith(".html"):
                html_files.append(os.path.join(root, file))

    modified_count = 0
    for file_path in html_files:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        soup = bs4.BeautifulSoup(content, "html.parser")
        rel_dir = os.path.relpath(os.path.dirname(file_path), docs_root)
        
        # 階層の深さを判定
        if rel_dir == ".":
            depth = 0
        else:
            depth = len(rel_dir.split(os.sep))

        made_changes = False
        
        # 1. ルートディレクトリにおける "../index.html" 等の誤りを修正
        if depth == 0:
            for a in soup.find_all("a", href=True):
                old_href = a["href"]
                if old_href.startswith("../index.html"):
                    a["href"] = old_href.replace("../index.html", "index.html")
                    print(f"  Fixing root link: {file_path} -> {old_href} to {a['href']}")
                    made_changes = True
                elif old_href == "..":
                    a["href"] = "index.html"
                    print(f"  Fixing root link: {file_path} -> .. to index.html")
                    made_changes = True

        if made_changes:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(str(soup))
            modified_count += 1

    print(f"\n--- Repair Complete ---")
    print(f"Files modified: {modified_count}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python fix_links.py <project_root>")
        sys.exit(1)
    
    fix_links(sys.argv[1])
