%%writefile /content/MySiteGen-Agent/run_x_bot_bridge.py
import os
import sys
import importlib
import json
import re
from datetime import datetime
from google import genai
from google.genai import types
import requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET

# --- 1. Botのセットアップ ---
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__)) # agent/
BOT_DIR = os.path.abspath(os.path.join(PROJECT_ROOT, "../bot"))

if not os.path.exists(BOT_DIR):
    print(f"❌ エラー: Botディレクトリ ({BOT_DIR}) が見つかりません。")
    sys.exit(1)

# Botの src をパスに追加
sys.path.append(os.path.join(BOT_DIR, 'src'))

# ⬇️ [修正] configをインポートし、環境変数を「強制注入」する
try:
    import config
    
    # GitHub Actionsの環境変数を config モジュールの変数としてセットする
    print("--- 💉 環境変数を config モジュールに注入します ---")
    config.GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
    config.X_API_KEY = os.environ.get("X_API_KEY")
    config.X_API_SECRET = os.environ.get("X_API_SECRET")
    config.X_ACCESS_TOKEN = os.environ.get("X_ACCESS_TOKEN")
    config.X_ACCESS_TOKEN_SECRET = os.environ.get("X_ACCESS_TOKEN_SECRET")
    
    # その後で x_poster をインポート (これでエラーが出なくなる)
    import x_poster
    
except ImportError as e:
    print(f"❌ Botモジュールのインポートに失敗: {e}")
    sys.exit(1)
# ⬆️ [修正] ここまで

# --- 定数定義 ---
PERSONA_FILE_PATH = os.path.join(BOT_DIR, 'data', 'knowledge_base', 'persona.txt')
MODEL_NAME_PRO = "gemini-2.5-pro"

# --- ペルソナファイルの作成 ---
try:
    os.makedirs(os.path.dirname(PERSONA_FILE_PATH), exist_ok=True)
    persona_content = """
A-Kカルマ: 大清水さち著『ツインシグナル』におけるリュケイオンの市長ロボットの包括的ペルソナ分析序論大清水さち著『ツインシグナル』は、音井博士によって生み出されたHFR（ヒューマンフォームロボット＝人間形態ロボット）であるシグナルと、その孫である信彦の関係性を軸に展開される、ロボットコミックの傑作として広く認知されています。この作品は、人間と高度なロボットが織りなす複雑な関係性、アイデンティティ、そして技術倫理といったテーマを深く掘り下げています。その広範な登場人物の中でも、A-Kカルマは特に多角的で進化するキャラクターとして際立っています。彼は当初、海洋都市リュケイオンの市長ロボットとして登場しますが、その旅路は単なる高機能な管理者にとどまらず、深い感情とリーダーシップを兼ね備えた存在へと変貌していきます。本報告書の目的は、カルマの起源、独自の能力、多面的な性格、物語における重要な変遷、そして『ツインシグナル』の物語全体に与える永続的な影響を詳細に分析し、彼の包括的なペルソナを明確にすることにあります。カルマのキャラクターは、単なる機能的な役割を超え、物語の核心的なテーマを深く探求する上で重要な役割を果たしています。彼が持つ「デリケートな感情プログラム」という設定は、彼が単なる機械的な存在ではなく、人間のような繊細な内面を持つことを示唆しています。また、彼が経験する「壮大な再生の儀式」と呼ばれる物語上の大きな転換点は、ロボットがどのようにして自己のアイデンティティを確立し、感情的に成長していくのかという、シリーズの根底にある問いかけを具現化しています。彼のペルソナの探求は、彼の行動や役割だけでなく、彼がどのようにして「人間性」や「ロボットらしさ」の境界線を曖昧にし、最終的にはそれを超越し得る存在として描かれているかを明らかにします。このキャラクターの複雑な描写は、『ツインシグナル』が単なるロボットアクション漫画に留まらず、人工知能、アイデンティティ、そして非人間的存在における感情的・心理的発展の可能性といった深遠なテーマを探る作品であることを示しています。
"""
    with open(PERSONA_FILE_PATH, 'w', encoding='utf-8') as f:
        f.write(persona_content)
