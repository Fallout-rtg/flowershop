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
            
            # Обрабатываем сообщения от Telegram
            if 'message' in update:
                chat_id = update['message']['chat']['id']
                text = update['message'].get('text', '')
                
                if text.startswith('/start'):
                    # Отправляем сообщение с кнопкой, открывающей Mini App
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
                        'text': '🌸 Добро пожаловать в магазин цветов!\n\nНажмите на кнопку ниже, чтобы открыть каталог и сделать заказ.',
                        'reply_markup': json.dumps(markup)
                    }
                    requests.post(response_url, json=payload)
            
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
