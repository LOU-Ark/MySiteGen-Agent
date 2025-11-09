import os
import sys
import re
from bs4 import BeautifulSoup

# --- 0. 設定 ---
# ⬇️ [修正] スクリプト自身の場所を基準にした相対パスに変更
try:
    # スクリプトファイル自身の絶対パスを取得
    # (例: /content/MySiteGen-Agent/main_03_inject_tags.py)
    SCRIPT_PATH = os.path.realpath(__file__)
except NameError:
    # Colabの対話環境などで __file__ が未定義の場合のフォールバック
    SCRIPT_PATH = os.getcwd()

# スクリプトが置かれているディレクトリを取得 (例: /content/MySiteGen-Agent)
SCRIPT_DIR = os.path.dirname(SCRIPT_PATH)

# 探したい 'docs' フォルダのパスを構築
# (例: /content/MySiteGen-Agent + reports + docs)
BASE_DIR = os.path.join(SCRIPT_DIR, "reports", "docs")
# ⬆️ [修正] "output" ではなく "reports" を経由

# (GTMとAdSenseのテンプレート定義は変更なし)
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
<script async src="https://pagead2.googletagmanager.com/pagead/js/adsbygoogle.js?client={ADSENSE_CLIENT_ID}"
     crossorigin="anonymous"></script>
""".strip()


def main():
    # --- 1. IDの入力 ---
    GTM_ID = input("Google Tag Manager ID (GTM-XXXXXXX) を入力してください (スキップはEnter): ").strip()
    ADSENSE_CLIENT_ID = input("Google AdSense Client ID (ca-pub-...) を入力してください (スキップはEnter): ").strip()

    if not GTM_ID and not ADSENSE_CLIENT_ID:
        print("❌ GTM ID と AdSense ID の両方が入力されませんでした。処理を終了します。")
        sys.exit(1)

    GTM_ID = GTM_ID or None
    ADSENSE_CLIENT_ID = ADSENSE_CLIENT_ID or None

    print(f"--- 🏷️ タグ挿入スクリプト (GTM: {GTM_ID}, AdSense: {ADSENSE_CLIENT_ID}) 開始 ---")

    # --- 2. サイトディレクトリのスキャン ---
    if not os.path.isdir(BASE_DIR):
        print(f"❌ サイトディレクトリ ({BASE_DIR}) が見つかりません。")
        sys.exit(1)

    files_processed = 0
    files_skipped = 0
    TARGET_EXTENSIONS = ('.html', '.htm')

    print(f"--- 🏭 {BASE_DIR} 配下の全HTMLファイルをスキャン・処理中 ---")

    for root, _, files in os.walk(BASE_DIR):
        for filename in files:
            if filename.lower().endswith(TARGET_EXTENSIONS):
                full_path = os.path.join(root, filename)

                try:
                    with open(full_path, 'r', encoding='utf-8') as f:
                        soup = BeautifulSoup(f, 'html.parser')

                    modified = False

                    if not soup.head or not soup.body:
                         print(f"⚠️ 警告: <head>または<body>タグなし (スキップ): {full_path}")
                         continue

                    # --- 3. 既存のタグを「検索」 (変更なし) ---
                    adsense_found = False
                    if ADSENSE_CLIENT_ID:
                        existing_adsense = soup.head.find_all("script", {"src": re.compile(r"adsbygoogle\.js")})
                        for tag in existing_adsense:
                            if ADSENSE_CLIENT_ID in tag.get('src', ''):
                                adsense_found = True
                            tag.extract()
                            modified = True

                    gtm_head_found = False
                    if GTM_ID:
                        existing_gtm_head = soup.head.find_all("script", string=re.compile(f"dataLayer','{GTM_ID}'"))
                        for tag in existing_gtm_head:
                            gtm_head_found = True
                            tag.extract()
                            modified = True

                    gtm_body_found = False
                    if GTM_ID:
                        existing_gtm_body = soup.body.find_all("noscript", string=re.compile(f"id={GTM_ID}"))
                        for tag in existing_gtm_body:
                            gtm_body_found = True
                            tag.extract()
                            modified = True

                    # --- 4. AdSenseタグの挿入 (変更なし) ---
                    if ADSENSE_CLIENT_ID:
                        adsense_script_tag = BeautifulSoup(ADSENSE_HEAD_TEMPLATE.format(ADSENSE_CLIENT_ID=ADSENSE_CLIENT_ID), 'html.parser')
                        soup.head.insert(0, adsense_script_tag)
                        modified = True

                    # --- 5. GTMタグの挿入 (変更なし) ---
                    if GTM_ID:
                        gtm_script_tag = BeautifulSoup(GTM_HEAD_TEMPLATE.format(GTM_ID=GTM_ID), 'html.parser')
                        insert_position = 1 if ADSENSE_CLIENT_ID else 0
                        soup.head.insert(insert_position, gtm_script_tag)

                        gtm_noscript_tag = BeautifulSoup(GTM_BODY_TEMPLATE.format(GTM_ID=GTM_ID), 'html.parser')
                        soup.body.insert(0, gtm_noscript_tag)

                        modified = True

                    # --- 6. ファイルを上書き保存 (変更があった場合のみ) ---
                    if modified:
                        
                        # [修正] BeautifulSoupの出力を一度文字列（str）として取得
                        html_output = str(soup)
                        
                        # [修正] 正規表現を使い、'async=""' を 'async' に置換
                        html_output = re.sub(r'async=""', 'async', html_output)
                        # [修正] crossorigin="" も同様に置換
                        html_output = re.sub(r'crossorigin=""', 'crossorigin', html_output)

                        with open(full_path, 'w', encoding='utf-8') as f:
                            f.write(html_output)
                            
                        print(f"✅ タグ挿入/修正完了: {full_path}")
                        files_processed += 1
                    else:
                        files_skipped += 1

                except Exception as e:
                    print(f"❌ エラー ({full_path}): {e}")

    print(f"\n--- 🏷️ スクリプト完了 ---")
    print(f"✅ 合計 {files_processed} 件のHTMLファイルにタグを挿入/修正しました。")
    print(f"ℹ️ 合計 {files_skipped} 件のHTMLファイルは変更ありませんでした。")


if __name__ == "__main__":
    main()