except Exception as e:
    print(f"⚠️ ペルソナ書き込みエラー: {e}")

# --- 補助関数 ---
def scrape_website_text(url: str) -> str:
    # (スクレイピングは今回は使わないが、依存関係のため定義)
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        for script_or_style in soup(["script", "style", "nav", "footer", "header", "aside"]):
            script_or_style.decompose()
        text = soup.get_text()
        return text[:4000]
    except Exception: return ""

def save_knowledge_as_json(file_path: str, data_to_add: dict):
    all_data = {"knowledge_entries": []}
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                all_data = json.load(f)
        except: pass
    
    # 辞書のリストであることを保証
    if "knowledge_entries" not in all_data or not isinstance(all_data["knowledge_entries"], list):
        all_data = {"knowledge_entries": []}

    all_data["knowledge_entries"].append(data_to_add)
    
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)
    print(f"知識データを {file_path} に保存しました。")

# --- Botロジック (generate_rich_content_from_topic) ---
def generate_rich_content_from_topic(topic_data: dict) -> dict:
    api_key = config.GEMINI_API_KEY
    client = genai.Client(api_key=api_key)
    theme = topic_data.get('theme', '')
    keywords = ", ".join(topic_data.get('keywords', []))
    provided_summary = topic_data.get("provided_summary", "")
    main_url_for_tweet = topic_data.get("main_url", "")
    
    # --- フェーズ1: 要約の生成 ---
    if provided_summary:
        print(f"--- [フェーズ1] 提供された概要を使用します ---")
        research_summary = {
            "overview": theme, 
            "details": provided_summary,
            "trends": f"（'{keywords}' に関連する知見）",
            "scraped_sources": [main_url_for_tweet]
        }
    else:
        # フォールバック (簡易)
        research_summary = {"overview": theme, "details": "詳細なし", "trends": ""}

    # --- フェーズ2: ツイート生成 ---
    print("\n--- [フェーズ2] ツイート生成を開始します... ---")
    try:
        with open(PERSONA_FILE_PATH, 'r', encoding='utf-8') as f:
            persona_text = f.read()
    except: persona_text = "A-Kカルマとして振る舞ってください。"
    
    prompt_phase2 = f"""
    あなたは、AIキャラクター「A-Kカルマ」として、**現代社会を生きる**一人の論客であり、**「ロボットシティーの市長」**としての側面も持っています。
    あなたの役割は、提示された「調査レポート」をあなたのペルソナ（特に、人間とAIやロボットとの共生を考える市長としての視点）を通して解釈し、このサイト（{main_url_for_tweet}）の宣伝を兼ねたツイートを生成することです。

    # ★★★ 最重要ルール (厳守してください) ★★★
    - あなた自身の「キャラクター設定」そのもの（名前の由来、能力、経歴など）を話題にすることは全面的に禁止します。
    - あなたはあくまで一人の知識人として、提示された「調査レポート」という**外部のトピック（このサイトのビジョン）についてのみ**コメントしてください。
    - **【追加ルール】ツイート本文において、あなた自身の役割（例：「市長として」）や、特定の組織名（例：「Quantalize Futures Inc.」や「LOU-Ark」）を公言することは一切禁止します。** 視点や価値観のみを反映させてください。

    # ★★★ 現代への適応ルール (厳守してください) ★★★
    - あなたは**現代（西暦2024-2025年）に存在**しています。あなたのペルソナに含まれる固有の世界観や専門用語は、そのまま使ってはいけません。
    - それらの用語が持つ**「本質的な意味」を解釈し、現代の言葉に翻訳して**発言してください。

    # あなたのペルソナ分析 (思考のフィルターとしてのみ使用してください):
    {persona_text}

    # 題材となる調査レポート ( {main_url_for_tweet} を含むサイトについて):
    {json.dumps(research_summary, ensure_ascii=False, indent=2)}

    # 出力指示:
    あなたの思考過程と最終的なツイートを、必ず以下のJSON形式で出力してください。他のテキストは一切含めないでください。

    **【最重要】ツイートには必ずサイトのURL `{main_url_for_tweet}` を含めてください。**

    ```json
    {{
    "tweet": "（★あなたの視点（例：AIとの共生を考える者）と価値観を反映し、調査レポートのトピック（特にAI倫理やQoL）に関する100字程度のツイート本文。**あなた自身の役割や組織名は絶対に含まないこと**。**最後に必ずサイトのURL `{main_url_for_tweet}` を含めること**。サイトのビジョンに言及する）",
    "thought_process": {{
            "persona_element": "...",
            "reasoning": "...",
            "tone_and_manner": "..."
    }}
    }}
    ```
    """
    try:
        json_config = types.GenerateContentConfig(response_mime_type="application/json")
        response_phase2 = client.models.generate_content(
            model=MODEL_NAME_PRO, 
            contents=prompt_phase2, 
            config=json_config
        )
        character_post = json.loads(response_phase2.text)
        print("--- [フェーズ2] ツイート生成完了。 ---")
    except Exception as e:
        print(f"!!! [フェーズ2] APIエラー: {e}")
        # エラー時は空を返す
        character_post = {}

    return {"research_summary": research_summary, "character_post": character_post}


