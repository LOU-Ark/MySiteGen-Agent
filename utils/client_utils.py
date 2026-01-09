import os
import sys
from google import genai
try:
    from google.colab import userdata
except ImportError:
    # Colab以外の環境（ローカル実行など）のためのフォールバック
    userdata = None

import random
from config import settings

def setup_client():
    try:
        if userdata:
            # Colab環境
            GOOGLE_API_KEY = userdata.get('GEMINI_API_KEY')
            if not GOOGLE_API_KEY:
                # Colabでもsettingsからキーを拾えるようにする（Secrets未設定時など）
                if settings.API_KEYS:
                     GOOGLE_API_KEY = random.choice(settings.API_KEYS)
                else:
                    raise ValueError("GEMINI_API_KEY が Colab Secrets に設定されていません。")
        else:
            # ローカル環境
            # settings.py でロード・パース済みのリストからランダムに選択
            if settings.API_KEYS:
                GOOGLE_API_KEY = random.choice(settings.API_KEYS)
                # Debug: リストが複数ある場合、どれが選ばれたか（末尾4桁）を表示しても良いが、一旦シンプルに
            else:
                # 万が一 settings.py 経由で取れなかった場合の最終フォールバック (os.environ directly)
                GOOGLE_API_KEY = os.environ.get('GEMINI_API_KEY')
            
            if not GOOGLE_API_KEY:
                raise EnvironmentError("GEMINI_API_KEY (または GEMINI_API_KEYS) が環境変数に設定されていません。")
        
        # Debug: キーの確認 (セキュリティのため一部隠す)
        if len(GOOGLE_API_KEY) > 10:
             print(f"  🔑 Using API Key: {GOOGLE_API_KEY[:4]}...{GOOGLE_API_KEY[-4:]}")
        else:
             print(f"  🔑 Using API Key: (Too short/Invalid)")  

        return genai.Client(api_key=GOOGLE_API_KEY)
        
    except Exception as e:
        print(f"❌ クライアント初期化エラー: {e}")
        return None
