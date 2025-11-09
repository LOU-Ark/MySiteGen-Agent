import os
import sys
import json
import shutil
from google import genai
# from IPython.display import display, Markdown # .pyファイルからは削除

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

# --- 0. 設定 ---
# ⬇️ [修正] 画像のディレクトリ構造 'reports/' をパスに追加
BASE_DIR = os.path.join("reports", "docs")
REPORTS_DIR = os.path.join("reports", "output_reports")
# ⬆️ [修正] 

REPORT_FILE = os.path.join(REPORTS_DIR, "planned_articles.md")
DEFAULT_ARTICLE_COUNT = 3

def setup_client():
    """Geminiクライアントを初期化"""
    try:
        from google.colab import userdata
        GOOGLE_API_KEY = userdata.get('GEMINI_API_KEY')
        if not GOOGLE_API_KEY:
            raise ValueError("GEMINI_API_KEY が Colab Secrets に設定されていません。")
        return genai.Client(api_key=GOOGLE_API_KEY)
    except ImportError:
        GOOGLE_API_KEY = os.environ.get('GEMINI_API_KEY')
        if not GOOGLE_API_KEY:
            raise EnvironmentError("GEMINI_API_KEY が環境変数に設定されていません。")
        return genai.Client(api_key=GOOGLE_API_KEY)
    except Exception as e:
        print(f"❌ クライアント初期化エラー: {e}")
        return None

# ⬇️ [修正] 法人格をファイルから読み込むように変更
def load_corporate_identity():
    """
    'main_01' が保存した法人格レポートをファイルから読み込む。
    """
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
            with open("config/opinion.txt", 'r', encoding='utf-8') as f:
                RAW_VISION_INPUT = f.read()
            client = setup_client()
            if client:
                print("⚠️ [フォールバック] 法人格をAPIで再生成します。")
                return generate_corporate_identity(client, RAW_VISION_INPUT)
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

    # --- 5a. 戦略（AS-IS分析）---
    print(f"\n--- [フェーズ5a: AS-IS分析] 計画ファイル ({REPORT_FILE}) を読み込み中 ---")
    processed_articles = None
    if os.path.exists(REPORT_FILE):
        processed_articles = load_markdown_table_to_list(REPORT_FILE)

    if processed_articles:
        print(f"✅ 既存の計画ファイルから {len(processed_articles)} 件の目的を読み込みました。（APIコールをスキップ）")
    else:
        # (フォールバック)
        print(f"⚠️ 計画ファイルが見つからないか、読み込みに失敗しました。")
        print(f"--- [フェーズ5a 代替] 既存サイト ({BASE_DIR}) をスキャン中 ---")
        processed_articles = []
        TARGET_EXTENSIONS = ('.html', '.htm')
        if not os.path.isdir(BASE_DIR):
            print(f"❌ 分析対象ディレクトリ {BASE_DIR} が見つかりません。")
            sys.exit(1)
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
                            "summary": purpose # ⬅️ [修正] 'summary' キーで保存
                        })
        print(f"\n✅ [フェーズ5a 代替完了] 合計 {len(processed_articles)} 件の目的をAPIで再定義しました。")
        
    # ⬇️ [修正] 5a-2. 「戦略的バランス」の数値化
    print(f"\n--- [フェーズ5a-2: 戦略的バランスの分析] ---")
    hub_counts = {}
    all_hubs = []
    
    # 1. ハブを特定
    for p in processed_articles:
        if p.get('file_name', '').endswith('index.html'):
            hub_counts[p['file_name']] = 0 # カウントを0で初期化
            all_hubs.append(p['file_name'])

    # 2. ハブ配下の記事をカウント
    for p in processed_articles:
        if not p.get('file_name', '').endswith('index.html'):
            parent_dir = os.path.dirname(p.get('file_name', ''))
            parent_hub = os.path.join(parent_dir, 'index.html').replace(os.path.sep, '/')
            if parent_hub in hub_counts:
                hub_counts[parent_hub] += 1
    
    # 3. AIに渡すためのバランスレポートを作成
    balance_report = "| ハブページ | 配下の詳細記事数 |\n| :--- | :--- |\n"
    print("✅ 現在のサイトバランス:")
    for hub, count in hub_counts.items():
        # ユーティリティページと 'projects/' はレポートから除外
        if 'legal/' not in hub and 'contact/' not in hub and 'about-us/' not in hub and 'projects/' not in hub:
            balance_report += f"| {hub} | {count} |\n"
            print(f"  - {hub}: {count} 件")

