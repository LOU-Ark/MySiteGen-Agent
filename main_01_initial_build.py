import os
import sys
import json
import shutil
import re 
from google import genai
from google.genai import types 
from utils.client_utils import setup_client

# モジュールをインポート
from agents.agent_01_identity import generate_corporate_identity
from agents.agent_02_strategy import (
    generate_final_sitemap,
    generate_content_strategy,
    generate_target_page_list
)
from agents.agent_03_generation import generate_single_page_html

# --- 0. 設定 ---
OPINION_FILE = "config/opinion.txt"
# ⬇️ [修正] メインの出力先を 'output' フォルダに
MAIN_OUTPUT_DIR = "output"
REPORTS_DIR = os.path.join(MAIN_OUTPUT_DIR, "output_reports")
# (OUTPUT_DIR と ZIP_FILENAME は main() 内で動的に設定)

def generate_site_name_and_slug(client, identity, SITE_TYPE):
    """
    法人格/ブランドに基づき、サイトの正式名称とディレクトリ用のスラッグ（フォルダ名）を生成する。
    """
    if SITE_TYPE == 'corporate':
        role_desc = "この「法人格」"
        name_desc = "「サイトの正式名称（日本語）」"
        slug_desc = "「ディレクトリ名（英語のスラッグ）」"
        example_name = "（例）クオンタライズ・フューチャーズ"
        example_slug = "quantalize-futures-site"
    else: # 'personal'
        role_desc = "この「パーソナル・ブランド」"
        name_desc = "「ポートフォリオの正式名称（日本語）」"
        slug_desc = "「ディレクトリ名（英語のスラッグ）」"
        example_name = "（例）LOU-Ark ポートフォリオ"
        example_slug = "lou-ark-portfolio"
        
    prompt = f"""
    あなたは企業のブランディング専門家です。
    以下の{role_desc}を分析し、このプロジェクトにふさわしい{name_desc}と{slug_desc}をJSON形式で提案してください。

    ### {role_desc}
    {identity}

    ### ルール
    - スラッグは、英語の小文字、ハイフン区切りにしてください。（例: '{example_slug}'）
    - 非常にユニークで、哲学の核を反映した名前にしてください。

    ### 出力フォーマット (JSONのみ)
    {{"site_name": "{example_name}", "slug": "{example_slug}"}}
    """
    print("... 🤖 AI (Flash) がサイト名を動的生成中 ...")
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash", 
            contents=prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )
        data = json.loads(response.text)
        
        slug = data.get("slug", "default-site-name").strip().lower()
        slug = re.sub(r"[^a-z0-9-]", "", slug)
        if not slug: slug = "default-site-name"
        
        print(f"✅ AIがサイト名を生成しました: {data.get('site_name')} (Slug: {slug})")
        return slug
    except Exception as e:
        print(f"❌ サイト名の生成に失敗: {e}。デフォルト名を使用します。")
        return "people-opt-default-site"

