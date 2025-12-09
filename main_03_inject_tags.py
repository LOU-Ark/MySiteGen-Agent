import os
import sys
import re
import threading
import time
from bs4 import BeautifulSoup

# --- 0. 設定 ---
try:
    SCRIPT_PATH = os.path.realpath(__file__)
except NameError:
    SCRIPT_PATH = os.getcwd()

SCRIPT_DIR = os.path.dirname(SCRIPT_PATH)
# パスの互換性を考慮 (output/docs を優先)
BASE_DIR = os.path.join(SCRIPT_DIR, "output", "docs")

# タイムアウト時間（秒）
INPUT_TIMEOUT_SECONDS = 10

# GTMスニペットのテンプレート
GTM_HEAD_TEMPLATE = """
<script>(function(w,d,s,l,i){{w[l]=w[l]||[];w[l].push({{'gtm.start':
new Date().getTime(),event:'gtm.js'}});var f=d.getElementsByTagName(s)[0],
j=d.createElement(s),dl=l!='dataLayer'?'&l='+l:'';j.async=true;j.src=
'https://www.googletagmanager.com/gtm.js?id='+i+dl;f.parentNode.insertBefore(j,f);
}})(window,document,'script','dataLayer','{GTM_ID}');</script>
""".strip()

GTM_BODY_TEMPLATE = """
<noscript><iframe src="https://www.googletagmanager.com/ns.html?id={GTM_ID}"
height="0" width="0" style="display:none;visibility:hidden"></iframe></noscript>
""".strip()

# AdSenseスニペットのテンプレート
ADSENSE_HEAD_TEMPLATE = """
<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={ADSENSE_CLIENT_ID}"
     crossorigin="anonymous"></script>
""".strip()


def input_with_timeout(prompt, timeout):
    """
    指定された時間(秒)だけ入力を待つ関数。
    タイムアウトした場合は None を返す。
    """
    print(f"{prompt} ({timeout}秒待機): ", end='', flush=True)
    
    result = []
    
    def get_input():
        try:
            # 入力を受け取りリストに格納
            # sys.stdin.readline() はEnterが押されるまでブロックする
            data = sys.stdin.readline().strip()
            result.append(data)
        except:
            pass

    # 入力待ち用のスレッドを作成
    t = threading.Thread(target=get_input)
    t.daemon = True # メインプロセス終了時に道連れにする
    t.start()
    
    # 指定時間待機
    t.join(timeout)
    
    if t.is_alive():
        # タイムアウトした場合
        print("\n⏰ タイムアウト: 入力がなかったためスキップします。")
        return None
    else:
        # 入力があった場合
        if result and result[0]:
            return result[0]
        return None


def main():
    GTM_ID = None
    ADSENSE_CLIENT_ID = None

    # --- 1. タイムアウト付き入力でIDを取得 ---
    
    # GTM ID の入力待ち
    user_input_gtm = input_with_timeout("GTM IDを入力してください (例: GTM-XXXXXX)", INPUT_TIMEOUT_SECONDS)
    if user_input_gtm:
        GTM_ID = user_input_gtm
        print(f"👉 GTM_ID: {GTM_ID} を適用します。")

    # AdSense ID の入力待ち
    user_input_ads = input_with_timeout("AdSense Client IDを入力してください (例: ca-pub-XXXXXX)", INPUT_TIMEOUT_SECONDS)
    if user_input_ads:
        ADSENSE_CLIENT_ID = user_input_ads
        print(f"👉 AdSense ID を適用します。")

    # IDがどちらもない場合は終了
    if not GTM_ID and not ADSENSE_CLIENT_ID:
        print("ℹ️ 有効なIDが入力されませんでした。")
        print("ℹ️ タグ挿入プロセスをスキップして終了します。")
        return

    print(f"--- 🏷️ タグ挿入スクリプト開始 ---")

    # --- 2. サイトディレクトリのスキャン ---
    if not os.path.isdir(BASE_DIR):
        # 代替パスの確認
        ALT_BASE_DIR = os.path.join(SCRIPT_DIR, "reports", "docs")
        if os.path.isdir(ALT_BASE_DIR):
            BASE_DIR_TARGET = ALT_BASE_DIR
        else:
            print(f"❌ サイトディレクトリ ({BASE_DIR}) が見つかりません。スキップします。")
            return
    else:
        BASE_DIR_TARGET = BASE_DIR

    files_processed = 0
    files_skipped = 0
    TARGET_EXTENSIONS = ('.html', '.htm')

    for root, _, files in os.walk(BASE_DIR_TARGET):
        for filename in files:
            if filename.lower().endswith(TARGET_EXTENSIONS):
                full_path = os.path.join(root, filename)

                try:
                    with open(full_path, 'r', encoding='utf-8') as f:
                        soup = BeautifulSoup(f, 'html.parser')

                    modified = False

                    if not soup.head or not soup.body:
                         continue

                    # --- 3. 既存タグの削除 (重複防止) ---
                    # AdSense
                    if ADSENSE_CLIENT_ID:
                        existing_adsense = soup.head.find_all("script", {"src": re.compile(r"adsbygoogle\.js")})
                        for tag in existing_adsense:
                            tag.extract()
                            modified = True

                    # GTM
                    if GTM_ID:
                        # Headタグ
                        existing_gtm_head = soup.head.find_all("script", string=re.compile(r"gtm\.js"))
                        for tag in existing_gtm_head:
                            if GTM_ID in tag.string:
                                tag.extract()
                                modified = True
                        # Bodyタグ
                        existing_gtm_body = soup.body.find_all("iframe", src=re.compile(r"googletagmanager\.com"))
                        for tag in existing_gtm_body:
                             if tag.parent.name == 'noscript':
                                 tag.parent.extract()
                                 modified = True

                    # --- 4. AdSenseタグの挿入 ---
                    if ADSENSE_CLIENT_ID:
                        adsense_script_tag = BeautifulSoup(ADSENSE_HEAD_TEMPLATE.format(ADSENSE_CLIENT_ID=ADSENSE_CLIENT_ID), 'html.parser')
                        soup.head.insert(0, adsense_script_tag)
                        modified = True

                    # --- 5. GTMタグの挿入 ---
                    if GTM_ID:
                        # Head挿入 (AdSenseがある場合はその次、なければ先頭)
                        gtm_script_tag = BeautifulSoup(GTM_HEAD_TEMPLATE.format(GTM_ID=GTM_ID), 'html.parser')
                        insert_position = 1 if ADSENSE_CLIENT_ID else 0
                        soup.head.insert(insert_position, gtm_script_tag)

                        # Body挿入 (先頭)
                        gtm_noscript_tag = BeautifulSoup(GTM_BODY_TEMPLATE.format(GTM_ID=GTM_ID), 'html.parser')
                        soup.body.insert(0, gtm_noscript_tag)
                        modified = True

                    # --- 6. 保存 ---
                    if modified:
                        html_output = str(soup)
                        # bs4による属性の崩れを修正
                        html_output = re.sub(r'async=""', 'async', html_output)
                        html_output = re.sub(r'crossorigin=""', 'crossorigin', html_output)

                        with open(full_path, 'w', encoding='utf-8') as f:
                            f.write(html_output)
                        files_processed += 1
                    else:
                        files_skipped += 1

                except Exception as e:
                    print(f"❌ エラー ({filename}): {e}")

    print(f"✅ 合計 {files_processed} 件のファイルにタグを挿入/更新しました。")

if __name__ == "__main__":
    main()