# MySiteGen-Agent 共通設定ファイル

# 使用するAIモデルの定義
# 最新の安定版やプレビュー版を一括で切り替えられます
DEFAULT_MODEL = "gemini-3-flash-preview"

# プロフェッショナルな生成タスク（企画、リファクタリングなど）
MODEL_NAME_PRO = "gemini-3-flash-preview"

# HTMLページ生成タスク（長文出力が必要なため、安定したモデルを推奨）
# Flash 3 で切れる場合は "gemini-1.5-pro" に戻すと安定します
MODEL_NAME_GEN = "gemini-3-flash-preview" 

MODEL_NAME_FLASH = "gemini-3-flash-preview"
