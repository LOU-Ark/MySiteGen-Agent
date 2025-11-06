import re
import json
from google import genai
from google.genai import types

# ⬇️ [修正] SITE_TYPE を引数に追加
def generate_final_sitemap(client, identity, SITE_TYPE='corporate'):
    """
    法人格またはパーソナル・ブランドに基づき、サイトマップを生成させる。
    """
    if client is None:
        return "❌ Geminiクライアントが初期化されていません。"

    # ⬇️ [修正] サイトタイプに応じてプロンプト（ルール）を切り替える
    if SITE_TYPE == 'corporate':
        prompt_rules = """
        ### サイトマップ生成のルール
        1. サイトの核となるメッセージと構造を反映すること。
        2. グローバルナビゲーションは、**VISION, SOLUTIONS, INSIGHTS, COLLABORATION, CONTACT**の5つをレベル1の項目とすること。
        3. 法人のミッション（データサイエンスPDCA、個別最適化）を反映した具体的なレベル2のページ構造を設計すること。
        """
        identity_label = "法人アイデンティティ"
    else: # 'personal'
        prompt_rules = """
        ### サイトマップ生成のルール
        1. サイトの核となる「個人の哲学」と「専門性」を反映すること。
        2. グローバルナビゲーションは、**ABOUT (私について), PHILOSOPHY (哲学), PROJECTS (実績), INSIGHTS (知見), CONTACT** の5つをレベル1の項目とすること。
        3. 個人の専門性（データサイエンス、AI倫理）を反映した具体的なレベル2のページ構造（例: PROJECTS配下に具体的な分析事例）を設計すること。
        """
        identity_label = "パーソナル・ブランド"
    # ⬆️ [修正] ここまで

    prompt = f"""
    あなたはウェブサイトのUXアーキテクトです。
    以下の「{identity_label}」に基づき、ユーザーの論理的思考を助ける**階層的なサイトマップ**をMarkdown形式で生成してください。

    {prompt_rules}
    4. 見出しは「## サイトマップ: [サイト名]」から開始してください。

    ### {identity_label}
    {identity}
    """

    print("Geminiモデルで最終サイトマップの階層構造を生成しています...")
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        return response.text.strip()
    except Exception as e:
        return f"❌ サイトマップの生成中にエラーが発生しました: {e}"

# ⬇️ [修正] SITE_TYPE を引数に追加
def generate_content_strategy(client, identity, sitemap, SITE_TYPE='corporate'):
    """
    法人格/ブランドとサイトマップに基づき、コンテンツ戦略の骨子を生成させる。
    """
    if client is None:
        return "❌ Geminiクライアントが初期化されていません。"

    # ⬇️ [修正] サイトタイプに応じてプロンプト（ルール）を切り替える
    if SITE_TYPE == 'corporate':
        prompt_rules = """
        ### 策定ルール
        1. **ターゲット:** Society 5.0の変革に関心のあるビジネスリーダー、研究者、および未来志向の生活者。
        2. **トーン:** 先進的、分析的、論理的、信頼感を重視すること。
        3. **出力フォーマット:** 以下の3つのセクションに分けて、具体的な見出し案と概要を箇条書きで記述すること。

        ### コンテンツ戦略の策定（出力）
        --- A. トップページ (Homepage) 戦略 ---
        --- B. VISION ページ戦略 (信頼性の確立) ---
        --- C. SOLUTIONS ページ戦略 (実行力の証明) ---
        """
        identity_label = "法人アイデンティティ"
    else: # 'personal'
        prompt_rules = """
        ### 策定ルール
        1. **ターゲット:** 採用担当者、協業パートナー、または同じ分野（データサイエンス・AI倫理）に興味を持つ技術者。
        2. **トーン:** 専門的、論理的、思慮深い、未来志向であること。
        3. **出力フォーマット:** 以下の3つのセクションに分けて、具体的な見出し案と概要を箇条書きで記述すること。

        ### コンテンツ戦略の策定（出力）
        --- A. トップページ (Homepage) 戦略 (個人の専門性が一目で分かるように) ---
        --- B. PROJECTS ページ戦略 (実績の証明) ---
        --- C. INSIGHTS ページ戦略 (専門性の発信) ---
        """
        identity_label = "パーソナル・ブランド"
    # ⬆️ [修正] ここまで

    prompt = f"""
    あなたはコンテンツストラテジストです。
    以下の「{identity_label}」と「サイトマップ」に基づき、トップページと主要ページのコンテンツ戦略（骨子）を策定してください。

    {prompt_rules}

    ### {identity_label}
    {identity}

    ### 確定済みサイトマップの主要構造
    {sitemap}
    """

    print(f"Geminiモデルで {SITE_TYPE} 用のコンテンツ戦略を策定しています...")
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        return response.text.strip()
    except Exception as e:
        return f"❌ コンテンツ戦略の生成中にエラーが発生しました: {e}"

# (generate_target_page_list は 'strategy' に基づいて生成するため、修正不要)
def generate_target_page_list(client, identity, strategy):
    """
    法人格と戦略に基づき、ナビゲーションに必要な全ページのリストをJSON形式で生成する。
    """
    prompt_extract = f"""
    あなたは、Webサイトのアーキテクトです。以下の「アイデンティティ」と「コンテンツ戦略」に基づき、サイトのグローバルナビゲーションを構成する**全ての固定ページ**のリストを、以下のJSONリスト形式で生成してください。

    ### 重要なルール
    1. グローバルナビゲーションの全要素（例: VISION, SOLUTIONS... または ABOUT, PROJECTS...）を含めること。
    2. **ファイル構造:** 主要セクションは、**サブディレクトリに配置**し、ファイル名を **`セクション名/index.html`** としてください。（例: vision/index.html や projects/index.html）
    3. ユーティリティページ（ポリシー）は、`legal/` ディレクトリに配置してください。
    4. 目的 (purpose) は、そのページが持つべき戦略的な役割を簡潔に記述すること。

    【抽出フォーマット】
    [
      {{"title": "ホーム", "file_name": "index.html", "purpose": "..."}},
      {{"title": "...", "file_name": ".../index.html", "purpose": "..."}},
      ... (全ページを完成させる)
    ]

    ### アイデンティティ
    {identity}

    ### コンテンツ戦略の要点
    {strategy}
    """

    print("\n📢 AIが戦略に基づき、ターゲットページリストを動的生成中...")
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt_extract,
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )
        target_list = json.loads(response.text.strip())
        print(f"✅ ターゲットリストの抽出と構造化に成功しました ({len(target_list)} 件)。")
        return target_list
    except Exception as e:
        print(f"❌ ターゲットリストの動的抽出に失敗しました: {e}")
        return []
