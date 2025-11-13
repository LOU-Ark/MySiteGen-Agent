import os
import sys
from google import genai
try:
    from google.colab import userdata
except ImportError:
    # Colab以外の環境（ローカル実行など）のためのフォールバック
    userdata = None

def setup_client():
    """Geminiクライアントを初期化"""
    try:
        if userdata:
            # Colab環境
            GOOGLE_API_KEY = userdata.get('GEMINI_API_KEY')
            if not GOOGLE_API_KEY:
                raise ValueError("GEMINI_API_KEY が Colab Secrets に設定されていません。")
        else:
            # ローカル環境
            GOOGLE_API_KEY = os.environ.get('GEMINI_API_KEY')
            if not GOOGLE_API_KEY:
                raise EnvironmentError("GEMINI_API_KEY が環境変数に設定されていません。")
        
        return genai.Client(api_key=GOOGLE_API_KEY)
        
    except Exception as e:
        print(f"❌ クライアント初期化エラー: {e}")
        return None
