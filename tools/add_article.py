import os
import sys
import re
import json
import random
from google import genai
from google.genai import types
from datetime import datetime
from dotenv import load_dotenv

# --- 設定 ---
# 環境変数の読み込み
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))
# tools/ から見たルートディレクトリ
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 親ディレクトリのMySiteGen-Agentのユーティリティをインポートするためのパス追加
sys.path.append(ROOT_DIR)
try:
    from utils.client_utils import setup_client
    from agents.agent_03_generation import generate_single_page_html
    from config.settings import MODEL_NAME_PRO
except ImportError:
    print("Error: MySiteGen-Agentのユーティリティまたは設定をインポートできませんでした。")
    sys.exit(1)

def find_projects():
    """output_reports/planned_articles.md を含むディレクトリを探す"""
    projects = []
    for item in os.listdir(ROOT_DIR):
        item_path = os.path.join(ROOT_DIR, item)
        if os.path.isdir(item_path) and item not in ["agents", "config", "tools", "utils", "venv", "__pycache__", ".git"]:
            if os.path.exists(os.path.join(item_path, "output_reports", "planned_articles.md")):
                projects.append(item_path)
    
    projects_dir = os.path.join(ROOT_DIR, "projects")
    if os.path.exists(projects_dir):
        for item in os.listdir(projects_dir):
            item_path = os.path.join(projects_dir, item)
            if os.path.isdir(item_path):
                if os.path.exists(os.path.join(item_path, "output_reports", "planned_articles.md")):
                    if item_path not in projects:
                        projects.append(item_path)
    return projects

def get_next_number(base_docs_dir):
    """docs 配下の全ディレクトリ内のファイル名から最大の数字を探して +1 を返す"""
    max_num = 0
    if not os.path.exists(base_docs_dir):
        return 1
    
    # 探索対象のサブディレクトリ
    subdirs = ['projects', 'insights', 'philosophy', 'about', 'legal']
    
    for subdir in subdirs:
        target_dir = os.path.join(base_docs_dir, subdir)
        if os.path.exists(target_dir):
            for f in os.listdir(target_dir):
                # ファイル名の末尾の数字を抽出 (例: name-37.html -> 37)
                match = re.search(r"-(\d+)\.html$", f)
                if match:
                    num = int(match.group(1))
                    if num > max_num:
                        max_num = num
    
    # ルート直下のリテラルファイルも一応チェック
    for f in os.listdir(base_docs_dir):
        if f.endswith('.html'):
            match = re.search(r"-(\d+)\.html$", f)
            if match:
                num = int(match.group(1))
                if num > max_num:
                    max_num = num

    return max_num + 1

def get_multiline_input(prompt):
    print(prompt)
    print("(入力を完了するには、Windowsなら Ctrl+Z、または 'END' とだけ入力してEnter)")
    lines = []
    while True:
        try:
            line = input()
            if line.strip() == "END":
                break
            lines.append(line)
        except EOFError:
            break
    return "\n".join(lines).strip()

