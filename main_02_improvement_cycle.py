import os
import sys
import json
import shutil
import re # ⬅️ [修正] re をインポート
import time # ⬅️ [修正] リトライのために time をインポート
from google import genai
from datetime import datetime
from utils.client_utils import setup_client

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

def load_corporate_identity():
    # ... (この関数は変更なし) ...
    identity_file = os.path.join(REPORTS_DIR, "01_identity.md")
    try:
        with open(identity_file, 'r', encoding='utf-8') as f:
            identity = f.read()
        print(f"✅ 法人格を {identity_file} から読み込みました。")
        return identity
    except Exception as e:
        print(f"❌ 法人格ファイル ({identity_file}) の読み込みに失敗: {e}")
        # (フォールバック)
        try:
            from agents.agent_01_identity import generate_corporate_identity
            opinion_path = os.path.join(PROJECT_ROOT_PATH, "config", "opinion.txt")
            with open(opinion_path, 'r', encoding='utf-8') as f:
                RAW_VISION_INPUT = f.read()
            client = setup_client()
            if client:
                print("⚠️ [フォールバック] 法人格をAPIで再生成します。")
                return generate_corporate_identity(client, RAW_VISION_INPUT, 'personal')
            else:
                raise Exception("クライアントの初期化に失敗")
        except Exception as e_fallback:
            print(f"❌ 代替処理も失敗: {e_fallback}。ダミーを使用します。")
            return "パーパス: データによる個人の生活最適化。 トーン: 論理的、先進的。"

