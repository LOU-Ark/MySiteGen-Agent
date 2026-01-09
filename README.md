# MySiteGen-Agent

## 概要

`MySiteGen-Agent`は、Google Gemini APIを活用したPythonベースのAIエージェントシステムです。単一の「理念（`opinion.txt`）」ファイルに基づき、**「法人サイト」または「個人ポートフォリオ」**を選択的に自動構築し、継続的にコンテンツを改善・拡張します。

このシステムは、単なるHTMLジェネレーターではなく、**Webサイトの完全なライフサイクル（戦略策定 → 初回構築 → 分析 → 改善）**を自動化するよう設計されています。

-----

## ✨ 主な機能

### コア機能 (main_*.py)

| スクリプト | 概要 |
|:---|:---|
| `main_01_initial_build.py` | 理念ファイルからサイトの骨格（全ハブページ）を一括生成 |
| `main_02_improvement_cycle.py` | AIが既存サイトを分析し、戦略的に記事を追加・改善 |
| `main_03_inject_tags.py` | GTM/AdSenseタグを全HTMLに一括挿入 |
| `main_04_generate_sitemap.py` | SEO用の `sitemap.xml` を自動生成 |

### 運用ツール (tools/)

| ツール | 概要 |
|:---|:---|
| `add_article.py` | **全自動で記事を追加**。原案を入力するだけでタイトル・目的をAIが生成し、HTMLを作成して一覧ページも自動更新。|
| `update_listings.py` | 各セクション（projects, insights等）の一覧ページを `planned_articles.md` に基づき再生成。 |
| `check_links.py` | サイト内のリンク切れを検出。 |
| `fix_links.py` | 検出されたリンク切れを自動修復。 |

### 主要な自動化機能

*   **ヘッダー・フッターの自動継承**: トップページから共通パーツを抽出し、新記事に自動適用。サイト全体のデザイン一貫性を維持。
*   **GTM ID の自動抽出**: `docs/index.html` から GTM ID を自動検出し、新規ページに挿入。
*   **グローバル連番**: サイト全体で重複しない記事番号（例: 37, 38...）を自動付与。
*   **作成日の自動挿入**: 記事タイトル下に「公開日: YYYY年MM月DD日」を自動挿入。

-----

## 🚀 クイックスタート

### 1. セットアップ

```bash
git clone https://github.com/LOU-Ark/MySiteGen-Agent.git
cd MySiteGen-Agent
pip install -r requirements.txt
```

### 2. 環境変数の設定

`.env` ファイルを作成し、以下を記述します。

```
GEMINI_API_KEY=your_api_key_here
```

### 3. 記事の追加（推奨ワークフロー）

```bash
python tools/add_article.py
```

対話形式でプロジェクトを選択し、原案を入力するだけで：
1.  AIがタイトルと目的を生成
2.  HTMLファイルを作成
3.  計画ファイル (`planned_articles.md`) に登録
4.  一覧ページ (`projects/index.html` 等) を自動更新

-----

## 📂 ディレクトリ構造

```
MySiteGen-Agent/
├── agents/             # AIエージェントのコアロジック
├── config/             # 設定ファイル (settings.py, opinion.txt)
├── tools/              # 運用・保守ツール ★ NEW
│   ├── add_article.py
│   ├── update_listings.py
│   ├── check_links.py
│   └── fix_links.py
├── utils/              # 共通ユーティリティ
├── projects/           # 生成ターゲットプロジェクト (Git管理対象外)
│   └── sophia-echoes/
├── main_*.py           # 各種実行スクリプト
├── requirements.txt
└── README.md
```

-----

## ライセンス

このプロジェクトは [MIT License](LICENSE) の下で公開されています。

## 謝辞

*   Google AI (Gemini API)
*   Pythonコミュニティ