def main():
    client = setup_client()
    MODEL_NAME = MODEL_NAME_PRO
    
    projects = find_projects()
    if not projects:
        print("プロジェクトが見つかりませんでした。")
        return

    print("\n対象のプロジェクトを選択してください:")
    for i, p in enumerate(projects):
        print(f"[{i}] {os.path.relpath(p, ROOT_DIR)}")
    
    try:
        sel = int(input("\n選択 (番号): "))
        project_root = projects[sel]
    except (ValueError, IndexError):
        return

    DOCS_DIR = os.path.join(project_root, "docs")
    REPORTS_DIR = os.path.join(project_root, "output_reports")
    PLANNED_FILE = os.path.join(REPORTS_DIR, "planned_articles.md")
    IDENTITY_FILE = os.path.join(REPORTS_DIR, "01_identity.md")

    print("\n--- 記事作成モード ---")
    print("[1] 全自動作成 (原案からタイトル・目的をAIが生成) ★推奨")
    print("[2] 手動作成 (タイトル・目的を自分で入力)")
    print("[3] 計画済みの記事を生成 (planned_articles.md から選択)")
    
    mode = input("選択 (1, 2, 3): ")

    target_article = None

    if mode == "1":
        # 全自動作成モード
        draft = get_multiline_input("\n実績の原案（メモ、箇条書き、Markdown等）を貼り付けてください:")
        if not draft:
            print("原案が入力されませんでした。")
            return

        print("\nAIが原案からタイトル、目的、ファイル名を考案中...")
        prompt = f"""
        以下の記事原案に基づき、ウェブサイトに掲載するための「タイトル」「目的（概要）」「URL用スラッグ」を考案してください。
        
        【原案】
        {draft}
        
        【出力形式】
        JSON形式で出力してください。
        {{
            "title": "読者を惹きつける魅力的なタイトル",
            "purpose": "この記事が解決する課題や価値の要約（200文字程度）",
            "slug": "英単語をハイフンで繋いだスラッグ（例: looker-studio-automation）"
        }}
        """
        try:
            resp = client.models.generate_content(
                model=MODEL_NAME, 
                contents=prompt,
                config=types.GenerateContentConfig(response_mime_type="application/json")
            )
            data = json.loads(resp.text)
            
            next_num = get_next_number(DOCS_DIR)
            target_article = {
                "title": data["title"],
                "file_name": f"projects/{data['slug']}-{next_num}.html",
                "purpose": data["purpose"],
                "draft": draft,
                "is_new": True
            }
            print(f"\nAIの提案:")
            print(f"  タイトル: {target_article['title']}")
            print(f"  目的: {target_article['purpose']}")
            print(f"  ファイル名: {target_article['file_name']}")
            
            confirm = input("\nこの内容で作成しますか？ (y/n): ")
            if confirm.lower() != 'y':
                print("中断しました。")
                return
        except Exception as e:
            print(f"AIによる構成に失敗しました: {e}")
            return

    elif mode == "2":
        # 手動作成モード
        title = input("記事のタイトル: ").strip()
        print("セクションを選択: [0] projects (実績) [1] insights (知見) [2] philosophy (哲学)")
        sec_sel = input("選択: ")
        section = {"0": "projects", "1": "insights", "2": "philosophy"}.get(sec_sel, "projects")
        purpose = input("記事の概要・目的: ").strip()
        
        print("AIにファイル名を相談中...")
        prompt = f"「{title}」のスラッグを考案してください。出力はスラッグのみ。"
        resp = client.models.generate_content(model=MODEL_NAME, contents=prompt)
        slug = resp.text.strip().lower().replace(".html", "")
        
        next_num = get_next_number(DOCS_DIR)
        target_article = {
            "title": title,
            "file_name": f"{section}/{slug}-{next_num}.html",
            "purpose": purpose,
            "is_new": True
        }
        draft = get_multiline_input("\n記事の原案を入力しますか？ (なければAIにお任せ、空でEnter):")
        if draft:
            target_article["draft"] = draft

    elif mode == "3":
        # 既存計画モード
        with open(PLANNED_FILE, "r", encoding="utf-8") as f:
            content = f.read()
        articles = []
        for line in content.splitlines():
            if line.startswith("|") and not "ファイル名" in line and not "---" in line:
                parts = [p.strip() for p in line.split("|")]
                if len(parts) >= 4:
                    articles.append({"file_name": parts[1], "title": parts[2], "purpose": parts[3]})
        
        sections = sorted(list(set([a["file_name"].split("/")[0] for a in articles])))
        print("\nセクションを選択:")
        for i, s in enumerate(sections): print(f"[{i}] {s}")
        sel = int(input("選択: "))
        target_section = sections[sel]
        
        section_articles = [a for a in articles if a["file_name"].startswith(target_section + "/")]
        for i, a in enumerate(section_articles):
            status = "[済]" if os.path.exists(os.path.join(DOCS_DIR, a["file_name"])) else "[未]"
            print(f"[{i}] {status} {a['title']}")
        sel_art = int(input("選択: "))
        target_article = section_articles[sel_art]
    else:
        return

    with open(IDENTITY_FILE, "r", encoding="utf-8") as f:
        identity_content = f.read()

    print(f"\n生成開始: {target_article['title']}...")
    # --- [修正] 今日の日付を取得 (YYYY-MM-DD) ---
    today_str = datetime.now().strftime("%Y-%m-%d")

    html_content = generate_single_page_html(
        client, 
        target_article, 
        identity_content, 
        None, 
        [], 
        SITE_TYPE="personal",
        GTM_ID=settings.get("GTM_ID"),
        article_date=today_str # 日付を渡すように修正
    )
    if html_content:
        output_path = os.path.join(DOCS_DIR, target_article["file_name"])
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        print(f"\n✅ 生成成功: {output_path}")

        if target_article.get("is_new"):
            with open(PLANNED_FILE, "a", encoding="utf-8") as f:
                f.write(f"\n| {target_article['file_name']} | {target_article['title']} | {target_article['purpose']} |\n")
            print(f"✅ 計画ファイル ({PLANNED_FILE}) に登録しました。")
    else:
        print("❌ 生成に失敗しました。")

if __name__ == "__main__":
    main()
