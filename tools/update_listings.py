import os
import sys
import json
import re
from google import genai
from dotenv import load_dotenv

# --- 設定 ---
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(ROOT_DIR)

# .env をロード (Gemini APIキー等)
load_dotenv(os.path.join(ROOT_DIR, ".env"))

from utils.client_utils import setup_client
from agents.agent_03_generation import generate_single_page_html
from config import settings

def load_planned_articles(planned_file):
    """planned_articles.md から記事リストを読み込む"""
    articles = []
    if not os.path.exists(planned_file):
        return articles
    
    try:
        with open(planned_file, "r", encoding="utf-8") as f:
            content = f.read()
            for line in content.splitlines():
                if line.startswith("|") and not "ファイル名" in line and not "---" in line:
                    parts = [p.strip() for p in line.split("|")]
                    if len(parts) >= 4:
                        articles.append({
                            "file_name": parts[1],
                            "title": parts[2],
                            "purpose": parts[3]
                        })
            print(f"  > {len(articles)} 件の記事を計画ファイルから読み込みました。")
    except Exception as e:
        print(f"計画ファイル読み込み失敗: {e}")
    return articles

def extract_gtm_id(html_path):
    if not os.path.exists(html_path): return None
    with open(html_path, "r", encoding="utf-8") as f:
        match = re.search(r"GTM-[A-Z0-9]+", f.read())
        return match.group(0) if match else None

def extract_common_parts(html_path):
    snippets = {"header": None, "footer": None}
    if not os.path.exists(html_path): return snippets
    with open(html_path, "r", encoding="utf-8") as f:
        content = f.read()
        h = re.search(r"<header.*?>.*?</header>", content, re.DOTALL | re.IGNORECASE)
        f = re.search(r"<footer.*?>.*?</footer>", content, re.DOTALL | re.IGNORECASE)
        if h: snippets["header"] = h.group(0)
        if f: snippets["footer"] = f.group(0)
    return snippets

def update_all_listings(project_root):
    """プロジェクト内の全一覧ページを再生成する"""
    docs_dir = os.path.join(project_root, "docs")
    reports_dir = os.path.join(project_root, "output_reports")
    planned_file = os.path.join(reports_dir, "planned_articles.md")
    identity_file = os.path.join(reports_dir, "01_identity.md")
    
    if not os.path.exists(planned_file):
        print(f"  > 計画ファイルが見つかりません: {planned_file}")
        return

    articles = load_planned_articles(planned_file)
    with open(identity_file, "r", encoding="utf-8") as f:
        identity = f.read()
    
    client = setup_client()
    index_path = os.path.join(docs_dir, "index.html")
    gtm_id = extract_gtm_id(index_path)
    common_snippets = extract_common_parts(index_path)

    # セクションの特定 (projects, insights, philosophy, etc.)
    sections = sorted(list(set([a["file_name"].split("/")[0] for a in articles if "/" in a["file_name"]])))
    
    for section in sections:
        list_file = f"{section}/index.html"
        section_articles = [a for a in articles if a["file_name"].startswith(f"{section}/") and not a["file_name"].endswith("index.html")]
        
        target_page = {
            "title": f"{section.capitalize()} | LOU-Ark",
            "file_name": list_file,
            "purpose": f"「{section}」セクションの一覧ページです。登録されている全記事をカード形式で魅力的に紹介してください。"
        }

        print(f"  > 一覧ページ生成中: {list_file} ({len(section_articles)}件の記事)...")
        # Debug: 記事リストの末尾を確認
        if section_articles:
            print(f"    Last article: {section_articles[-1]['file_name']}")

        html = generate_single_page_html(
            client, 
            target_page, 
            identity, 
            None, 
            section_articles, # ここにそのセクションの記事リストを渡す
            GTM_ID=gtm_id,
            SITE_TYPE="personal",
            header_snippet=common_snippets.get("header"),
            footer_snippet=common_snippets.get("footer")
        )

        if html and "❌" not in html:
            output_path = os.path.join(docs_dir, list_file)
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(html)
            print(f"  ✅ 更新完了: {list_file}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python update_listings.py <project_root_path>")
        sys.exit(1)
    
    project_root = sys.argv[1]
    update_all_listings(project_root)
