import json
from google import genai
# from IPython.display import display, Markdown # .pyファイルからは削除

# ⬇️ [修正] 'SITE_TYPE' ( 'corporate' or 'personal' ) を引数として受け取る
def generate_corporate_identity(client, raw_input, SITE_TYPE='corporate'):
    """
    提供されたRAWテキストとSITE_TYPEに基づき、
    「法人格」または「パーソナル・ブランド」をGeminiに生成させる。
    """
    
    # ⬇️ [修正] サイトタイプに応じてAIへの指示（プロンプト）を切り替える
    if SITE_TYPE == 'corporate':
        print("... 🤖 AI (Flash) が「法人格」を形成しています ...")
        prompt_title = "法人格フレームワーク"
        prompt_instructions = """
        ### 抽出・生成すべき法人格フレームワーク

        **パーパス (存在意義):** [最も根源的な存在理由と社会への貢献を簡潔に定義]
        **ミッション (現在の使命・行動指針):** [パーパスを達成するために、現在具体的に行うべき使命を定義]
        **ビジョン (目指す未来像):** [ミッションが達成された先に実現したい、具体的で鼓舞される未来の姿を定義]
        **法人格/トーン:** [この法人が対外的に持つべき個性、ブランドイメージ、コミュニケーションのトーンを定義]
        """
        prompt_role = "あなたは企業のアイデンティティ構築の専門家です。"
        
    else: # 'personal' の場合
        print("... 🤖 AI (Flash) が「パーソナル・ブランド」を形成しています ...")
        prompt_title = "パーソナル・ブランドフレームワーク"
        prompt_instructions = """
        ### 抽出・生成すべきパーソナル・ブランドフレームワーク

        **コンセプト (主題):** [このポートフォリオサイトの核となる主題を簡潔に定義]
        **ミッション (個人の使命):** [この主題を探求する上での、個人の使命や行動指針を定義]
        **専門分野 (Skills):** [哲学を実現するための具体的な専門分野（例: データサイエンス, AI倫理）を列挙]
        **トーン (個性のトーン):** [この個人が持つべき個性、コミュニケーションのトーンを定義（例: 専門的、論理的、未来志向）]
        """
        prompt_role = "あなたは個人のブランディング専門家です。"
        
    # ⬇️ [修正] 共通のプロンプトテンプレート
    prompt = f"""
    {prompt_role}
    以下の「核となる哲学とビジョン」を総合的に分析し、{prompt_title} を定義してください。

    【重要】分析以外の言葉や、対話的な応答、説明は一切せず、要求されたフォーマットの抽出結果のみを Markdown で出力してください。

    ### 核となる哲学とビジョン
    {raw_input}

    ---
    {prompt_instructions}
    """

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        print(f"✅ AIによる定義が完了しました。")
        return response.text.strip()
    except Exception as e:
        print(f"❌ 定義の形成中にエラーが発生しました: {e}")
        return f"❌ 定義の形成中にエラーが発生しました: {e}"
