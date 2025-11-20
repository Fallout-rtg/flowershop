from http.server import BaseHTTPRequestHandler
import json
import requests

# Конфигурация (эти значения вы установите в настройках Vercel)
BOT_TOKEN = "@@@BOT_TOKEN@@@"  # Будет заменен на секрет
VERCEL_URL = "@@@VERCEL_URL@@@"  # Будет заменен на секрет

class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        update = json.loads(post_data)

        # Обрабатываем сообщения от Telegram
        if 'message' in update:
            chat_id = update['message']['chat']['id']
            text = update['message'].get('text', '')

            if text == '/start':
                # Отправляем сообщение с кнопкой, открывающей Mini App
                response_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
                markup = {
                    "inline_keyboard": [[
                        {
                            "text": "🌸 Открыть магазин",
                            "web_app": {"url": f"https://{VERCEL_URL}/"}  # Ссылка на ваше Mini App
                        }
                    ]]
                }
                payload = {
                    'chat_id': chat_id,
                    'text': 'Добро пожаловать в магазин цветов! Нажмите на кнопку ниже, чтобы открыть каталог.',
                    'reply_markup': json.dumps(markup)
                }
                requests.post(response_url, json=payload)

        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write('OK'.encode('utf-8'))
        return

    def do_GET(self):
        # Простой ответ для проверки работоспособности
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write('Бот жив!'.encode('utf-8'))
        return
