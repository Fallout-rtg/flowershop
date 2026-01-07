# api/AI.py
from http.server import BaseHTTPRequestHandler
import json
import os
import sys
import requests

sys.path.append(os.path.dirname(__file__))

try:
    from supabase_client import supabase
    from health import log_error
except ImportError as e:
    print(f"Import error: {e}")

OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY', '')
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "deepseek/deepseek-r1-0528:free"

def get_ai_response(prompt, context=""):
    if not OPENROUTER_API_KEY:
        return {"error": "OpenRouter API ключ не настроен"}
    
    system_prompt = f"Вы — ИИ-ассистент администратора магазина 'АртФлора'. Вы говорите напрямую с владельцем. Будьте кратки, профессиональны и помогайте в управлении."

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://artflora.vercel.app",
        "X-Title": "ArtFlora Flower Shop"
    }

    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 1000
    }

    try:
        response = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            if 'choices' in result and len(result['choices']) > 0:
                return {
                    "success": True,
                    "response": result['choices'][0]['message']['content'].strip()
                }
            else:
                return {"error": "Пустой ответ от AI"}
        else:
            return {"error": f"Ошибка API: {response.status_code}", "details": response.text}
    
    except requests.exceptions.Timeout:
        return {"error": "Таймаут запроса к AI"}
    except Exception as e:
        return {"error": f"Ошибка: {str(e)}"}

class Handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Telegram-Id')
        self.end_headers()
    
    def do_GET(self):
        try:
            if self.path == '/api/ai/status' or self.path == '/api/ai/status/':
                status_data = {
                    "status": "online" if OPENROUTER_API_KEY else "offline",
                    "model": MODEL,
                    "service": "OpenRouter + DeepSeek R1"
                }
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                
                response_json = json.dumps(status_data, ensure_ascii=False).encode('utf-8')
                self.wfile.write(response_json)
            else:
                self.send_response(404)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                response = {'error': 'Not found'}
                response_json = json.dumps(response, ensure_ascii=False).encode('utf-8')
                self.wfile.write(response_json)
                
        except Exception as e:
            error_msg = str(e).encode('utf-8').decode('utf-8', 'ignore')
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            response = {'error': error_msg}
            response_json = json.dumps(response, ensure_ascii=False).encode('utf-8')
            self.wfile.write(response_json)
    
    def do_POST(self):
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length).decode('utf-8', errors='ignore')
            data = json.loads(post_data)
            
            user_message = data.get('message', '').strip()
            context = data.get('context', 'Цветочный магазин "АртФлора"')
            
            if not user_message:
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                response = {'error': 'Пустое сообщение'}
                response_json = json.dumps(response, ensure_ascii=False).encode('utf-8')
                self.wfile.write(response_json)
                return
            
            # Получаем ответ от AI
            ai_response = get_ai_response(user_message, context)
            
            if "error" in ai_response:
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                response_json = json.dumps(ai_response, ensure_ascii=False).encode('utf-8')
                self.wfile.write(response_json)
            else:
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                response_json = json.dumps(ai_response, ensure_ascii=False).encode('utf-8')
                self.wfile.write(response_json)
            
        except json.JSONDecodeError:
            self.send_response(400)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            response = {'error': 'Invalid JSON'}
            response_json = json.dumps(response, ensure_ascii=False).encode('utf-8')
            self.wfile.write(response_json)
            
        except Exception as e:
            error_msg = str(e).encode('utf-8').decode('utf-8', 'ignore')
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            response = {'error': error_msg}
            response_json = json.dumps(response, ensure_ascii=False).encode('utf-8')
            self.wfile.write(response_json)
