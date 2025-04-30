# lambda/index.py
import json
import os
import urllib.request
from botocore.exceptions import ClientError

# FastAPIサーバーのエンドポイントURL
FASTAPI_ENDPOINT = os.environ.get("FASTAPI_ENDPOINT", "https://b549-34-125-193-13.ngrok-free.app")

def lambda_handler(event, context):
    try:
        print("Received event:", json.dumps(event))
        
        # Cognitoで認証されたユーザー情報を取得
        user_info = None
        if 'requestContext' in event and 'authorizer' in event['requestContext']:
            user_info = event['requestContext']['authorizer']['claims']
            print(f"Authenticated user: {user_info.get('email') or user_info.get('cognito:username')}")
        
        # リクエストボディの解析
        body = json.loads(event['body'])
        message = body['message']
        conversation_history = body.get('conversationHistory', [])
        
        print("Processing message:", message)
        
        # 会話履歴を使用してプロンプトを作成
        prompt = ""
        for msg in conversation_history:
            role = msg["role"]
            content = msg["content"]
            if role == "user":
                prompt += f"ユーザー: {content}\n"
            elif role == "assistant":
                prompt += f"アシスタント: {content}\n"
        
        # 最新のユーザーメッセージを追加
        prompt += f"ユーザー: {message}\nアシスタント: "
        
        print("Sending prompt to FastAPI server:", prompt)
        
        # /generateエンドポイント用のリクエストデータを準備
        request_data = {
            "prompt": prompt,
            "max_new_tokens": 512,
            "do_sample": True,
            "temperature": 0.7,
            "top_p": 0.9
        }
        
        # リクエストの設定
        req = urllib.request.Request(
            f"{FASTAPI_ENDPOINT}/generate",
            data=json.dumps(request_data).encode('utf-8'),
            headers={
                'Content-Type': 'application/json'
            }
        )
        
        # FastAPIサーバーにリクエストを送信
        with urllib.request.urlopen(req) as response:
            response_body = json.loads(response.read())
            print("FastAPI response:", json.dumps(response_body))
            
            # アシスタントの応答を取得
            assistant_response = response_body.get('generated_text', '')
            
            if not assistant_response:
                raise Exception("No response content from the model")
        
        # 会話履歴にメッセージを追加
        messages = conversation_history.copy()
        messages.append({
            "role": "user",
            "content": message
        })
        messages.append({
            "role": "assistant",
            "content": assistant_response
        })
        
        # 成功レスポンスの返却
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
                "Access-Control-Allow-Methods": "OPTIONS,POST"
            },
            "body": json.dumps({
                "success": True,
                "response": assistant_response,
                "conversationHistory": messages
            })
        }
        
    except Exception as error:
        print("Error:", str(error))
        
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
                "Access-Control-Allow-Methods": "OPTIONS,POST"
            },
            "body": json.dumps({
                "success": False,
                "error": str(error)
            })
        }
