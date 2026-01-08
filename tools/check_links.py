import os
import sys
import bs4

def check_links(project_root):
    docs_root = os.path.join(project_root, "docs")
    if not os.path.exists(docs_root):
        print(f"Error: {docs_root} が見見つかりません。")
        return

    print(f"Scanning files in {docs_root}...")
    html_files = []
    for root, dirs, files in os.walk(docs_root):
        for file in files:
            if file.endswith(".html"):
                html_files.append(os.path.relpath(os.path.join(root, file), docs_root))

    broken_links = []
    total_links = 0
    for rel_path in html_files:
        full_path = os.path.join(docs_root, rel_path)
        with open(full_path, "r", encoding="utf-8") as f:
            soup = bs4.BeautifulSoup(f, "html.parser")
            
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if href.startswith(("http", "mailto", "#")):
                continue
            
            total_links += 1
            # 内部リンクの存在確認
            target_path = os.path.normpath(os.path.join(os.path.dirname(full_path), href))
            if not os.path.exists(target_path):
                broken_links.append({
                    "source": rel_path,
                    "href": href,
                    "target": target_path
                })

    print(f"\n--- Scan Complete ---")
    print(f"Files checked: {len(html_files)}")
    print(f"Total internal links checked: {total_links}")

    if broken_links:
        print(f"\n[ERROR] {len(broken_links)} 件のリンク切れが見つかりました:")
        for link in broken_links:
            print(f"  Source: {link['source']}")
            print(f"  Href:   {link['href']}")
            print(f"  Reason: Target not found at {link['target']}")
            print("-" * 20)
    else:
        print("\n[SUCCESS] リンク切れは見つかりませんでした！")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python check_links.py <project_root>")
        sys.exit(1)
    
    check_links(sys.argv[1])
