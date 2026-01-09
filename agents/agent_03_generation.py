import re
import os
import json
import time
import random
from google import genai
from google.genai import types
from datetime import datetime
try:
    from config import settings
except ImportError:
    # settingsがない場合の簡易フォールバック（通常はありえない）
    class MockSettings:
        API_KEYS = []
    settings = MockSettings()
try:
    from config.settings import MODEL_NAME_PRO, MODEL_NAME_GEN
except ImportError:
    MODEL_NAME_PRO = "gemini-3-flash-preview"
    MODEL_NAME_GEN = "gemini-3-flash-preview"

# ⬇️ [修正] 引数に article_date=None を追加
def generate_single_page_html(client, target_page, identity, strategy_full, page_list, GTM_ID=None, ADSENSE_CLIENT_ID=None, SITE_TYPE='corporate', retry_attempts=3, article_date=None, header_snippet=None, footer_snippet=None):
    """
    ターゲットページ情報に基づいてプロンプトを動的に生成し、HTMLファイルを出力する。
    GTMとAdSenseのスニペットを自動で挿入し、サイトタイプに応じてフッターを変更する。
    """
    if client is None:
        return "❌ Geminiクライアントが利用できません。"

    nav_structure = "\n".join([f' - {p.get("title", "N/A")} ({p.get("file_name", "N/A")})' for p in page_list])

    # --- ⬇️ [追加] Python側でグリッドHTMLを生成して強制挿入する ---
    grid_html = ""
    if page_list:
        grid_html += '<div class="grid grid-cols-1 md:grid-cols-2 gap-8">\n'
        for page in page_list:
            title = page.get('title', 'No Title')
            # 目的が長い場合は丸める処理を入れてもいいが、一旦そのまま
            desc = page.get('purpose', 'No Description')
            # ファイル名からリンク先を特定 (相対パス計算は簡易的、同階層前提)
            link = os.path.basename(page.get('file_name', '#'))
            
            # カテゴリ推定 (ディレクトリ名)
            category = "Project"
            if '/' in page.get('file_name', ''):
                category = page.get('file_name', '').split('/')[0].capitalize()

            grid_html += f"""
            <!-- Article Card -->
            <a href="{link}" class="block bg-brand-gray-800 rounded-lg p-6 hover:bg-brand-gray-700 hover:scale-105 transition-all duration-300 shadow-lg">
                <div class="flex items-center mb-3">
                    <span class="inline-block bg-brand-accent-500 text-brand-gray-900 text-xs font-semibold px-2.5 py-1 rounded-full">{category}</span>
                </div>
                <h3 class="text-xl font-bold text-white mb-2">{title}</h3>
                <p class="text-brand-light-300 text-sm">{desc}</p>
            </a>
            """
        grid_html += '</div>'
    # --- ⬆️ [追加] ---

    target_title = target_page['title']
    target_filename = target_page['file_name']
    target_purpose = target_page['purpose']
    
    # --- ⬇️ [修正] GTM/AdSense の定義を追加 ---
    gtm_instructions = ""
    if GTM_ID:
        print(f"  > GTM ID ({GTM_ID}) をHTMLに挿入します。")
        gtm_instructions = f"""
    5.  **GTM (Google Tag Manager) の挿入:**
        - <head> タグのできるだけ高い位置に以下のコードを挿入してください:
        <script>(function(w,d,s,l,i){{w[l]=w[l]||[];w[l].push({{'gtm.start':
        new Date().getTime(),event:'gtm.js'}});var f=d.getElementsByTagName(s)[0],
        j=d.createElement(s),dl=l!='dataLayer'?'&l='+l:'';j.async=true;j.src=
        'https://www.googletagmanager.com/gtm.js?id='+i+dl;f.parentNode.insertBefore(j,f);
        }})(window,document,'script','dataLayer','{GTM_ID}');</script>
        - <body> タグの直後に以下のコードを挿入してください:
        <noscript><iframe src="https://www.googletagmanager.com/ns.html?id={GTM_ID}"
        height="0" width="0" style="display:none;visibility:hidden"></iframe></noscript>
        """
    else:
         print(f"  > GTM ID が指定されていないため、GTMタグは挿入しません。")
         
    adsense_instructions = ""
    if ADSENSE_CLIENT_ID:
        print(f"  > AdSense Client ID ({ADSENSE_CLIENT_ID}) をHTMLに挿入します。")
        adsense_instructions = f"""
    6.  **Google AdSense の挿入:**
        - <head> タグのできるだけ高い位置に以下のコードを挿入してください:
        <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={ADSENSE_CLIENT_ID}"
             crossorigin="anonymous"></script>
        """
    else:
        print(f"  > AdSense ID が指定されていないため、AdSenseタグは挿入しません。")
    # --- ⬆️ [修正] ここまで ---

    # --- 共通パーツの指示を生成 ---
    snippet_instruction = ""
    if header_snippet or footer_snippet:
        snippet_instruction = "### 共通パーツの強制利用 (COMMON SNIPPETS)\n"
        if header_snippet:
            snippet_instruction += f"- **HEADER**: 以下のHTMLをヘッダーとしてそのまま使用してください（ナビゲーションリンクのパスは必要に応じて自動調整すること）:\n{header_snippet}\n"
        if footer_snippet:
            snippet_instruction += f"- **FOOTER**: 以下のHTMLをフッターとしてそのまま使用してください:\n{footer_snippet}\n"
    # --- ⬆️ [追加] ---

    content_focus = f"**このページの具体的な目的と、必要なコンテンツの詳細:** {target_purpose}\n"
    if strategy_full:
        content_focus += f"\n--- 全体戦略の要約 ---\n{strategy_full}"

    # --- フッターの指示を動的に変更 ---
    if SITE_TYPE == 'corporate':
        footer_instruction = "フッターの著作権表記は、AIが生成した法人名（例: Quantalize Futures Inc.）にしてください。"
        identity_label = "法人格フレームワーク"
    else: # 'personal'
        footer_instruction = "フッターの著作権表記は、**「LOU-Ark」**または**「LOU-Ark Portfolio」**にしてください。"
        identity_label = "パーソナル・ブランド"

    # --- 日付の指示を生成 ---
    date_instruction = ""
    if article_date:
        try:
            # 入力が文字列（2025-01-09など）の場合を考慮
            if isinstance(article_date, str):
                if 'T' in article_date:
                    date_obj = datetime.fromisoformat(article_date.replace('Z', '+00:00'))
                else:
                    date_obj = datetime.strptime(article_date, "%Y-%m-%d")
            else:
                date_obj = article_date
                
            formatted_date = date_obj.strftime("%Y年%m月%d日")
            date_instruction = f"""
    7.  **日付の明記:** 記事のタイトル下（メタ情報エリア）に、**「公開日: {formatted_date}」**という形式で必ず記載してください。
    """
        except Exception as e:
            print(f"日付処理エラー: {e}")
            date_instruction = f"""
    7.  **日付の明記:** 記事のタイトル下（メタ情報エリア）に、**「公開日: {article_date}」**を記載してください。
    """
    # --- ⬆️ [追加] ---

    prompt_template = f"""
    あなたはワールドクラスのウェブデザイナーであり、フロントエンドエンジニアです。
    以下の「{identity_label}」と「コンテンツ戦略」に基づき、**{target_title} ({target_filename}) 用の単一のモダンでレスポンシブなHTMLファイル**を生成してください。

    ### CRITICAL INSTRUCTION: 出力形式の厳守
    - **[START HTML CODE]** というマーカーからコードの記述を開始してください。
    - **必ず** `<!DOCTYPE html>` から `</html>` まで、全てのHTML構造を完全に記述してください。
    - **必ず** `\n```eof` で出力を完全に終了してください。（コードブロックは```htmlで開始してください）
    - **CRITICAL:** 提供された「全ページリスト」の**全ての項目**に対して、必ずカード（またはリストアイテム）を作成してください。省略・要約は厳禁です。リストがN個あれば、N個のカードを出力してください。

    ### デザイン・フォーマット要件 (DESIGN REQUIREMENTS)
    1.  **全体の雰囲気:** 背景は深みのあるダークモード (`bg-gray-900`)、テキストは読みやすいグレー (`text-gray-300`) を基調とします。
    2.  **タイポグラフィ:** Google Fonts の 'Inter' をメイン、『Roboto Mono』を等幅フォントとして使用してください。
    3.  **グラデーション:** 強調箇所やテキストには `#2dd4bf` (teal-400) から `#38bdf8` (blue-400) へのグラデーション (`gradient-text`) を使用してください。
    4.  **ヘッダー/フッター:** 
        - ヘッダーは `bg-gray-900/80 backdrop-blur-sm sticky top-0`。
        - ロゴテキストは `LOU-Ark`。
        - フッターにはサイトマップと著作権表記（© 2025 LOU-Ark Portfolio.）を含めてください。
    5.  **記事構造:**
        - パンくずリストを設置（ホーム > セクション名 > 記事タイトル）。リンクは相対パスで。
        - 記事ヘッダーにはタグ（例：Looker Studio, GA4）をバッジ形式で配置。
        - タイトルの下に「公開日: YYYY年MM月DD日」を配置。
        - 本文は `prose prose-lg prose-invert max-w-none` クラスを適用した `div` 内に記述してください。
    6.  **ナビゲーション:**
        - 現在のファイルパス `{target_filename}` に基づき、`../index.html` などの相対パスを正確に生成してください。
    {gtm_instructions}
    {adsense_instructions} 
    {date_instruction} 
    {snippet_instruction}

    ### ページ固有の入力データ
    - ページのタイトル: {target_title}
    - ページのファイル名: {target_filename}
    - ページの目的: {target_purpose}

    ### 全体的な入力データ
    - {identity_label}: {identity}
    - コンテンツ戦略（コンテンツ焦点）：{content_focus}
    - 確定した全ページリスト（ナビゲーション構造）:{nav_structure}
    
    ### CRITICAL: 記事一覧エリアのプレースホルダー
    **記事一覧（カードのグリッド）を描画する場所には、以下のプレースホルダーのみを記述してください。**
    AIが記事カードを生成する必要はありません。Pythonプログラムが後で置換します。
    
    <!-- GRID_PLACEHOLDER -->
    
    (上記プレースホルダーを、`main`タグ内の適切な場所（タイトルの下など）に配置してください。リスト項目は一切生成しないでください)
    
    ### CRITICAL: TEMPLATE MODE
    You are generating a Layout Container.
    1. Write the Header.
    2. Write the Page Title and Intro.
    3. Write `<!-- GRID_PLACEHOLDER -->`.
    4. Write the Footer.
    DO NOT GENERATE ANY ARTICLE CARDS. JUST THE PLACEHOLDER.

    [START HTML CODE]
    """

    for attempt in range(retry_attempts):
        print(f"  > HTMLコードの生成を開始中... (試行 {attempt + 1}/{retry_attempts}) for {target_filename}")
        try:
            response = client.models.generate_content(
                model=MODEL_NAME_GEN, # 生成用モデルを使用
                contents=prompt_template,
                config=types.GenerateContentConfig(max_output_tokens=65536)
            )
            raw_output = response.text.strip()
            
            # --- ⬇️ [追加] プレースホルダーをPython生成のグリッドに置換 (最優先) ---
            if "<!-- GRID_PLACEHOLDER -->" in raw_output:
                print("  > プレースホルダーを検知しました。グリッドHTMLと置換します。")
                raw_output = raw_output.replace("<!-- GRID_PLACEHOLDER -->", grid_html)
            elif grid_html:
                # プレースホルダーがない場合、強制的に mainの終わりの前などに挿入を試みるか、
                # または AIが指示を無視した場合のリスクヘッジとして警告を出す
                print("  ⚠️ 警告: GRID_PLACEHOLDER が検出されませんでした。AIが記事リストを自作した可能性があります。")
            # --- ⬆️ [追加] ---

            # より柔軟な抽出ロジック

            # より柔軟な抽出ロジック
            # 1. ```html ... ``` を探す
            match = re.search(r"```html\s*(.*?)\s*(?:```|$)", raw_output, re.DOTALL)
            if match:
                html_candidate = match.group(1).strip()
                if "</html>" in html_candidate:
                    return html_candidate

            # 2. マーカーがない場合、<html>...</html> を直接探す
            match = re.search(r"(<!DOCTYPE html>.*?</html>)", raw_output, re.DOTALL | re.IGNORECASE)
            if match:
                return match.group(1).strip()
            
            # 3. それでもダメで </html> で終わっているなら、マーカー類を削って返す
            if "</html>" in raw_output:
                clean_html = re.sub(r"^[^{]*\[START HTML CODE\]", "", raw_output, flags=re.DOTALL).strip()
                clean_html = re.sub(r"```.*$", "", clean_html, flags=re.DOTALL).strip()
                return clean_html

            print(f"警告: 有効なHTML構造が見つかりませんでした。 for {target_filename}")

        except Exception as e:
            print(f"エラーが発生しました: {e} for {target_filename}")
            
            # --- [追加] 自動フェイルオーバー (APIキーローテーション) ---
            # エラー時、次の試行のためにクライアントを別のキーで再構築する
            if hasattr(settings, 'API_KEYS') and settings.API_KEYS and len(settings.API_KEYS) > 1:
                # ランダムにキーを選択 (確率的に回避)
                new_key = random.choice(settings.API_KEYS)
                print(f"  ↻ Switching to a new API Key for retry... (****{new_key[-4:]})")
                try:
                    client = genai.Client(api_key=new_key)
                except Exception as client_err:
                    print(f"  ⚠️ Failed to switch client: {client_err}")
            # ----------------------------------------------------

            if attempt < retry_attempts - 1:
                time.sleep(5) # ローテーション時は待ち時間短縮でOK
            else:
                return f"❌ HTMLコードの生成に失敗しました。\nError: {e}"
