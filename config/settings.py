import os
from dotenv import load_dotenv

# --- 環境設定 ---
# プロジェクトルートの特定と .env の読み込み
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(ROOT_DIR, ".env"))

# --- APIキー管理 ---
# 複数のAPIキーをリストとして管理し、ローテーション可能にする
# .env で GEMINI_API_KEYS="key1,key2,key3" のようにカンマ区切りで指定可能
API_KEYS = []

# パターン1: カンマ区切りリスト (GEMINI_API_KEYS)
env_keys = os.environ.get("GEMINI_API_KEYS")
if env_keys:
    API_KEYS = [k.strip() for k in env_keys.split(',') if k.strip()]

# パターン2: 単一キー (GEMINI_API_KEY) - リストが空の場合のフォールバック
if not API_KEYS:
    single_key = os.environ.get("GEMINI_API_KEY")
    if single_key:
        API_KEYS.append(single_key)

# 参考: Colab等の場合、ここではロードできない可能性があるため、
# client_utilsで最終的なチェックを行う

# --- AIモデル定義 ---
# 使用するAIモデルの定義
# 最新の安定版やプレビュー版を一括で切り替えられます
DEFAULT_MODEL = "gemini-3-flash-preview"

# プロフェッショナルな生成タスク（企画、リファクタリングなど）
MODEL_NAME_PRO = "gemini-3-flash-preview"

# HTMLページ生成タスク（長文出力が必要なため、安定したモデルを推奨）
# Flash 3 で切れる場合は "gemini-1.5-pro" に戻すと安定します
MODEL_NAME_GEN = "gemini-3-flash-preview" 

MODEL_NAME_FLASH = "gemini-3-flash-preview"