def main():
    print(f"--- 🔄 HP改善サイクル (フェーズ5-8) [戦略的バランスモード] 開始 ---")

    # --- 0. クライアント初期化 ---
    gemini_client = setup_client()
    if gemini_client is None: sys.exit(1)

    # --- (前提) 法人格の取得 ---
    CORPORATE_IDENTITY = load_corporate_identity()

    if "法人格" in CORPORATE_IDENTITY or "corporate" in CORPORATE_IDENTITY:
        SITE_TYPE = 'corporate'
    else:
        SITE_TYPE = 'personal'
    print(f"✅ サイトタイプを '{SITE_TYPE}' と自動判定しました。")

    # --- 5a. 戦略（AS-IS分析）---
    print(f"\n--- [フェーズ5a: AS-IS分析] 計画ファイル ({REPORT_FILE}) を読み込み中 ---")
    processed_articles = None
    if os.path.exists(REPORT_FILE):
        processed_articles = load_markdown_table_to_list(REPORT_FILE)

    if processed_articles:
        processed_articles = [
            row for row in processed_articles 
            if not row.get('file_name', '').startswith(':---')
        ]
        print(f"✅ 既存の計画ファイルから {len(processed_articles)} 件の目的を読み込みました。（APIコールをスキップ）")
    else:
       # (フォールバック ... 変更なし)
        print(f"⚠️ 計画ファイルが見つからないか、読み込みに失敗しました。")
        print(f"--- [フェーズ5a 代替] 既存サイト ({BASE_DIR}) をスキャン中 ---")
        processed_articles = []
        TARGET_EXTENSIONS = ('.html', '.htm')
        if not os.path.isdir(BASE_DIR):
            print(f"❌ 分析対象ディレクトリ {BASE_DIR} が見つかりません。")
            sys.exit(1)
        current_time_iso = datetime.now().isoformat()
        for root, _, files in os.walk(BASE_DIR):
            for filename in files:
                if filename.lower().endswith(TARGET_EXTENSIONS):
                    full_path = os.path.join(root, filename)
                    article_data, error = analyze_article_structure(full_path)
                    if article_data:
                        purpose = generate_article_purpose(gemini_client, article_data, CORPORATE_IDENTITY)
                        processed_articles.append({
                            "file_name": os.path.relpath(full_path, BASE_DIR).replace(os.path.sep, '/'),
                            "title": article_data['page_title'],
                            "summary": purpose,
                            "created_at": current_time_iso,
                            "updated_at": ""
                        })
        print(f"\n✅ [フェーズ5a 代替完了] 合計 {len(processed_articles)} 件の目的をAPIで再定義しました。")
    
    # 5a-2. 「戦略的バランス」の数値化 (変更なし)
    print(f"\n--- [フェーズ5a-2: 戦略的バランスの分析] ---")
    # ... (hub_counts, balance_report のロジック ... 変更なし) ...
    hub_counts = {}
    for p in processed_articles:
        if p.get('file_name', '').endswith('index.html'):
            hub_counts[p['file_name']] = 0
    for p in processed_articles:
        if not p.get('file_name', '').endswith('index.html'):
            parent_dir = os.path.dirname(p.get('file_name', ''))
            parent_hub = os.path.join(parent_dir, 'index.html').replace(os.path.sep, '/')
            if parent_hub in hub_counts:
                hub_counts[parent_hub] += 1
    balance_report = "| ハブページ | 配下の詳細記事数 |\n| :--- | :--- |\n"
    print("✅ 現在のサイトバランス:")
    for hub, count in hub_counts.items():
        if 'legal/' not in hub and 'contact/' not in hub and 'projects/' not in hub:
             if 'about/' not in hub:
                balance_report += f"| {hub} | {count} |\n"
                print(f"  - {hub}: {count} 件")

    # --- 5b. 戦略的優先度の決定 (変更なし) ---
    print("\n--- [フェーズ5b: 戦略的優先度の決定] AIが分析中 ---")
    analysis_target_articles = [
        p for p in processed_articles 
        if not p.get('file_name', '').startswith('projects/')
    ]
    print(f"\nℹ️ 'projects/' セクションを除外し、{len(analysis_target_articles)}件を分析対象とします。")
    df_all_data = create_placeholder_data(analysis_target_articles) 
    priority_result = select_priority_section_by_data(
        gemini_client, df_all_data, CORPORATE_IDENTITY, 
        analysis_target_articles, balance_report 
    )
    priority_file = priority_result['file_name']
    # ⬇️ [修正] 安全装置を追加
        try:
            priority_section_info = next(p for p in processed_articles if p['file_name'] == priority_file)
        except StopIteration:
            print(f"⚠️ 警告: AIが選定した '{priority_file}' が計画リストに見つかりませんでした。")
            
            # フォールバック: 'insights/index.html' またはリストにある最初のハブページを使用
            fallback_candidates = [
                p for p in processed_articles 
                if p['file_name'].endswith('index.html') and p['file_name'] != 'index.html'
            ]
            
            if fallback_candidates:
                priority_section_info = fallback_candidates[0] # とりあえず最初の候補を使う
                priority_file = priority_section_info['file_name']
                print(f"⚠️ フォールバック: 代わりに '{priority_file}' を強化対象とします。")
            else:
                print("❌ エラー: 有効なハブページが計画リストに1つもありません。処理を中断します。")
                sys.exit(1)
        # ⬆️ [修正] ここまで
    print(f"✅ [フェーズ5b 完了] 最優先セクションが決定しました。")
    print(f"🥇 最優先セクション: {priority_section_info['title']} (`{priority_file}`)")
    print(f"🔑 選定理由: {priority_result['reason']}")

    # --- 6. 詳細記事の企画 ---
    print("\n--- [フェーズ6: 詳細記事の企画] AIが企画中 ---")
    
    # 通し番号を取得 (変更なし)
    max_article_num = 0
    for p in processed_articles:
        match = re.search(r'-(\d+)\.html$', p.get('file_name', ''))
        if match:
            num = int(match.group(1))
            if num > max_article_num: max_article_num = num
    start_number = max_article_num + 1
    print(f"ℹ️ 次の記事番号は {start_number} から開始します。")
    
    # --- ⬇️ [修正] 自動リトライロジックの追加 ---
    max_retries = 3
    wait_time = 30 # 最初の待機時間 (秒)
    article_plans = None
    error_msg = ""

    for attempt in range(max_retries):
        print(f"\n📢 AIに {priority_section_info['title']} セクション用の記事 {DEFAULT_ARTICLE_COUNT} 件の企画を依頼中... (試行 {attempt + 1}/{max_retries})")
        
        # 実際のAPI呼び出し
        error_msg, article_plans = generate_priority_article_titles(
            gemini_client, priority_section_info, CORPORATE_IDENTITY, DEFAULT_ARTICLE_COUNT, start_number
        )

        if article_plans: # 成功
            break # リトライ_ループを抜ける

        # 失敗
        print(f"⚠️ 企画に失敗: {error_msg}")
        
        # 503エラーか "overloaded" が含まれているかチェック
        if "503" in str(error_msg) or "overloaded" in str(error_msg).lower():
            if attempt < max_retries - 1:
                print(f"   ...AIモデルが混雑しています。{wait_time}秒待機して再試行します。")
                time.sleep(wait_time)
                wait_time *= 2 # 次の待機時間を2倍に (Exponential Backoff)
            else:
                # 最終試行でも失敗
                print(f"❌ {max_retries}回試行しましたが、APIが混雑しています。")
        else:
            # 503以外のエラー (例: プロンプトエラーなど)
            print("❌ APIの混雑ではない致命的なエラーのため、再試行を停止します。")
            break # リトライ_ループを抜ける

    # ループ終了後、最終的に成功したかチェック
    if not article_plans:
        print(f"❌ 記事の企画に失敗したため、処理を中断します。")
        sys.exit(1)
    # --- ⬆️ [修正]ここまで ---

    print(f"✅ [フェーズ6 完了] {len(article_plans)} 件の新規記事を企画しました。")
    
    # (日付追加 ... 変更なし)
    current_time_iso = datetime.now().isoformat()
    for plan in article_plans:
        plan['created_at'] = current_time_iso
        plan['updated_at'] = "" 

    # --- 7. (本番) 詳細記事のHTML生成 ---
    print("\n--- [フェーズ7: 詳細記事のHTML生成] ---")
    new_article_files_generated = [] 
    # (for ループ ... 変更なし)
    for i, plan in enumerate(article_plans):
        target_dir = os.path.dirname(priority_section_info['file_name'])
        file_name = os.path.join(target_dir, plan.get('file_name', f'error-slug-{i}.html'))
        file_name = file_name.replace(os.path.sep, '/')
        article_plans[i]['file_name'] = file_name 
        print(f"\n--- 🏭 [本番生成] {plan['title']} ---")
        target_page_for_generation = {
            'title': plan['title'],
            'file_name': file_name,
            'purpose': plan['summary']
        }
        nav_list_for_generation = [
            {
                "file_name": p['file_name'], "title": p['title'],
                "purpose": p.get('summary', p.get('generated_purpose', '')) 
            } for p in processed_articles
        ]

        final_html_code = generate_single_page_html(
            gemini_client,
            target_page_for_generation,
            CORPORATE_IDENTITY,
            None,
            nav_list_for_generation,
            SITE_TYPE=SITE_TYPE, 
            retry_attempts=3, # (generate_single_page_html 側にもリトライがある)
            article_date=plan['created_at'] 
        )

        if "❌" not in final_html_code:
            generate_file_path = os.path.join(BASE_DIR, file_name)
            os.makedirs(os.path.dirname(generate_file_path), exist_ok=True)
            try:
                with open(generate_file_path, 'w', encoding='utf-8') as f:
                    f.write(final_html_code)
                print(f"✅ [本番生成] ファイル作成成功: {generate_file_path}")
                new_article_files_generated.append(plan) 
            except Exception as e:
                print(f"❌ [本番生成] ファイル作成失敗: {e}")
        else:
            print(f"❌ [本番生成] HTMLコード生成失敗: {file_name}")

    # --- 8. ハブページの自動更新 ---
    print(f"\n--- [フェーズ8: ハブページの自動更新] ---")
    # (all_content_plans 統合 ... 変更なし)
    all_content_plans = integrate_content_data(processed_articles, article_plans)
    hub_path_to_update = priority_file
    hub_dir = os.path.dirname(hub_path_to_update)
    
    # (X Bot 連携用 ... 変更なし)
    newly_updated_hubs = []
    current_time_iso_update = datetime.now().isoformat()
    print(f"🏭 {hub_path_to_update} をスキャンし、配下の全記事リンクを組み込みます。")

    try:
        # (ハブの更新日を記録 ... 変更なし)
        parent_page_plan = next(p for p in all_content_plans if p['file_name'] == hub_path_to_update)
        parent_page_plan['updated_at'] = current_time_iso_update
        newly_updated_hubs.append(parent_page_plan) 
        
    except StopIteration:
        print(f"❌ [ハブ更新失敗] 計画リストに親ハブ ({hub_path_to_update}) が見つかりません。")
        sys.exit(1)

    parent_page_info_for_regeneration = {
        'file_name': parent_page_plan['file_name'],
        'title': parent_page_plan['title'],
        'purpose': parent_page_plan.get('summary', parent_page_plan.get('generated_purpose')) 
    }

    # (all_articles_in_section ... 変更なし)
    all_articles_in_section = [
        p for p in all_content_plans 
        if os.path.dirname(p.get('file_name','')) == hub_dir and p.get('file_name','') != hub_path_to_update
    ]
    print(f"  -> {len(all_articles_in_section)} 件の詳細記事（新旧含む）をスキャンしました。")

    # (new_article_links_html ... 変更なし)
    new_article_links_html = "<ul>"
    if not all_articles_in_section:
        new_article_links_html = "<p>（現在、このセクションの詳細記事はありません）</p>"
    else:
        for plan in all_articles_in_section:
            link_path = os.path.basename(plan['file_name'])
            article_summary = plan.get('summary', plan.get('generated_purpose', '')) 
            new_article_links_html += f"<li><a href='{link_path}' class='text-blue-500 hover:underline'>{plan['title']}</a>: {article_summary}</li>"
    new_article_links_html += "</ul>"

    # (ハブの purpose 上書き ... 変更なし)
    parent_page_info_for_regeneration['purpose'] = f"""
    このページ（{parent_page_info_for_regeneration['title']}）は、以下の「{len(all_articles_in_section)}件の全詳細記事」への導線を含むハブページとして機能します。
    元の目的（{parent_page_info_for_regeneration['purpose']}）を要約しつつ、これらの新しい記事への明確な導線（目次）を提供してください。

    【{hub_dir} セクションの全詳細記事リスト】
    {new_article_links_html}
    """
    
    # (nav_list_for_generation ... 変更なし)
    nav_list_for_generation = [
        {
            "file_name": p['file_name'], "title": p['title'],
            "purpose": p.get('summary', p.get('generated_purpose', '')) 
        } for p in all_content_plans
    ]

    # (final_hub_code 呼び出し ... 変更なし)
    final_hub_code = generate_single_page_html(
        gemini_client,
        parent_page_info_for_regeneration,
        CORPORATE_IDENTITY,
        None,
        nav_list_for_generation,
        SITE_TYPE=SITE_TYPE, 
        retry_attempts=3,
        article_date=current_time_iso_update 
    )

    # (ファイル書き込み ... 変更なし)
    if "❌" not in final_hub_code:
        hub_file_path = os.path.join(BASE_DIR, parent_page_info_for_regeneration['file_name'])
        try:
            with open(hub_file_path, "w", encoding="utf-8") as f:
                f.write(final_hub_code)
            print(f"✅ [ハブ更新完了] ファイルを上書き保存しました: {hub_file_path}")
        except Exception as e:
            print(f"❌ [ハブ更新失敗] ファイル書き込みエラー: {e}")
    else:
        print(f"❌ [ハブ更新失敗] HTMLの再生成に失敗しました。")

    # --- 9. (レポート) 全体計画をMDファイルに保存 ---
    print("\n--- [最終処理: 全体計画の保存] ---")
    os.makedirs(REPORTS_DIR, exist_ok=True)
    save_to_markdown(all_content_plans, REPORT_FILE)
    print(f"✅ 全体計画を {REPORT_FILE} に保存しました。")
    
    # --- 10. X投稿用の更新リストを保存 (変更なし) ---
    print("\n--- [フェーズ10: X投稿用の更新リストを保存] ---")
    output_for_x_bot = os.path.join(PROJECT_ROOT_PATH, "newly_updated_articles.json")
    SITE_BASE_URL = "https://lou-ark.github.io/sophia-echoes/"
    articles_for_x = []
    
    for plan in new_article_files_generated:
        articles_for_x.append({
            "theme": plan['title'],
            "keywords": ["AI", "QoL", "sophia-echoes", "知見"], 
            "main_url": os.path.join(SITE_BASE_URL, plan['file_name']).replace(os.path.sep, '/'),
            "provided_summary": plan.get('summary', '記事の概要') 
        })
        
    for plan in newly_updated_hubs:
         articles_for_x.append({
            "theme": f"更新: {plan['title']}", 
            "keywords": ["AI", "QoL", "sophia-echoes"],
            "main_url": os.path.join(SITE_BASE_URL, plan['file_name']).replace(os.path.sep, '/'),
            "provided_summary": plan.get('purpose', 'ハブページの概要') 
        })

    if articles_for_x:
        try:
            with open(output_for_x_bot, 'w', encoding='utf-8') as f:
                json.dump(articles_for_x, f, ensure_ascii=False, indent=2)
            print(f"✅ {len(articles_for_x)} 件の更新情報を {output_for_x_bot} に保存しました。")
        except Exception as e:
            print(f"❌ X投稿用リストの保存に失敗: {e}")
    else:
        print("ℹ️ Xに通知する新規記事・更新ハブはありませんでした。")

    # --- 11. タグの自動挿入 (変更なし) ---
    print("\n--- [フェーズ11: GTM/AdSense タグの自動挿入] ---")
    print("生成・更新されたHTMLファイルにタグを挿入します...")
    try:
        inject_tags_main()
    except Exception as e:
        print(f"❌ タグ挿入プロセス中にエラーが発生しました: {e}")
        print("ℹ️ タグを挿入する場合は、手動で %run main_03_inject_tags.py を実行してください。")

    print("--- 🔄 HP改善サイクルエージェント 完了 ---")

if __name__ == "__main__":
    PROJECT_ROOT_PATH = "/content/MySiteGen-Agent" 
    if PROJECT_ROOT_PATH not in sys.path:
        sys.path.append(PROJECT_ROOT_PATH)
    main()
