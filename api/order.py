from http.server import BaseHTTPRequestHandler
import json
import os
import requests
import sys

sys.path.append(os.path.dirname(__file__))

try:
    from supabase_client import supabase
except ImportError as e:
    print(f"Import error: {e}")

class Handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS, GET, PUT')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def do_GET(self):
        try:
            user_id = self.headers.get('User-Id', '')
            is_admin = self.headers.get('Is-Admin', 'false') == 'true'
            
            if is_admin:
                response = supabase.table("orders").select("*, order_statuses(name)").execute()
                orders = response.data
            else:
                response = supabase.table("orders").select("*").eq("user_id", user_id).execute()
                orders = response.data
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            self.wfile.write(json.dumps(orders).encode('utf-8'))
            
        except Exception as e:
            print(f"Error in order GET handler: {e}")
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            response = {'success': False, 'error': str(e)}
            self.wfile.write(json.dumps(response).encode('utf-8'))
    
    def do_PUT(self):
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            order_data = json.loads(post_data)
            
            order_id = order_data.get('order_id')
            status_id = order_data.get('status_id')
            admin_notes = order_data.get('admin_notes', '')
            
            update_data = {}
            if status_id:
                update_data['status_id'] = status_id
            if admin_notes is not None:
                update_data['admin_notes'] = admin_notes
            
            response = supabase.table("orders").update(update_data).eq("id", order_id).execute()
            
            if status_id:
                self.send_order_notification(order_id, status_id)
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            response_data = {'success': True, 'message': 'Order updated successfully'}
            self.wfile.write(json.dumps(response_data).encode('utf-8'))
            
        except Exception as e:
            print(f"Error in order PUT handler: {e}")
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            response = {'success': False, 'error': str(e)}
            self.wfile.write(json.dumps(response).encode('utf-8'))
    
    def do_POST(self):
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            order_data = json.loads(post_data)
            
            admin_success = self.send_admin_notification(order_data)
            db_success = self.save_order_to_db(order_data)
            
            if db_success:
                self.send_user_confirmation(order_data)
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            response = {'success': True, 'message': 'Order processed successfully'}
            self.wfile.write(json.dumps(response).encode('utf-8'))
            
        except Exception as e:
            print(f"Error in order POST handler: {e}")
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
🏙️ Город: Ярославль

🛍️ <b>Состав заказа:</b>
{items_text}

💵 <b>Итого к оплате:</b> {order_data['total']} ₽

📋 <b>Комментарий:</b> {order_data['comment'] or 'Нет комментария'}

🕐 <b>Время заказа:</b> {order_data['time']}"""
            
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            payload = {
                'chat_id': admin_chat_id,
                'text': message,
                'parse_mode': 'HTML',
                'disable_web_page_preview': True
            }
            
            response = requests.post(url, json=payload, timeout=10)
            return response.status_code == 200
            
        except Exception as e:
            print(f"Error sending admin notification: {e}")
            return False

    def save_order_to_db(self, order_data):
        try:
            clean_phone = order_data['phone'].replace(' ', '').replace('(', '').replace(')', '').replace('-', '')
            
            order_record = {
                "user_id": str(order_data['user']['id']),
                "user_name": order_data['user']['first_name'],
                "user_username": order_data['user'].get('username', ''),
                "phone": clean_phone,
                "comment": order_data.get('comment', ''),
                "items": order_data['items'],
                "total_amount": order_data['total'],
                "status_id": 1
            }
            
            result = supabase.table("orders").insert(order_record).execute()
            print(f"Order saved to DB: {result}")
            return True
            
        except Exception as e:
            print(f"Error saving order to DB: {e}")
            return False

    def send_user_confirmation(self, order_data):
        try:
            bot_token = os.environ.get('BOT_TOKEN')
            user_chat_id = order_data['user']['id']
            
            items_text = "\n".join([
                f"• {item['name']} - {item['quantity']} шт." 
                for item in order_data['items']
            ])
            
            message = f"""✅ *Ваш заказ принят!*

🛍 *Состав заказа:*
{items_text}

💵 *Сумма заказа:* {order_data['total']} ₽

📞 *Ваш телефон:* {order_data['phone']}

⏱ *Время заказа:* {order_data['time']}

Мы свяжемся с вами в ближайшее время для подтверждения заказа и уточнения деталей доставки.

Спасибо за ваш заказ! 💐"""
            
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            payload = {
                'chat_id': user_chat_id,
                'text': message,
                'parse_mode': 'Markdown'
            }
            
            response = requests.post(url, json=payload, timeout=10)
            return response.status_code == 200
            
        except Exception as e:
            print(f"Error sending user confirmation: {e}")
            return False

    def send_order_notification(self, order_id, status_id):
        try:
            bot_token = os.environ.get('BOT_TOKEN')
            
            order_response = supabase.table("orders").select("*, order_statuses(name)").eq("id", order_id).execute()
            if not order_response.data:
                return False
            
            order = order_response.data[0]
            status_name = order['order_statuses']['name']
            
            status_messages = {
                1: "✅ Ваш заказ принят! Мы начинаем его обработку.",
                2: "🔄 Заказ подтвержден! Мы готовим его к отправке.",
                3: "📦 Ваш заказ собирается! Скоро он будет у вас.",
                4: "🚗 Заказ в пути! Курьер уже везет его к вам.",
                5: "🎉 Заказ доставлен! Спасибо за покупку!",
                6: "❌ Заказ отменен."
            }
            
            message = status_messages.get(status_id, f"Статус заказа изменен: {status_name}")
            
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            payload = {
                'chat_id': order['user_id'],
                'text': message,
                'parse_mode': 'Markdown'
            }
            
            response = requests.post(url, json=payload, timeout=10)
            return response.status_code == 200
            
        except Exception as e:
            print(f"Error sending order notification: {e}")
            return False
