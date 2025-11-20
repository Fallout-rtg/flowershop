from http.server import BaseHTTPRequestHandler
import json
import os
import requests

photo_cache = {}
CHANNEL_ID = -1003493982951

class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            update = json.loads(post_data)
            
            if 'channel_post' in update:
                channel_post = update['channel_post']
                chat_id = channel_post['chat']['id']
                
                if chat_id == CHANNEL_ID:
                    self.process_channel_post(channel_post)
            
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

    def process_channel_post(self, channel_post):
        if 'photo' in channel_post:
            photos = channel_post['photo']
            best_photo = photos[-1]
            file_id = best_photo['file_id']
            
            file_url = self.get_file_url(file_id)
            if file_url:
                caption = channel_post.get('caption', '')
                product_type = self.detect_product_type(caption)
                
                if product_type:
                    photo_cache[product_type] = file_url

    def get_file_url(self, file_id):
        try:
            bot_token = os.environ.get('BOT_TOKEN')
            response = requests.get(
                f'https://api.telegram.org/bot{bot_token}/getFile?file_id={file_id}'
            )
            file_data = response.json()
            
            if file_data['ok']:
                file_path = file_data['result']['file_path']
                return f'https://api.telegram.org/file/bot{bot_token}/{file_path}'
        except Exception:
            pass
        return None

    def detect_product_type(self, caption):
        caption_lower = caption.lower()
        if 'роз' in caption_lower:
            return 'roses'
        elif 'тюльпан' in caption_lower:
            return 'tulips' 
        elif 'свадеб' in caption_lower:
            return 'wedding'
        elif 'орхиде' in caption_lower:
            return 'orchid'
        elif 'романт' in caption_lower:
            return 'romantic'
        elif 'радуга' in caption_lower:
            return 'rainbow'
        return None

    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        default_photos = {
            'roses': 'https://t.me/flowerShop_my/2',
            'tulips': 'https://t.me/flowerShop_my/3',
            'wedding': 'https://t.me/flowerShop_my/4',
            'orchid': 'https://t.me/flowerShop_my/5',
            'romantic': 'https://t.me/flowerShop_my/6',
            'rainbow': 'https://t.me/flowerShop_my/7'
        }
        
        merged_photos = {**default_photos, **photo_cache}
        response = {'photos': merged_photos}
        self.wfile.write(json.dumps(response).encode('utf-8'))