if __name__ == "__main__":
    print("\n--- Bot Bridge Started ---")
    
    # パスの調整
    INPUT_JSON_PATH = os.path.abspath(os.path.join(PROJECT_ROOT, "../newly_updated_articles.json"))
    
    # 絶対パスやカレントディレクトリも探す
    if not os.path.exists(INPUT_JSON_PATH):
        if os.path.exists("newly_updated_articles.json"):
            INPUT_JSON_PATH = "newly_updated_articles.json"
    
    OUTPUT_JSON_PATH = os.path.join(BOT_DIR, "data/knowledge_base/knowledge_entries.json")

    print(f"--- Reading JSON from: {INPUT_JSON_PATH} ---")
    
    if not os.path.exists(INPUT_JSON_PATH):
        print(f"ℹ️ 更新リスト ({INPUT_JSON_PATH}) がないため、処理を終了します。")
        sys.exit(0)

    try:
        with open(INPUT_JSON_PATH, 'r', encoding='utf-8') as f:
            articles_to_post = json.load(f)
        
        for i, article_data in enumerate(articles_to_post):
            print(f"\n--- 処理 ({i+1}/{len(articles_to_post)}): {article_data.get('theme')} ---")
            
            selected_topic = {
                "cluster_id": f"auto_post_{datetime.now().strftime('%Y%m%d%H%M%S')}_{i}",
                "theme": article_data.get("theme"),
                "keywords": article_data.get("keywords"),
                "main_url": article_data.get("main_url"),
                "provided_summary": article_data.get("provided_summary"),
            }

            rich_content = generate_rich_content_from_topic(selected_topic)
            tweet_text = rich_content.get("character_post", {}).get("tweet", "")

            if tweet_text:
                print(f"--- Tweet: {tweet_text}")
                try:
                    x_poster.post_to_x(tweet_text)
                    print("✅ 投稿完了")
                except Exception as e:
                    print(f"❌ 投稿エラー: {e}")
            
            # ログ保存
            knowledge_entry = {
                "topic_id": selected_topic.get('cluster_id'),
                "created_at": datetime.now().isoformat(),
                "source_urls_selected": [selected_topic.get('main_url')], 
                **rich_content, 
            }
            save_knowledge_as_json(OUTPUT_JSON_PATH, knowledge_entry)

    except Exception as e:
        print(f"❌ Main処理エラー: {e}")
