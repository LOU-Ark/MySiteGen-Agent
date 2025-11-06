# MySiteGen-Agent

## 概要

`MySiteGen-Agent`は、Google Gemini APIを活用したPythonベースのAIエージェントシステムです。単一の「理念（`opinion.txt`）」ファイルに基づき、\*\*「法人サイト」**または**「個人ポートフォリオ」\*\*を選択的に自動構築し、継続的にコンテンツを改善・拡張します。

このシステムは、単なるHTMLジェネレーターではなく、\*\*Webサイトの完全なライフサイクル（戦略策定 → 初回構築 → 分析 → 改善）\*\*を自動化するよう設計されています。

-----

## 主な機能とワークフロー

このプロジェクトは、複数の「実行スクリプト」（`main_*.py`）によって構成されています。

### 1\. `main_01_initial_build.py` (フェーズ1-4: 初回構築)

  * **サイトタイプの選択:** 実行時に「法人」か「個人」かを質問します。
  * **アイデンティティ生成 (`agent_01`):** `config/opinion.txt` を読み込み、「法人格」または「パーソナル・ブランド」をAIが定義します。
  * **サイト名生成:** AIがアイデンティティに基づき、サイト名（例: `seimei-chisei-ark`）を動的に命名します。
  * **戦略策定 (`agent_02`):** サイトタイプに合わせたサイトマップ（例: `PROJECTS` or `SOLUTIONS`）と戦略をAIが策定します。
  * **ハブページ生成 (`agent_03`):** 策定された戦略に基づき、サイトの骨格となる全ハブページ（`index.html` など）のHTMLをAIが一括生成します。

### 2\. `main_02_improvement_cycle.py` (フェーズ5-6: 改善サイクル)

  * **戦略的バランス分析 (`agent_04`):**
      * AIが既存サイト（`planned_articles.md`）を分析し、「`vision/` 21件」「`solutions/` 5件」といった**記事数の偏り**を検出します。
      * 「Vision偏愛」を避け、記事数が最も少ない戦略的ハブ（例: `solutions/index.html`）を次のターゲットとして選定します。
  * **詳細記事の企画・生成 (`agent_04`, `agent_03`):**
      * 選定されたハブを補強するため、AIが**3件の新しい詳細記事**を企画・生成します。
  * **自動内部リンク構築 (WBS 5.5/5.6):**
      * AIが該当するハブページ（`solutions/index.html`）を自動でスキャンし、**新旧すべての記事**（5+3=8件）へのリンク（目次）を含む形で\*\*ハブページを再生成（上書き）\*\*します。
  * **計画書の更新:** `planned_articles.md` を最新の状態（全記事リスト）に更新します。

### 3\. ユーティリティ・スクリプト

  * **`main_03_inject_tags.py` (タグ挿入):**
      * AIを使わず、`docs/` フォルダ内の全HTMLをスキャンし、GTM (`GTM-XXXXXXX`) および AdSense (`ca-pub-...`) タグを`<head>`と`<body>`の正しい位置に効率的に挿入（または修正）します。
  * **`main_04_generate_sitemap.py` (SEO):**
      * `planned_articles.md`（全体計画）を読み込み、Googleに通知するための `sitemap.xml` を `docs/` フォルダに自動生成します。

-----

## 🚀 実行ワークフロー (Usage)

### ステップ1: セットアップ

1.  **リポジトリのクローン:**
    ```bash
    git clone https://github.com/LOU-Ark/MySiteGen-Agent.git
    cd MySiteGen-Agent
    ```
2.  **依存関係のインストール:**
    ```bash
    pip install -r requirements.txt
    ```
3.  **理念の定義:**
      * `config/opinion.txt` を開き、あなたの核となる理念や哲学を記述します。
4.  **APIキーの設定 (Colab):**
      * Colabの「シークレット」（鍵アイコン）に以下を設定します。
          * `GEMINI_API_KEY`: （あなたのGoogle AI APIキー）
          * `GITHUB_PAT`: （GitHubへのPush時に使用するアクセストークン）

### ステップ2: 初回サイト構築 (main\_01)

以下のコマンドを実行します。

```bash
%run main_01_initial_build.py
```

  * `「1: 法人」か「2: 個人」か`を尋ねられます。
  * AIがサイト名（例: `anima-cognita-portfolio`）を決定し、`output_website/anima-cognita-portfolio/` にHTMLサイト（骨格）を生成します。

