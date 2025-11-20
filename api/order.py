from http.server import BaseHTTPRequestHandler
import json
import os
import requests

class Handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def do_POST(self):
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            order_data = json.loads(post_data)
            
            success = self.send_admin_notification(order_data)
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            if success:
                response = {'success': True, 'message': 'Order processed successfully'}
            else:
                response = {'success': False, 'message': 'Failed to send notification'}
                
            self.wfile.write(json.dumps(response).encode('utf-8'))
            
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            response = {'success': False, 'error': str(e)}
            self.wfile.write(json.dumps(response).encode('utf-8'))
    
    def send_admin_notification(self, order_data):
        try:
            bot_token = os.environ.get('BOT_TOKEN')
            admin_chat_id = os.environ.get('ADMIN_CHAT_ID')
            
            if not bot_token or not admin_chat_id:
                return False
            
            clean_phone = order_data['phone'].replace(' ', '').replace('(', '').replace(')', '').replace('-', '')
            telegram_url = f"https://t.me/{clean_phone}"
            
            items_text = "\n".join([
                f"• {item['name']} - {item['quantity']} шт. × {item['price']} ₽ = {item['total']} ₽" 
                for item in order_data['items']
            ])
            
            message = f"""🎉 <b>НОВЫЙ ЗАКАЗ!</b>

👤 <b>Информация о клиенте:</b>
🆔 ID: <code>{order_data['user']['id']}</code>
📛 Имя: {order_data['user']['first_name']}
👤 Юзернейм: @{order_data['user']['username']}
📞 Телефон: <code>{clean_phone}</code>

🛍️ <b>Состав заказа:</b>
{items_text}

💵 <b>Итого к оплате:</b> {order_data['total']} ₽

📋 <b>Комментарий:</b> {order_data['comment'] or 'Нет комментария'}

🕐 <b>Время заказа:</b> {order_data['time']}

💬 <a href="{telegram_url}">Написать покупателю</a>"""
            
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            payload = {
                'chat_id': admin_chat_id,
                'text': message,
                'parse_mode': 'HTML',
                'disable_web_page_preview': False
            }
            
            response = requests.post(url, json=payload, timeout=10)
            return response.status_code == 200
            
        except Exception as e:
            return False
