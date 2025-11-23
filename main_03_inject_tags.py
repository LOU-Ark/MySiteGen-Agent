import os
import sys
import re
from bs4 import BeautifulSoup

# --- 0. 設定 ---
try:
    SCRIPT_PATH = os.path.realpath(__file__)
except NameError:
    SCRIPT_PATH = os.getcwd()

SCRIPT_DIR = os.path.dirname(SCRIPT_PATH)
# パスの互換性を考慮 (output/docs を優先)
BASE_DIR = os.path.join(SCRIPT_DIR, "output", "docs")

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


def main():
    # --- 1. IDの取得 (完全自動化対応: 入力待機を排除) ---
    GTM_ID = None
    ADSENSE_CLIENT_ID = None

    try:
        from google.colab import userdata
        try:
            GTM_ID = userdata.get('GTM_ID')
            if GTM_ID: print(f"✅ シークレットから GTM_ID ({GTM_ID}) を読み込みました。")
        except: pass
        
        try:
            ADSENSE_CLIENT_ID = userdata.get('ADSENSE_CLIENT_ID')
            if ADSENSE_CLIENT_ID: print(f"✅ シークレットから AdSense ID を読み込みました。")
        except: pass
    except ImportError:
        pass

    # ⬇️ [修正] IDがない場合、入力(input)を求めずにスキップする
    if not GTM_ID and not ADSENSE_CLIENT_ID:
        print("ℹ️ GTM ID / AdSense ID がシークレットに見つかりませんでした。")
        print("ℹ️ タグ挿入プロセスをスキップして終了します（自動実行を継続）。")
        return # エラー終了(sys.exit)ではなく、正常終了(return)させる

    print(f"--- 🏷️ タグ挿入スクリプト開始 ---")

    # --- 2. サイトディレクトリのスキャン ---
    # フォルダが見つからない場合のフォールバック
    if not os.path.isdir(BASE_DIR):
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
                         # print(f"⚠️ スキップ: <head>または<body>なし: {filename}")
                         continue

                    # --- 3. 既存タグの削除 (重複防止) ---
                    if ADSENSE_CLIENT_ID:
                        existing_adsense = soup.head.find_all("script", {"src": re.compile(r"adsbygoogle\.js")})
                        for tag in existing_adsense:
                            tag.extract()
                            modified = True

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
                        gtm_script_tag = BeautifulSoup(GTM_HEAD_TEMPLATE.format(GTM_ID=GTM_ID), 'html.parser')
                        insert_position = 1 if ADSENSE_CLIENT_ID else 0
                        soup.head.insert(insert_position, gtm_script_tag)

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