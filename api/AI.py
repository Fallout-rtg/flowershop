# api/AI.py
from http.server import BaseHTTPRequestHandler
import json
import os
import sys
import requests
import logging
import traceback

sys.path.append(os.path.dirname(__file__))

# Настройка логирования
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

try:
    from supabase_client import supabase
    from health import log_error
    logger.info("✅ Импорт supabase_client и health успешен")
except ImportError as e:
    logger.error(f"❌ Ошибка импорта: {e}")
    print(f"Import error: {e}")

OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY', '')
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "deepseek/deepseek-r1-0528:free"

logger.info(f"🔑 OPENROUTER_API_KEY: {'установлен' if OPENROUTER_API_KEY else 'НЕ УСТАНОВЛЕН'}")
logger.info(f"🌐 OPENROUTER_URL: {OPENROUTER_URL}")
logger.info(f"🤖 MODEL: {MODEL}")

def get_ai_response(prompt, context=""):
    logger.info(f"📨 Получен запрос к AI. Prompt: {prompt[:50]}...")
    
    if not OPENROUTER_API_KEY:
        logger.error("❌ OPENROUTER_API_KEY не настроен")
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

    logger.info(f"📤 Отправка запроса к OpenRouter API")
    logger.debug(f"Headers: {headers}")
    logger.debug(f"Payload: {json.dumps(payload, ensure_ascii=False)}")

    try:
        response = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=30)
        logger.info(f"📥 Получен ответ от OpenRouter. Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            logger.debug(f"Response JSON: {json.dumps(result, ensure_ascii=False)[:200]}...")
            
            if 'choices' in result and len(result['choices']) > 0:
                ai_response = result['choices'][0]['message']['content'].strip()
                logger.info(f"✅ Успешный ответ от AI. Длина: {len(ai_response)} символов")
                return {
                    "success": True,
                    "response": ai_response
                }
            else:
                logger.warning("⚠️ Пустой ответ от AI (нет choices)")
                return {"error": "Пустой ответ от AI", "details": result}
        else:
            logger.error(f"❌ Ошибка API: {response.status_code}. Response: {response.text[:200]}")
            return {
                "error": f"Ошибка API: {response.status_code}", 
                "details": response.text[:500]
            }
    
    except requests.exceptions.Timeout:
        logger.error("⏰ Таймаут запроса к AI")
        return {"error": "Таймаут запроса к AI"}
    except requests.exceptions.ConnectionError as e:
        logger.error(f"🔌 Ошибка подключения: {e}")
        return {"error": f"Ошибка подключения: {str(e)}"}
    except Exception as e:
        logger.error(f"💥 Неожиданная ошибка: {str(e)}")
        logger.error(traceback.format_exc())
        return {"error": f"Ошибка: {str(e)}"}

class handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Переопределяем стандартное логирование
        logger.info(f"{self.address_string()} - {format % args}")
    
    def do_OPTIONS(self):
        logger.info(f"🔄 OPTIONS запрос на {self.path}")
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Telegram-Id')
        self.end_headers()
    
    def do_GET(self):
        logger.info(f"📄 GET запрос на {self.path}")
        try:
            if self.path == '/api/ai/status' or self.path == '/api/ai/status/':
                status_data = {
                    "status": "online" if OPENROUTER_API_KEY else "offline",
                    "model": MODEL,
                    "service": "OpenRouter + DeepSeek R1",
                    "api_key_set": bool(OPENROUTER_API_KEY)
                }
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                
                response_json = json.dumps(status_data, ensure_ascii=False).encode('utf-8')
                self.wfile.write(response_json)
                logger.info(f"✅ Статус отправлен: {status_data}")
            else:
                logger.warning(f"❌ Неизвестный GET путь: {self.path}")
                self.send_response(404)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                response = {'error': 'Not found'}
                response_json = json.dumps(response, ensure_ascii=False).encode('utf-8')
                self.wfile.write(response_json)
                
        except Exception as e:
            error_msg = str(e)
            logger.error(f"💥 Ошибка в GET обработчике: {error_msg}")
            logger.error(traceback.format_exc())
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            response = {'error': error_msg}
            response_json = json.dumps(response, ensure_ascii=False).encode('utf-8')
            self.wfile.write(response_json)
    
    def do_POST(self):
        logger.info(f"📨 POST запрос на {self.path}")
        logger.info(f"Заголовки: {dict(self.headers)}")
        
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            logger.info(f"Длина контента: {content_length}")
            
            if content_length == 0:
                logger.error("❌ Пустой запрос (content-length = 0)")
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                response = {'error': 'Пустой запрос'}
                response_json = json.dumps(response, ensure_ascii=False).encode('utf-8')
                self.wfile.write(response_json)
                return
                
            post_data = self.rfile.read(content_length).decode('utf-8', errors='ignore')
            logger.info(f"📝 Получены данные: {post_data[:200]}...")
            
            data = json.loads(post_data)
            user_message = data.get('message', '').strip()
            context = data.get('context', 'Цветочный магазин "АртФлора"')
            
            logger.info(f"💬 Сообщение пользователя: {user_message[:100]}...")
            logger.info(f"📋 Контекст: {context}")
            
            if not user_message:
                logger.warning("⚠️ Пустое сообщение от пользователя")
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                response = {'error': 'Пустое сообщение'}
                response_json = json.dumps(response, ensure_ascii=False).encode('utf-8')
                self.wfile.write(response_json)
                return
            
            # Получаем ответ от AI
            logger.info("🔄 Вызов get_ai_response...")
            ai_response = get_ai_response(user_message, context)
            logger.info(f"🤖 Ответ от get_ai_response: {ai_response.get('error', 'Успех')}")
            
            # Форматируем ответ для клиента
            if "error" in ai_response:
                response_data = {
                    "success": False,
                    "error": ai_response["error"],
                    "details": ai_response.get("details", "")
                }
                logger.warning(f"⚠️ AI вернул ошибку: {ai_response['error']}")
            else:
                response_data = {
                    "success": True,
                    "response": ai_response.get("response", "")
                }
                logger.info(f"✅ Успешный ответ AI. Длина: {len(ai_response.get('response', ''))}")
            
            # Отправляем ответ клиенту
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            response_json = json.dumps(response_data, ensure_ascii=False).encode('utf-8')
            self.wfile.write(response_json)
            logger.info("📤 Ответ отправлен клиенту")
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ Ошибка декодирования JSON: {e}")
            logger.error(f"Полученные данные: {post_data[:200] if 'post_data' in locals() else 'Нет данных'}")
            self.send_response(400)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            response = {'error': 'Invalid JSON', 'details': str(e)}
            response_json = json.dumps(response, ensure_ascii=False).encode('utf-8')
            self.wfile.write(response_json)
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"💥 Неожиданная ошибка в POST: {error_msg}")
            logger.error(traceback.format_exc())
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            response = {'error': error_msg}
            response_json = json.dumps(response, ensure_ascii=False).encode('utf-8')
            self.wfile.write(response_json)
