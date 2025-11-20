from http.server import BaseHTTPRequestHandler
import json
import os
import requests
from datetime import datetime

class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            order_data = json.loads(post_data)
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            # Отправляем уведомление админу
            self.send_admin_notification(order_data)
            
            response = {'success': True, 'message': 'Order processed'}
            self.wfile.write(json.dumps(response).encode('utf-8'))
            
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            response = {'success': False, 'error': str(e)}
            self.wfile.write(json.dumps(response).encode('utf-8'))
    
    def send_admin_notification(self, order_data):
        bot_token = os.environ.get('BOT_TOKEN')
        admin_chat_id = os.environ.get('ADMIN_CHAT_ID')
        
        if not bot_token or not admin_chat_id:
            print("BOT_TOKEN or ADMIN_CHAT_ID not set")
            return
        
        items_text = "\n".join([
            f"• {item['name']} - {item['quantity']} шт. × {item['price']} ₽ = {item['total']} ₽" 
            for item in order_data['items']
        ])
        
        message = f"""🛍️ <b>НОВЫЙ ЗАКАЗ!</b>

👤 <b>Информация о клиенте:</b>
ID: {order_data['user']['id']}
Имя: {order_data['user']['first_name']}
Юзернейм: @{order_data['user']['username']}
Телефон: {order_data['phone']}

📦 <b>Состав заказа:</b>
{items_text}

💰 <b>Итого к оплате:</b> {order_data['total']} ₽

📝 <b>Комментарий:</b> {order_data['comment'] or 'Нет комментария'}

⏰ <b>Время заказа:</b> {order_data['time']}"""
        
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            'chat_id': admin_chat_id,
            'text': message,
            'parse_mode': 'HTML'
        }
        
        requests.post(url, json=payload)
