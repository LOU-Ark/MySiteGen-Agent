import os
import sys
import json
import shutil
import re 
import time 
from google import genai
from datetime import datetime

# モジュールをインポート
from agents.agent_03_generation import generate_single_page_html
from agents.agent_04_improvement import (
    analyze_article_structure,
    generate_article_purpose,
    select_priority_section_by_data,
    generate_priority_article_titles
)
from utils.file_utils import (
    get_existing_article_count,
    integrate_content_data,
    save_to_markdown,
    load_markdown_table_to_list
)
from utils.analysis_utils import create_placeholder_data
from main_03_inject_tags import main as inject_tags_main

# --- 0. 設定 ---
PROJECT_ROOT_PATH = "/content/MySiteGen-Agent" 
BASE_DIR = os.path.join(PROJECT_ROOT_PATH, "output", "docs")
REPORTS_DIR = os.path.join(PROJECT_ROOT_PATH, "output", "output_reports")

REPORT_FILE = os.path.join(REPORTS_DIR, "planned_articles.md")
DEFAULT_ARTICLE_COUNT = 3

def setup_client():
    try:
        from google.colab import userdata
        GOOGLE_API_KEY = userdata.get('GEMINI_API_KEY')
        if not GOOGLE_API_KEY: raise ValueError("No API KEY")
        return genai.Client(api_key=GOOGLE_API_KEY)
    except ImportError:
        GOOGLE_API_KEY = os.environ.get('GEMINI_API_KEY')
        if not GOOGLE_API_KEY: raise EnvironmentError("No API KEY")
        return genai.Client(api_key=GOOGLE_API_KEY)
    except Exception as e:
        print(f"❌ クライアント初期化エラー: {e}")
        return None

def load_corporate_identity():
    identity_file = os.path.join(REPORTS_DIR, "01_identity.md")
    try:
        with open(identity_file, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"❌ ID読み込み失敗: {e}")
        try:
            from agents.agent_01_identity import generate_corporate_identity
            opinion_path = os.path.join(PROJECT_ROOT_PATH, "config", "opinion.txt")
            with open(opinion_path, 'r', encoding='utf-8') as f:
                return generate_corporate_identity(setup_client(), f.read(), 'personal')
        except: return "パーパス: データによる個人の生活最適化。"

