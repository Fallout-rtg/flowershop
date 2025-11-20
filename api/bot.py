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
                
                bot_token = os.environ.get('BOT_TOKEN')
                vercel_url = os.environ.get('VERCEL_URL')
                
                if text.startswith('/start'):
                    markup = {
                        "inline_keyboard": [
                            [{
                                "text": "🌸 Открыть магазин цветов", 
                                "web_app": {"url": f"https://{vercel_url}/"}
                            }],
                            [
                                {"text": "📞 Поддержка", "url": "https://t.me/flower_support"},
                                {"text": "ℹ️ О магазине", "callback_data": "about"}
                            ]
                        ]
                    }
                    
                    message = """🌸 *Добро пожаловать в магазин элитных цветов!*

✨ У нас вы найдете:
• Свежие цветы от проверенных поставщиков
• Быструю доставку по Ярославлю
• Индивидуальный подход к каждому заказу

Нажмите на кнопку ниже, чтобы открыть каталог и сделать заказ!"""
                    
                    response_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
                    payload = {
                        'chat_id': chat_id,
                        'text': message,
                        'parse_mode': 'Markdown',
                        'reply_markup': json.dumps(markup)
                    }
                    requests.post(response_url, json=payload)
                
                elif text.startswith('/help'):
                    message = """🛠 *Помощь по боту*

*Основные команды:*
/start - начать работу с ботом
/help - получить помощь

*Как сделать заказ:*
1. Нажмите кнопку «Открыть магазин цветов»
2. Выберите понравившиеся букеты
3. Оформите заказ в корзине
4. Укажите ваш телефон для связи

*Доставка:* 
🏙️ По Ярославлю - бесплатно
⏱ В течение 2-х часов"""
                    
                    response_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
                    payload = {
                        'chat_id': chat_id,
                        'text': message,
                        'parse_mode': 'Markdown'
                    }
                    requests.post(response_url, json=payload)
            
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'OK')
            
        except Exception as e:
            print(f"Error in bot handler: {e}")
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'OK')

    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b'Bot is running')