def main():
    print("--- 🚀 HP初回構築エージェント (フェーズ1-4) 開始 ---")

    # --- 0. サイトタイプの選択 ---
    SITE_TYPE = ''
    while SITE_TYPE not in ['1', '2']:
        SITE_TYPE = input("生成するサイトのタイプを選んでください (1 or 2):\n 1: 法人 (Corporate)\n 2: 個人 (Personal)\n > ")
    
    SITE_TYPE = 'corporate' if SITE_TYPE == '1' else 'personal'
    print(f"✅ サイトタイプ: {SITE_TYPE} を選択しました。")

    # --- 1. クライアント初期化 ---
    gemini_client = setup_client()
    if gemini_client is None:
        sys.exit(1)

    # --- [修正] レポートディレクトリを先に作成 ---
    os.makedirs(REPORTS_DIR, exist_ok=True) # ⬅️ 'output/output_reports' を作成

    # --- 2. 個人の意見をロード ---
    try:
        with open(OPINION_FILE, 'r', encoding='utf-8') as f:
            RAW_VISION_INPUT = f.read()
        print(f"✅ [フェーズ1] {OPINION_FILE} を読み込みました。")
    except Exception as e:
        print(f"❌ {OPINION_FILE} の読み込みに失敗: {e}")
        sys.exit(1)

    # --- 3. 法人格/ブランドの生成 ---
    IDENTITY_TEXT = generate_corporate_identity(gemini_client, RAW_VISION_INPUT, SITE_TYPE)
    print(f"✅ [フェーズ2] {SITE_TYPE} のアイデンティティを生成しました。")
    try:
        with open(os.path.join(REPORTS_DIR, "01_identity.md"), 'w', encoding='utf-8') as f:
            f.write(IDENTITY_TEXT)
        print(f"✅ [レポート] 01_identity.md を保存しました。")
    except Exception as e:
        print(f"⚠️ [レポート] 01_identity.md の保存中にエラー: {e}")

    # --- 4. サイト名の動的生成 ---
    SITE_SLUG = generate_site_name_and_slug(gemini_client, IDENTITY_TEXT, SITE_TYPE)
    # ⬇️ [修正] 出力先を 'output/output_website/[slug]' に変更
    OUTPUT_DIR = os.path.join(MAIN_OUTPUT_DIR, "output_website", SITE_SLUG)
    # ⬇️ [修正] ZIPファイル名を変更
    ZIP_FILENAME = f"{SITE_SLUG}_output.zip" # 例: "anima-cognita-portfolio_output.zip"
    print(f"✅ 出力先を動的に設定: {OUTPUT_DIR}")

    # --- 5. 戦略の生成 ---
    print("\n--- [フェーズ3] サイト戦略の生成を開始 ---")
    
    sitemap_result = generate_final_sitemap(gemini_client, IDENTITY_TEXT, SITE_TYPE)
    try:
        with open(os.path.join(REPORTS_DIR, "02_sitemap.md"), 'w', encoding='utf-8') as f:
            f.write(sitemap_result)
        print(f"✅ [レポート] 02_sitemap.md を保存しました。")
    except Exception as e:
        print(f"⚠️ [レポート] 02_sitemap.md の保存中にエラー: {e}")

    content_strategy_result = generate_content_strategy(gemini_client, IDENTITY_TEXT, sitemap_result, SITE_TYPE)
    try:
        with open(os.path.join(REPORTS_DIR, "03_content_strategy.md"), 'w', encoding='utf-8') as f:
            f.write(content_strategy_result)
        print(f"✅ [レポート] 03_content_strategy.md を保存しました。")
    except Exception as e:
        print(f"⚠️ [レポート] 03_content_strategy.md の保存中にエラー: {e}")

    TARGET_PAGES_LIST = generate_target_page_list(gemini_client, IDENTITY_TEXT, content_strategy_result)
    try:
        with open(os.path.join(REPORTS_DIR, "04_target_pages_list.json"), 'w', encoding='utf-8') as f:
            json.dump(TARGET_PAGES_LIST, f, indent=2, ensure_ascii=False)
        print(f"✅ [レポート] 04_target_pages_list.json を保存しました。")
    except Exception as e:
        print(f"⚠️ [レポート] 04_target_pages_list.json の保存中にエラー: {e}")

    if not TARGET_PAGES_LIST:
        print("❌ ターゲットリストの生成に失敗したため、処理を中断します。")
        sys.exit(1)
    print("✅ [フェーズ3] サイト戦略とターゲットリストの生成が完了しました。")

    # --- 6. 全体（ハブページ）の生成 ---
    print(f"\n--- [フェーズ4] 全体（ハブページ）のHTML生成を開始 (出力先: {OUTPUT_DIR}) ---")
    if os.path.exists(OUTPUT_DIR):
        shutil.rmtree(OUTPUT_DIR)

    generated_files = {}

    for page in TARGET_PAGES_LIST:
        print(f"\n--- 🏭 ページ生成: {page['title']} ({page['file_name']}) ---")

        final_html_code = generate_single_page_html(
            gemini_client,
            page,
            IDENTITY_TEXT,
            content_strategy_result,
            TARGET_PAGES_LIST,
            GTM_ID=None, 
            ADSENSE_CLIENT_ID=None,
            SITE_TYPE=SITE_TYPE, 
            retry_attempts=3
        )

        if "❌" not in final_html_code:
            target_file_path = os.path.join(OUTPUT_DIR, page['file_name'])
            target_dir = os.path.dirname(target_file_path)
            os.makedirs(target_dir, exist_ok=True)

            try:
                with open(target_file_path, "w", encoding="utf-8") as f:
                    f.write(final_html_code)
                generated_files[page['file_name']] = f"✅ 生成完了: {target_file_path}"
            except Exception as e:
                generated_files[page['file_name']] = f"❌ ファイル書き込みエラー: {e}"
        else:
            generated_files[page['file_name']] = final_html_code

    print("\n--- 🎉 全ページ生成結果サマリー ---")
    for filename, status in generated_files.items():
        print(f"{filename.ljust(30)}: {status}")

    # ---  ZIP化 ---
    # ⬇️ [修正] 'MAIN_OUTPUT_DIR' ('output' フォルダ) を丸ごとZIP化
    print(f"\n--- 📦 {ZIP_FILENAME} にZIP圧縮中 ---")
    try:
        shutil.make_archive(
            ZIP_FILENAME.replace('.zip', ''),  # ZIPファイル名 (例: 'anima-cognita-portfolio_output')
            'zip',                             # 形式
            MAIN_OUTPUT_DIR                    # ⬅️ 圧縮対象 ('output' フォルダ)
        )
        print(f"✅ ZIPファイルの作成が完了しました: {ZIP_FILENAME}")
    except Exception as e:
        print(f"❌ ZIPファイルの作成中にエラーが発生しました: {e}")

    print("--- 🚀 HP初回構築エージェント 完了 ---")

if __name__ == "__main__":
    main()
