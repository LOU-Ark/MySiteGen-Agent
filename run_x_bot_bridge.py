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

# --- 環境変数からのシークレット読み込みは GitHub Actions が自動で行うため省略可能 ---
# (ただしローカルテスト用に残しておいても良い)

# --- 1. Botのセットアップ (GitHub Actionsのディレクトリ構造に合わせる) ---
# Actionsでは '../bot' にクローンされている
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__)) # agent/
BOT_DIR = os.path.abspath(os.path.join(PROJECT_ROOT, "../bot"))

if not os.path.exists(BOT_DIR):
    print(f"❌ エラー: Botディレクトリ ({BOT_DIR}) が見つかりません。Workflowの設定を確認してください。")
    sys.exit(1)

# Botの src をパスに追加
sys.path.append(os.path.join(BOT_DIR, 'src'))

# config, x_poster をインポート
try:
    import config
    import x_poster
except ImportError as e:
    print(f"❌ Botモジュールのインポートに失敗: {e}")
    sys.exit(1)

# --- 定数定義 ---
PERSONA_FILE_PATH = os.path.join(BOT_DIR, 'data', 'knowledge_base', 'persona.txt')
MODEL_NAME_PRO = "gemini-2.5-pro"

# --- ペルソナファイルの作成 (フォルダがない場合作成) ---
try:
    os.makedirs(os.path.dirname(PERSONA_FILE_PATH), exist_ok=True)
    persona_content = """
A-Kカルマ: 大清水さち著『ツインシグナル』における... (省略)...
"""
    with open(PERSONA_FILE_PATH, 'w', encoding='utf-8') as f:
        f.write(persona_content)
except Exception as e:
    print(f"⚠️ ペルソナ書き込みエラー: {e}")

# --- 補助関数 (generate_rich_content_from_topic など) ---
# (Colabで作った関数 generate_rich_content_from_topic, scrape_website_text, save_knowledge_as_json などをここにコピー)
# ★長くなるため、Colabの「実行セル2」の中身をここに貼り付けてください★
# ★ただし、INPUT_JSON_PATH の指定だけ変更します★

# ... (関数定義) ...

if __name__ == "__main__":
    print("\n--- Bot Bridge Started ---")
    
    # ⬇️ [重要] Actions用にパスを調整
    # Workflowのsedコマンドで書き換えられた場合、または相対パスで探す
    # "agent" フォルダ内で実行されるため、JSONは一つ上にあるはず
    INPUT_JSON_PATH = os.path.abspath(os.path.join(PROJECT_ROOT, "../newly_updated_articles.json"))
    # または sed で書き換えられたパス ("/home/runner/.../newly_updated_articles.json")
    
    # もし sed置換が効いていれば絶対パスになっている可能性があるためチェック
    if not os.path.exists(INPUT_JSON_PATH):
        # 同一ディレクトリも探す
        INPUT_JSON_PATH = "newly_updated_articles.json"
    
    OUTPUT_JSON_PATH = os.path.join(BOT_DIR, "data/knowledge_base/knowledge_entries.json")

    print(f"--- Reading JSON from: {INPUT_JSON_PATH} ---")
    
    if not os.path.exists(INPUT_JSON_PATH):
        print(f"ℹ️ 更新リスト ({INPUT_JSON_PATH}) がないため、処理を終了します。")
        sys.exit(0)

    # ... (以下、Colabの実行ロジックと同じ) ...
    # JSONをロードしてループ処理 -> generate_rich_content -> x_poster.post -> save_knowledge
