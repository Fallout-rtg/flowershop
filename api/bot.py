from http.server import BaseHTTPRequestHandler
import json
import os
import requests

class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            update = json.loads(post_data)
            
            if 'message' in update:
                chat_id = update['message']['chat']['id']
                text = update['message'].get('text', '')
                
                if text.startswith('/start'):
                    bot_token = os.environ.get('BOT_TOKEN')
                    vercel_url = os.environ.get('VERCEL_URL')
                    
                    response_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
                    markup = {
                        "inline_keyboard": [[
                            {
                                "text": "🌸 Открыть магазин цветов",
                                "web_app": {"url": f"https://{vercel_url}/"}
                            }
                        ]]
                    }
                    payload = {
                        'chat_id': chat_id,
                        'text': '🌸 Добро пожаловать в магазин элитных цветов!\n\nНажмите на кнопку ниже, чтобы открыть каталог и сделать заказ.',
                        'reply_markup': json.dumps(markup)
                    }
                    requests.post(response_url, json=payload)
                    
                    # Уведомление админу о новом пользователе
                    admin_chat_id = os.environ.get('ADMIN_CHAT_ID')
                    if admin_chat_id:
                        user = update['message']['from']
                        admin_message = f"👤 Новый пользователь запустил бота!\nID: {user['id']}\nИмя: {user.get('first_name', 'Неизвестно')}\nЮзернейм: @{user.get('username', 'Неизвестно')}"
                        requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", 
                                    json={'chat_id': admin_chat_id, 'text': admin_message})
            
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write('OK'.encode('utf-8'))
            
        except Exception as e:
            print(f"Error: {e}")
            self.send_response(200)
            self.end_headers()

    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write('Bot is running!'.encode('utf-8'))
