import re
import os
import json
from google import genai
from google.genai import types
from datetime import datetime 

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
            date_obj = datetime.fromisoformat(article_date.replace('Z', '+00:00'))
            formatted_date = date_obj.strftime("%Y年%m月%d日")
            date_instruction = f"""
    7.  **日付の明記:** 記事のタイトル下など、読者から見える分かりやすい位置に、この記事の公開日（または更新日）として、**「{formatted_date}」**を必ず記載してください。
    """
        except Exception:
            date_instruction = f"""
    7.  **日付の明記:** 記事のタイトル下など、読者から見える分かりやすい位置に、この記事の公開日（または更新日）として、**「{article_date}」**を記載してください。
    """
    # --- ⬆️ [追加] ---

    prompt_template = f"""
    あなたはワールドクラスのウェブデザイナーであり、フロントエンドエンジニアです。
    以下の「{identity_label}」と「コンテンツ戦略」に基づき、**{target_title} ({target_filename}) 用の単一のモダンでレスポンシブなHTMLファイル**を生成してください。

    ### CRITICAL INSTRUCTION: 出力形式の厳守
    - **[START HTML CODE]** というマーカーからコードの記述を開始してください。
    - **必ず** `<!DOCTYPE html>` から `</html>` まで、全てのHTML構造を完全に記述してください。
    - **必ず** `\n```eof` で出力を完全に終了してください。（コードブロックは```htmlで開始してください）

    ### 必須要件 (CRITICAL REQUIREMENTS)
    1.  **デザインフレームの維持:** デザイン（配色、フォント、Tailwind CSS）を完全に維持してください。
    2.  **ナビゲーションの統合（最重要）:**
        - このページのファイルパスは `{target_filename}` です。
        - 他のページへのリンク（例: ヘッダー、フッター）は、このパスからの**正しい相対パス**で生成する必要があります。
        - (例1) `{target_filename}` が `insights/page.html` の場合、ルートの `index.html` へのリンクは `href="../index.html"` となります。
        - (例2) `{target_filename}` が `insights/page.html` の場合、`vision/index.html` へのリンクは `href="../vision/index.html"` となります。
        - (例3) `{target_filename}` が `index.html` （ルート）の場合、`vision/index.html` へのリンクは `href="vision/index.html"` となります。
        - 渡された「確定した全ページリスト」に基づき、すべてのナビゲーションリンクをこのルールで生成してください。
    3.  **コンテンツの役割:** {content_instruction}
    4.  **Tailwind CSS:** CDNをロードし、全てのスタイリングにTailwindクラスを使用してください。
    {gtm_instructions}
    {adsense_instructions} 
    5.  **[修正] フッターの著作権:** {footer_instruction}
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
                model="gemini-3-flash-preview",
                contents=prompt_template
            )
            raw_output = response.text.strip()

            if raw_output.endswith("</html>\n```eof"):
                match = re.search(r"```html\s*(.*?)\s*```eof", raw_output, re.DOTALL)
                if match:
                    return match.group(1).strip()

            print(f"警告: コードが途中で切れたか、終了マーカーが見つかりませんでした。 for {target_filename}")

        except Exception as e:
            print(f"エラーが発生しました: {e} for {target_filename}")

    return "❌ HTMLコードの生成に失敗しました。"
