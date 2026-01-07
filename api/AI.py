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

# Конфигурация OpenRouter
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY', '')
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "deepseek/deepseek-r1-0528:free"

def get_ai_response(prompt, context=""):
    """
    Отправляет запрос к DeepSeek через OpenRouter
    """
    if not OPENROUTER_API_KEY:
        return {"error": "OpenRouter API ключ не настроен"}
    
    # Системный промт с контекстом магазина цветов
    system_prompt = f"""You are an AI assistant for a flower shop called "АртФлора". 
You help with questions about flowers, bouquets, orders, delivery, and shop management.
You should always respond in Russian language.
Shop context: {context}

Instructions:
1. Always respond in Russian
2. Be helpful, friendly and professional
3. If asked about specific flowers, provide accurate information
4. For order-related questions, guide users to proper procedures
5. For administrative questions, provide guidance on using the admin panel
6. Keep responses concise but informative
7. If you don't know something, admit it politely"""

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://artflora.vercel.app",
        "X-Title": "АртФлора Цветочный Магазин"
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
    def _send_response(self, status_code, data):
        """Универсальный метод отправки ответа"""
        self.send_response(status_code)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        # Кодируем данные в UTF-8
        response_data = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.wfile.write(response_data)
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Telegram-Id')
        self.end_headers()
    
    def do_GET(self):
        try:
            path = self.path.rstrip('/')
            if path == '/api/ai/status':
                status_data = {
                    "status": "online" if OPENROUTER_API_KEY else "offline",
                    "model": MODEL,
                    "service": "OpenRouter + DeepSeek R1"
                }
                self._send_response(200, status_data)
            else:
                self._send_response(404, {'error': 'Not found'})
                
        except Exception as e:
            log_error("AI_GET", e, self.headers.get('Telegram-Id', ''), f"Path: {self.path}")
            self._send_response(500, {'error': str(e)})
    
    def do_POST(self):
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length).decode('utf-8')
            data = json.loads(post_data)
            
            user_message = data.get('message', '').strip()
            context = data.get('context', 'Цветочный магазин "АртФлора"')
            
            if not user_message:
                self._send_response(400, {'error': 'Пустое сообщение'})
                return
            
            # Получаем ответ от AI
            ai_response = get_ai_response(user_message, context)
            
            if "error" in ai_response:
                self._send_response(500, ai_response)
            else:
                self._send_response(200, ai_response)
            
        except json.JSONDecodeError:
            self._send_response(400, {'error': 'Invalid JSON'})
        except Exception as e:
            error_data = str(e)
            # Безопасная логировка для избежания проблем с кодировкой
            try:
                log_error("AI_POST", str(e), self.headers.get('Telegram-Id', ''), "Error occurred")
            except:
                pass
            self._send_response(500, {'error': 'Internal server error'})