# --- 5b. 戦略的優先度の決定 ---
    print("\n--- [フェーズ5b: 戦略的優先度の決定] AIが分析中 ---")

    # ⬇️ [追加] AIの分析対象から 'projects/' セクションを除外
    analysis_target_articles = [
        p for p in processed_articles 
        if not p.get('file_name', '').startswith('projects/')
    ]
    print(f"\nℹ️ 'projects/' セクションを除外し、{len(analysis_target_articles)}件を分析対象とします。")

    df_all_data = create_placeholder_data(analysis_target_articles) # ⬅️ [修正]

    # ⬇️ [修正] 'balance_report' を引数として渡す
    priority_result = select_priority_section_by_data(
        gemini_client, 
        df_all_data, 
        CORPORATE_IDENTITY, 
        analysis_target_articles, # ⬅️ [修正]
        balance_report # ⬅️ バランスレポートを渡す
    )

    priority_file = priority_result['file_name']
    priority_section_info = next(p for p in processed_articles if p['file_name'] == priority_file)

    print(f"✅ [フェーズ5b 完了] 最優先セクションが決定しました。")
    print(f"🥇 最優先セクション: {priority_section_info['title']} (`{priority_file}`)")
    print(f"🔑 選定理由: {priority_result['reason']}")

    # --- 6. 詳細記事の企画 ---
    print("\n--- [フェーズ6: 詳細記事の企画] AIが企画中 ---")
    start_number = get_existing_article_count(BASE_DIR) + 1
    
    # ⬇️ [修正] 'summary' キーを持つ辞書を渡す
    error_msg, article_plans = generate_priority_article_titles(
        gemini_client, priority_section_info, CORPORATE_IDENTITY, DEFAULT_ARTICLE_COUNT, start_number
    )

    if not article_plans:
        print(f"❌ 記事の企画に失敗しました: {error_msg}")
        sys.exit(1)

    print(f"✅ [フェーズ6 完了] {len(article_plans)} 件の新規記事を企画しました。")

    # --- 7. (本番) 詳細記事のHTML生成 ---
    print("\n--- [フェーズ7: 詳細記事のHTML生成] ---")

    new_article_files_generated = []

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
                "file_name": p['file_name'],
                "title": p['title'],
                "purpose": p.get('summary', p.get('generated_purpose', '')) 
            } for p in processed_articles
        ]

        final_html_code = generate_single_page_html(
            gemini_client,
            target_page_for_generation,
            CORPORATE_IDENTITY,
            None,
            nav_list_for_generation,
            retry_attempts=3
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

    all_content_plans = integrate_content_data(processed_articles, article_plans)

    hub_path_to_update = priority_file
    hub_dir = os.path.dirname(hub_path_to_update)

    print(f"🏭 {hub_path_to_update} をスキャンし、配下の全記事リンクを組み込みます。")

    try:
        parent_page_info = next(p for p in all_content_plans if p['file_name'] == hub_path_to_update)
    except StopIteration:
        print(f"❌ [ハブ更新失敗] 計画リストに親ハブ ({hub_path_to_update}) が見つかりません。")
        sys.exit(1)

    parent_page_info_for_regeneration = {
        'file_name': parent_page_info['file_name'],
        'title': parent_page_info['title'],
        'purpose': parent_page_info.get('summary', parent_page_info.get('generated_purpose')) 
    }

    all_articles_in_section = []
    for plan in all_content_plans:
        if (os.path.dirname(plan['file_name']) == hub_dir) and \
           (plan['file_name'] != hub_path_to_update):
            all_articles_in_section.append(plan)

    print(f"  -> {len(all_articles_in_section)} 件の詳細記事（新旧含む）をスキャンしました。")

    new_article_links_html = "<ul>"
    if not all_articles_in_section:
        new_article_links_html = "<p>（現在、このセクションの詳細記事はありません）</p>"
    else:
        for plan in all_articles_in_section:
            link_path = os.path.basename(plan['file_name'])
            article_summary = plan.get('summary', plan.get('generated_purpose', '')) 
            new_article_links_html += f"<li><a href='{link_path}' class='text-blue-500 hover:underline'>{plan['title']}</a>: {article_summary}</li>"
        new_article_links_html += "</ul>"

    parent_page_info_for_regeneration['purpose'] = f"""
    このページ（{parent_page_info_for_regeneration['title']}）は、以下の「{len(all_articles_in_section)}件の全詳細記事」への導線を含むハブページとして機能します。
    元の目的（{parent_page_info_for_regeneration['purpose']}）を要約しつつ、これらの新しい記事への明確な導線（目次）を提供してください。

    【{hub_dir} セクションの全詳細記事リスト】
    {new_article_links_html}
    """

    nav_list_for_generation = [
        {
            "file_name": p['file_name'],
            "title": p['title'],
            "purpose": p.get('summary', p.get('generated_purpose', '')) 
        } for p in all_content_plans
    ]

    final_hub_code = generate_single_page_html(
        gemini_client,
        parent_page_info_for_regeneration,
        CORPORATE_IDENTITY,
        None,
        nav_list_for_generation,
        retry_attempts=3
    )

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
    print("--- 🔄 HP改善サイクルエージェント 完了 ---")

if __name__ == "__main__":
    main()
