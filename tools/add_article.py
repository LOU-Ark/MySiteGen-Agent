import os
import sys
import re
from google import genai
from google.genai import types

# --- 設定 ---
# tools/ から見たルートディレクトリ
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 親ディレクトリのMySiteGen-Agentのユーティリティをインポートするためのパス追加
sys.path.append(ROOT_DIR)
try:
    from utils.client_utils import setup_client
    from agents.agent_03_generation import generate_single_page_html
except ImportError:
    print("Error: MySiteGen-Agentのユーティリティをインポートできませんでした。")
    sys.exit(1)

def find_projects():
    """output_reports/planned_articles.md を含むディレクトリを探す"""
    projects = []
    # 1. ルート直下のディレクトリを探索
    for item in os.listdir(ROOT_DIR):
        item_path = os.path.join(ROOT_DIR, item)
        if os.path.isdir(item_path) and item not in ["agents", "config", "tools", "utils", "venv", "__pycache__", ".git"]:
            if os.path.exists(os.path.join(item_path, "output_reports", "planned_articles.md")):
                projects.append(item_path)
    
    # 2. projects/ ディレクトリ内を探索
    projects_dir = os.path.join(ROOT_DIR, "projects")
    if os.path.exists(projects_dir):
        for item in os.listdir(projects_dir):
            item_path = os.path.join(projects_dir, item)
            if os.path.isdir(item_path):
                if os.path.exists(os.path.join(item_path, "output_reports", "planned_articles.md")):
                    if item_path not in projects:
                        projects.append(item_path)
    
    return projects

def main():
    client = setup_client()
    
    # プロジェクトの自動検出
    projects = find_projects()
    if not projects:
        print("プロジェクトが見つかりませんでした。対象のプロジェクトフォルダに必要なファイル（output_reports/planned_articles.md）があるか確認してください。")
        return

    print("\n対象のプロジェクトを選択してください:")
    for i, p in enumerate(projects):
        print(f"[{i}] {os.path.relpath(p, ROOT_DIR)}")
    
    try:
        sel = int(input("\n選択 (番号): "))
        project_root = projects[sel]
    except (ValueError, IndexError):
        print("無効な選択です。")
        return

    # パスの設定
    DOCS_DIR = os.path.join(project_root, "docs")
    REPORTS_DIR = os.path.join(project_root, "output_reports")
    PLANNED_FILE = os.path.join(REPORTS_DIR, "planned_articles.md")
    IDENTITY_FILE = os.path.join(REPORTS_DIR, "01_identity.md")

    if not os.path.exists(PLANNED_FILE):
        print(f"Error: {PLANNED_FILE} が見つかりません。")
        return

    # 1. 記事一覧の読み取り
    with open(PLANNED_FILE, "r", encoding="utf-8") as f:
        content = f.read()

    articles = []
    lines = content.splitlines()
    for line in lines:
        if line.startswith("|") and not "ファイル名" in line and not "---" in line:
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 4:
                file_path = parts[1]
                title = parts[2]
                purpose = parts[3]
                if file_path.endswith(".html") and "/" in file_path:
                    articles.append({
                        "file_name": file_path,
                        "title": title,
                        "purpose": purpose
                    })

    if not articles:
        print("planned_articles.md 内に記記事データが見つかりませんでした。")
        return

    print(f"\n{len(articles)} 件の記事案が見つかりました。")
    
    # 2. セクションの選択
    sections = sorted(list(set([a["file_name"].split("/")[0] for a in articles])))
    print("\nセクションを選択してください:")
    for i, s in enumerate(sections):
        print(f"[{i}] {s}")
    
    try:
        sel = int(input("\n選択 (番号): "))
        target_section = sections[sel]
    except (ValueError, IndexError):
        print("無効な選択です。")
        return

    section_articles = [a for a in articles if a["file_name"].startswith(target_section + "/")]
    
    print(f"\n'{target_section}' 内の記事:")
    for i, a in enumerate(section_articles):
        full_path = os.path.join(DOCS_DIR, a["file_name"])
        status = "[生成済み]" if os.path.exists(full_path) else "[未生成]"
        print(f"[{i}] {status} {a['title']}")

    try:
        sel_art = int(input("\n生成する記事を選択 (番号): "))
        target_article = section_articles[sel_art]
    except (ValueError, IndexError):
        print("無効な選択です。")
        return

    # 3. 生成
    with open(IDENTITY_FILE, "r", encoding="utf-8") as f:
        identity_content = f.read()

    print(f"\n生成開始: {target_article['title']}...")
    
    html = generate_single_page_html(
        client, 
        target_article, 
        identity_content, 
        None, 
        [], 
        SITE_TYPE="personal"
    )

    if html:
        output_path = os.path.join(DOCS_DIR, target_article["file_name"])
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"生成成功: {output_path}")
    else:
        print("HTMLの生成に失敗しました。")

if __name__ == "__main__":
    main()
