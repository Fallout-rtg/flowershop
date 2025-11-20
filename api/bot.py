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
            
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write('OK'.encode('utf-8'))
            
        except Exception as e:
            self.send_response(200)
            self.end_headers()

    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        photos = {
            'roses': 'https://t.me/flowerShop_my/2',
            'tulips': 'https://t.me/flowerShop_my/3',
            'wedding': 'https://t.me/flowerShop_my/4',
            'orchid': 'https://t.me/flowerShop_my/5',
            'romantic': 'https://t.me/flowerShop_my/6',
            'rainbow': 'https://t.me/flowerShop_my/7'
        }
        
        response = {'photos': photos}
        self.wfile.write(json.dumps(response).encode('utf-8'))
