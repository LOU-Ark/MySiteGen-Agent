import os
import re
import json
import pandas as pd
from bs4 import BeautifulSoup
from google import genai
from google.genai import types
try:
    from config.settings import MODEL_NAME_PRO
except ImportError:
    MODEL_NAME_PRO = "gemini-3-flash-preview"

# (analyze_article_structure, generate_article_purpose は変更なし)
def analyze_article_structure(file_path):
    """HTMLファイルを読み込み、タイトル、見出し構造、本文テキストを抽出する。"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            soup = BeautifulSoup(content, 'html.parser')
        page_title = soup.find('title').get_text() if soup.find('title') else os.path.basename(file_path)
        main_content_area = soup.find('main')
        temp_soup = BeautifulSoup(content, 'html.parser')
        for tag in temp_soup.find_all(["script", "style", "nav", "header", "footer"]):
            tag.decompose()
        headings = []
        if main_content_area:
            for tag in main_content_area.find_all(['h1', 'h2', 'h3']):
                headings.append(f"<{tag.name}> {tag.get_text().strip()}")
        clean_text = temp_soup.get_text(separator='\n', strip=True)
        return {
            "page_title": page_title.split('|')[0].strip(),
            "structure": "\n".join(headings),
            "full_text_excerpt": clean_text[:500].replace('\n', ' ').strip() + "..."
        }, None
    except Exception as e:
        return None, f"❌ 解析エラー: {e}"

def generate_article_purpose(client, article_data, identity):
    """記事の構造とテキストを分析し、戦略的目的 (Purpose) を生成する。"""
    if client is None: return "❌ クライアント未設定"
    prompt = f"""
    あなたは、Webサイトのコンテンツ戦略家です。
    以下の「法人の哲学」と「記事の現在の構造・内容」を分析し、**サイト全体の戦略に照らして、この記事が持つべき戦略的目的 (Purpose)** を1文で生成してください。
    【重要】回答は生成された「Purpose」の**文字列のみ**を返してください。
    ### 法人の哲学 (CORPORATE IDENTITY)
    {identity}
    ### 対象記事の現状分析
    - 記事タイトル: {article_data['page_title']}
    - 見出し構造: {article_data['structure']}
    - 本文抜粋: {article_data['full_text_excerpt']}
    生成するPurpose (1文):
    """
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        return response.text.strip()
    except Exception as e:
        return f"❌ AI生成失敗: {e}"

# ⬇️ [修正] AIの「Vision偏愛」を治すため、プロンプトを「戦略的バランス」重視に変更
def select_priority_section_by_data(client, df_all_data, identity, target_pages_list, balance_report):
    """
    AIの「偏愛」を防ぐため、サイトの「記事数バランス」を数値化し、
    AIに最も記事が少ないハブを選定させる。
    """
    if client is None:
        return {'file_name': 'solutions/index.html', 'reason': 'クライアント未設定のため、戦略的基盤であるSOLUTIONSをフォールバックしました。'}
    
    data_markdown = df_all_data.to_markdown()
    
    # 目的リストもプロンプトに含める（参考情報として）
    df_target_pages_data = []
    for p in target_pages_list:
         df_target_pages_data.append({
            "file_name": p.get('file_name'),
            "title": p.get('title'),
            "summary": p.get('summary', p.get('generated_purpose', '')) 
        })
    df_target_pages = pd.DataFrame(df_target_pages_data)

    # --- [修正] 新しい「戦略的バランス」重視のプロンプト ---
    prompt = f"""
    あなたはデータ駆動型のコンテンツ戦略責任者です。以下の情報を分析し、**サイト全体の戦略的バランス**の観点から、次にリソースを投入すべきセクションを1つだけ選定してください。

    ### 貴社の目標と戦略的重み
    1. **戦略的バランスの分析:** 以下の「サイトの戦略的バランス（現状の記事数）」レポートを分析してください。
    2. **選定基準:** 「理念（VISION）」セクションは既に充実している可能性が高いです。**記事数が最も少ない**、または VISION との差が最も大きい**コア戦略セクション**（例: SOLUTIONS, INSIGHTS）を選定してください。
    3. **除外対象:** ユーティリティページ（legal/, contact/）は選定対象から除外してください。

    ### サイトの戦略的バランス（現状の記事数）
    {balance_report}

    ### 法人格
    {identity}

    ### 分析対象ページリスト (参考: 全ページの目的)
    {df_target_pages.to_markdown(index=False)}

    ### パフォーマンスデータ (参考: データは均一)
    {data_markdown}
    ---
    回答は以下のJSON形式のみで出力し、理由には**「なぜそのセクションが戦略的バランスの観点から最適か」**を記述してください。
    {{"file_name": "[選定したファイル名]", "reason": "[選定した論理的根拠を記述]"}}
    """

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )
        parsed_json = json.loads(response.text.strip().replace("```json", "").replace("```", ""))
        if any(p.get('file_name') == parsed_json.get('file_name') for p in target_pages_list):
            return parsed_json
        else:
            # [修正] フォールバック先を vision ではなく solutions に変更
            return {'file_name': 'solutions/index.html', 'reason': 'AIの選定結果が不適切なため、次に重要なSOLUTIONSをフォールバックしました。'}
    except Exception as e:
        print(f"❌ AI選定エラー: {e}")
        return {'file_name': 'solutions/index.html', 'reason': 'API接続エラーまたはJSONパース失敗のため、SOLUTIONSをフォールバックします。'}

# ⬇️ [修正] KeyError: 'generated_purpose' を防ぐため、両方のキーに対応
def generate_priority_article_titles(client, section_info, identity, count, start_number):
    """
    最優先セクションの目的を満たす、具体的な記事タイトル、要約、スラッグを企画する。
    """
    if client is None: return "❌ Geminiクライアントが初期化されていません。", []
    
    # ⬅️ [修正] 'generated_purpose' と 'summary' の両方に対応
    section_purpose = section_info.get('summary', section_info.get('generated_purpose', ''))
    
    prompt = f"""
    あなたは、SEOとデータサイエンスの専門家です。
    以下の「法人のアイデンティティ」と「最優先セクションの戦略的目的」に基づき、その目的に最も貢献する**具体的かつ専門性の高い記事タイトル、要約、SEOスラッグ（ファイル名）**を {count} 件生成してください。

    ### CRITICAL要件
    1. **スラッグの形式:** 英語小文字、ハイフン区切り、`.html` 拡張子で、**記事の内容を正確に反映**してください。
    2. **連番の開始点:** 生成する {count} 件の連番は、**既存のコンテンツを考慮し {start_number} から開始**してください。（例: ...-{start_number}.html, ...-{start_number + 1}.html, ...）
    3. **JSON出力:** 回答はJSON配列形式のみで出力してください。スラッグにはこの連番を含めてください。

    ### 最優先セクションの戦略的目的
    {section_info['title']} ({section_info['file_name']})
    目的: {section_purpose} 

    ### 法人格
    {identity}
    ---
    回答は、以下のJSON配列形式のみで出力してください。
    [
      {{"title": "記事タイトル", "summary": "要約", "file_name": "seo-optimized-slug-{start_number}.html"}},
      ... ({count}件分)
    ]
    """

    print(f"📢 AIに {section_info['title']} セクション用の記事 {count} 件の企画を依頼中...")
    try:
        response = client.models.generate_content(
            model=MODEL_NAME_PRO,
            contents=prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )
        parsed_list = json.loads(response.text.strip().replace("```json", "").replace("```", ""))
        print("✅ 記事企画の生成に成功しました。")
        return "", parsed_list
    except Exception as e:
        print(f"❌ APIまたはJSONパースエラー: {e}")
        return str(e), []