def main():
    print(f"--- 🔄 HP改善サイクル (フェーズ5-8) [戦略的バランスモード] 開始 ---")
    gemini_client = setup_client()
    if gemini_client is None: sys.exit(1)
    CORPORATE_IDENTITY = load_corporate_identity()
    
    if "法人格" in CORPORATE_IDENTITY or "corporate" in CORPORATE_IDENTITY: SITE_TYPE = 'corporate'
    else: SITE_TYPE = 'personal'
    print(f"✅ サイトタイプ: {SITE_TYPE}")

    # --- 5a. 戦略（AS-IS分析）---
    processed_articles = []
    if os.path.exists(REPORT_FILE):
        processed_articles = load_markdown_table_to_list(REPORT_FILE)
        processed_articles = [r for r in processed_articles if not r.get('file_name', '').startswith(':---')]
        print(f"✅ 計画ファイルから {len(processed_articles)} 件読み込み")
    else:
        print(f"⚠️ 計画ファイルなし。実ファイルスキャン開始。")
        if not os.path.isdir(BASE_DIR): sys.exit(1)
        current_time_iso = datetime.now().isoformat()
        for root, _, files in os.walk(BASE_DIR):
            for filename in files:
                if filename.lower().endswith(('.html', '.htm')):
                    full_path = os.path.join(root, filename)
                    ad, _ = analyze_article_structure(full_path)
                    if ad:
                        processed_articles.append({
                            "file_name": os.path.relpath(full_path, BASE_DIR).replace(os.path.sep, '/'),
                            "title": ad['page_title'],
                            "summary": generate_article_purpose(gemini_client, ad, CORPORATE_IDENTITY),
                            "created_at": current_time_iso, "updated_at": ""
                        })

    # 5a-2. バランス分析
    hub_counts = {}
    for p in processed_articles:
        if p.get('file_name', '').endswith('index.html'): hub_counts[p['file_name']] = 0
    for p in processed_articles:
        if not p.get('file_name', '').endswith('index.html'):
            parent_hub = os.path.join(os.path.dirname(p.get('file_name', '')), 'index.html').replace(os.path.sep, '/')
            if parent_hub in hub_counts: hub_counts[parent_hub] += 1
    
    balance_report = "| ハブページ | 記事数 |\n| :--- | :--- |\n"
    for hub, count in hub_counts.items():
        if 'legal/' not in hub and 'contact/' not in hub and 'projects/' not in hub:
             if 'about/' not in hub:
                balance_report += f"| {hub} | {count} |\n"

    # --- 5b. 戦略的優先度の決定 ---
    print("\n--- [フェーズ5b] ---")
    analysis_target = [p for p in processed_articles if not p.get('file_name', '').startswith('projects/')]
    priority_result = select_priority_section_by_data(
        gemini_client, create_placeholder_data(analysis_target), 
        CORPORATE_IDENTITY, analysis_target, balance_report
    )
    priority_file = priority_result['file_name']
    try:
        priority_section_info = next(p for p in processed_articles if p['file_name'] == priority_file)
    except StopIteration:
        # フォールバック: insights または 最初のハブ
        fallback = next((p for p in processed_articles if p['file_name'] == 'insights/index.html'), None)
        if not fallback: fallback = next((p for p in processed_articles if p['file_name'].endswith('index.html')), None)
        if not fallback: sys.exit(1)
        priority_section_info = fallback
        priority_file = fallback['file_name']
        print(f"⚠️ フォールバック: {priority_file}")

    print(f"🥇 最優先: {priority_section_info['title']}")

    # --- 6. 詳細記事の企画 ---
    print("\n--- [フェーズ6] ---")
    max_num = 0
    for p in processed_articles:
        m = re.search(r'-(\d+)\.html$', p.get('file_name', ''))
        if m and int(m.group(1)) > max_num: max_num = int(m.group(1))
    start_number = max_num + 1
    
    # リトライロジック
    article_plans = None
    for attempt in range(3):
        _, article_plans = generate_priority_article_titles(
            gemini_client, priority_section_info, CORPORATE_IDENTITY, DEFAULT_ARTICLE_COUNT, start_number
        )
        if article_plans: break
        print(f"⚠️ 企画失敗。リトライ {attempt+1}/3")
        time.sleep(10 * (attempt + 1))

    if not article_plans: sys.exit(1)
    
    current_time_iso = datetime.now().isoformat()
    for plan in article_plans:
        plan['created_at'] = current_time_iso; plan['updated_at'] = ""

    # --- 7. HTML生成 ---
    print("\n--- [フェーズ7] ---")
    new_article_files_generated = []
    nav_list = [{"file_name": p['file_name'], "title": p['title'], "purpose": p.get('summary', '')} for p in processed_articles]

    for i, plan in enumerate(article_plans):
        target_dir = os.path.dirname(priority_section_info['file_name'])
        file_name = os.path.join(target_dir, plan.get('file_name', f'error-{i}.html')).replace(os.path.sep, '/')
        plan['file_name'] = file_name
        print(f"🏭 {plan['title']}")
        
        code = generate_single_page_html(
            gemini_client, {'title': plan['title'], 'file_name': file_name, 'purpose': plan['summary']},
            CORPORATE_IDENTITY, None, nav_list, SITE_TYPE=SITE_TYPE, retry_attempts=3, article_date=plan['created_at']
        )
        if "❌" not in code:
            path = os.path.join(BASE_DIR, file_name)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f: f.write(code)
            new_article_files_generated.append(plan)

    # --- 8. ハブ更新 ---
    print("\n--- [フェーズ8] ---")
    all_plans = integrate_content_data(processed_articles, article_plans)
    hub_path = priority_file
    newly_updated_hubs = []
    
    try:
        parent = next(p for p in all_plans if p['file_name'] == hub_path)
        parent['updated_at'] = current_time_iso
        newly_updated_hubs.append(parent)
        
        children = [p for p in all_plans if os.path.dirname(p.get('file_name','')) == os.path.dirname(hub_path) and p['file_name'] != hub_path]
        links_html = "<ul>" + "".join([f"<li><a href='{os.path.basename(p['file_name'])}' class='text-blue-500 hover:underline'>{p['title']}</a>: {p.get('summary','')}</li>" for p in children]) + "</ul>"
        
        nav_list_hub = [{"file_name": p['file_name'], "title": p['title'], "purpose": p.get('summary', '')} for p in all_plans]
        
        # ⬇️ [修正] summary が None の場合のガード処理を追加
        parent_summary = parent.get('summary') or parent.get('purpose') or ""
        
        code = generate_single_page_html(
            gemini_client,
            # ⬇️ [修正] purposeの結合部分を安全に
            {'file_name': parent['file_name'], 'title': parent['title'], 'purpose': parent_summary + f"\n\n【記事リスト】\n{links_html}"},
            CORPORATE_IDENTITY, None, nav_list_hub, SITE_TYPE=SITE_TYPE, retry_attempts=3, article_date=current_time_iso
        )
        if "❌" not in code:
            with open(os.path.join(BASE_DIR, parent['file_name']), 'w', encoding='utf-8') as f: f.write(code)
            print(f"✅ ハブ更新: {parent['file_name']}")
            
    except StopIteration: pass

    # --- 9. 保存 ---
    print("\n--- [フェーズ9] ---")
    os.makedirs(REPORTS_DIR, exist_ok=True)
    save_to_markdown(all_plans, REPORT_FILE)

    # --- 10. X投稿用JSON生成 (URL自動解決版) ---
    print("\n--- [フェーズ10: X投稿リスト生成] ---")
    output_for_x_bot = os.path.join(PROJECT_ROOT_PATH, "newly_updated_articles.json")
    
    github_repo = os.environ.get('GITHUB_REPOSITORY') # 例: LOU-Ark/repo-name
    if github_repo:
        username, repo_name = github_repo.split('/')
        SITE_BASE_URL = f"https://{username}.github.io/{repo_name}/"
        print(f"ℹ️ 自動設定URL: {SITE_BASE_URL}")
    else:
        SITE_BASE_URL = "https://lou-ark.github.io/arche-narrative-portfolio/"
        print(f"⚠️ 環境変数なし。デフォルトURL: {SITE_BASE_URL}")

    articles_for_x = []
    
    for plan in new_article_files_generated:
        articles_for_x.append({
            "theme": plan['title'],
            "keywords": ["AI", "QoL", "sophia-echoes", "知見"],
            "main_url": os.path.join(SITE_BASE_URL, plan['file_name']).replace(os.path.sep, '/'),
            "provided_summary": plan.get('summary', '記事の概要')
        })
    
    if articles_for_x:
        with open(output_for_x_bot, 'w', encoding='utf-8') as f:
            json.dump(articles_for_x, f, ensure_ascii=False, indent=2)
        print(f"✅ {len(articles_for_x)} 件の記事情報を保存しました。")
    else:
        print("ℹ️ Xへの通知対象はありません。")

    # --- 11. タグ挿入 ---
    print("\n--- [フェーズ11] ---")
    try: inject_tags_main()
    except: pass

    print("--- 完了 ---")

if __name__ == "__main__":
    if PROJECT_ROOT_PATH not in sys.path: sys.path.append(PROJECT_ROOT_PATH)
    main()