### ステップ3: デプロイ準備 (docs/ への移動)

AIが生成したサイトを、GitHub Pages公開用の `docs` フォルダに移動させます。
（`anima-cognita-portfolio` の部分は、`main_01` のログに出力された実際のスラッグ名に置き換えてください）

```bash
# 既存のdocsがあれば削除
!rm -rf docs

# AIが生成したサイトを 'docs' にリネーム（移動）
!mv output_website/anima-cognita-portfolio docs
```

### ステップ4: GTM/AdSenseタグの挿入 (main\_03)

`docs/` フォルダ内の全HTMLに、計測タグとAdSense審査コードを挿入します。

```bash
%run main_03_inject_tags.py
```

  * `GTM-XXXXXXX` IDの入力を求められます。
  * `ca-pub-...` IDの入力を求められます。

### ステップ5: サイトマップの生成 (main\_04)

公開サイト用の `sitemap.xml` を生成します。

```bash
%run main_04_generate_sitemap.py
```

### ステップ6: GitHubへの初回Push

`docs/` フォルダと、レポート、スクリプトの変更をGitHubにPushします。

```bash
# (Git Push用スクリプトを実行し、GitHub Pagesで /docs フォルダを公開設定)
```

### ステップ7: 改善サイクルの実行 (main\_02)

サイトのコンテンツを（例: 3記事ずつ）循環的に追加・改善します。

```bash
%run main_02_improvement_cycle.py
```

  * AIが「戦略的バランス」に基づき、記事が少ないセクション（例: `insights/`）を選定します。
  * `docs/insights/` に3件の**新規記事**が生成されます。
  * `docs/insights/index.html` が**自動更新**され、新規記事への内部リンクが追加されます。
  * `output_reports/planned_articles.md` が更新されます。

### ステップ8: 改善のPush

ステップ7の変更（`docs/` と `output_reports/`）を `git push` して、公開サイトに反映させます。

-----

## ディレクトリ構造

```
MySiteGen-Agent/
│
├── main_01_initial_build.py      # (実行) 1. 初回構築エージェント
├── main_02_improvement_cycle.py  # (実行) 2. 改善・記事追加エージェント
├── main_03_inject_tags.py        # (実行) 3. GTM/AdSenseタグ挿入
├── main_04_generate_sitemap.py   # (実行) 4. sitemap.xml 生成
│
├── config/
│   └── opinion.txt               # (入力) 1. あなたの「理念」
│
├── agents/
│   ├── agent_01_identity.py      # (AI頭脳) アイデンティティ生成 (法人/個人)
│   ├── agent_02_strategy.py      # (AI頭脳) サイトマップ・戦略生成 (法人/個人)
│   ├── agent_03_generation.py    # (AI頭脳) HTML生成 (フッター切替, GTM/AdSense)
│   └── agent_04_improvement.py   # (AI頭脳) サイト分析, 優先度決定, 記事企画
│
├── utils/
│   ├── analysis_utils.py         # (補助) ダミーデータ生成
│   └── file_utils.py             # (補助) MD/計画ファイルの読込/保存
│
├── output_reports/
│   ├── 01_identity.md            # (出力) AIが生成したアイデンティティ
│   ├── 02_sitemap.md             # (出力) AIが生成したサイトマップ
│   ├── 03_content_strategy.md    # (出力) AIが生成した戦略
│   ├── 04_target_pages_list.json # (出力) AIが生成したハブリスト
│   └── planned_articles.md       # (出力) サイト全体の最終計画書 (随時更新)
│
├── docs/
│   ├── index.html                # (出力) 公開サイト本体 (旧 output_website)
│   ├── vision/
│   │   └── index.html
│   │   └── article-1.html ...
│   ├── solutions/
│   │   └── ...
│   ├── robots.txt                # (出力) SEO用
│   └── sitemap.xml               # (出力) SEO用
│
├── notebooks/
│   ├── 1_Initial_Build.ipynb     # (Jupyter) main_01 の実行ノート
│   └── 2_Improvement_Cycle.ipynb # (Jupyter) main_02 の実行ノート
│
├── requirements.txt              # 依存ライブラリ
└── README.md                     # (このファイル)
```

## ライセンス情報

このプロジェクトは [MITライセンス](https://www.google.com/search?q=LICENSE) の下で公開されています。
（`LICENSE` ファイルをリポジトリのルートに配置してください）

## 謝辞

  * Google AI (Gemini API)
  * Pythonコミュニティ
