import re
import os
import json
from google import genai
from google.genai import types
from datetime import datetime
try:
    from config.settings import MODEL_NAME_PRO, MODEL_NAME_GEN
except ImportError:
    MODEL_NAME_PRO = "gemini-3-flash-preview"
    MODEL_NAME_GEN = "gemini-3-flash-preview"

# ⬇️ [修正] 引数に article_date=None を追加
def generate_single_page_html(client, target_page, identity, strategy_full, page_list, GTM_ID=None, ADSENSE_CLIENT_ID=None, SITE_TYPE='corporate', retry_attempts=3, article_date=None):
    """
    ターゲットページ情報に基づいてプロンプトを動的に生成し、HTMLファイルを出力する。
    GTMとAdSenseのスニペットを自動で挿入し、サイトタイプに応じてフッターを変更する。
    """
    if client is None:
        return "❌ Geminiクライアントが利用できません。"

    nav_structure = "\n".join([f' - {p.get("title", "N/A")} ({p.get("file_name", "N/A")})' for p in page_list])

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

    # --- コンテンツ指示ロジック ('projects' の特別ルールを無効化) ---
    if 'index.html' in target_filename:
        # 通常のハブページ
        content_instruction = f"このページはハブページ（目次）です。目的（{target_purpose}）を達成するため、**深い論理構成と具体的な記述**に焦点を当ててください。"
    else:
        # 通常の詳細記事
        content_instruction = f"このページは詳細記事です。目的（{target_purpose}）を達成するため、**深い論理構成と具体的なデータサイエンスの記述**に焦点を当ててください。"
    # --- ⬆️ [修正] ここまで ---

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

    ### ページ固有の入力データ
    - ページのタイトル: {target_title}
    - ページのファイル名: {target_filename}
    - ページの目的: {target_purpose}

    ### 全体的な入力データ
    - {identity_label}: {identity}
    - コンテンツ戦略（コンテンツ焦点）：{content_focus}
    - 確定した全ページリスト（ナビゲーション構造）:{nav_structure}

    [START HTML CODE]
    """

    for attempt in range(retry_attempts):
        print(f"  > HTMLコードの生成を開始中... (試行 {attempt + 1}/{retry_attempts}) for {target_filename}")
        try:
            response = client.models.generate_content(
                model=MODEL_NAME_GEN, # 生成用モデルを使用
                contents=prompt_template
            )
            raw_output = response.text.strip()

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

    return "❌ HTMLコードの生成に失敗しました。"
