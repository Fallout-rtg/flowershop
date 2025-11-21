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
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS, GET, PUT, DELETE')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def do_GET(self):
        try:
            user_id = self.headers.get('User-Id', '')
            is_admin = self.headers.get('Is-Admin', 'false') == 'true'
            
            if is_admin:
                orders_response = supabase.table("orders").select("*").execute()
                statuses_response = supabase.table("order_statuses").select("*").execute()
                
                orders = orders_response.data
                statuses = statuses_response.data
                
                status_map = {status['id']: status for status in statuses}
                
                for order in orders:
                    status_info = status_map.get(order['status_id'])
                    if status_info:
                        order['status_name'] = status_info['name']
                        order['status_color'] = status_info['color']
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
            
            if not order_id:
                raise ValueError("Order ID is required")
            
            update_data = {'status_id': status_id}
            
            if status_id == 5:
                order_response = supabase.table("orders").select("total_amount, discount_amount").eq("id", order_id).execute()
                if order_response.data:
                    order = order_response.data[0]
                    profit = order['total_amount'] - (order['discount_amount'] or 0)
                    update_data['profit'] = profit
            
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
            
            db_success = self.save_order_to_db(order_data)
            
            if db_success:
                delivery_option = order_data.get('delivery_option', 'pickup')
                delivery_address = order_data.get('delivery_address', '')
                discount_amount = order_data.get('discount_amount', 0)
                promocode_id = order_data.get('promocode_id')
                
                admin_success = self.send_admin_notification(order_data, delivery_option, delivery_address, discount_amount)
                
                if promocode_id:
                    self.update_promocode_usage(promocode_id)
            
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
    
    def do_DELETE(self):
        try:
            path_parts = self.path.split('/')
            order_id = path_parts[-1] if path_parts[-1] else path_parts[-2]
            
            if not order_id.isdigit():
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                response = {'success': False, 'error': 'Invalid order ID'}
                self.wfile.write(json.dumps(response).encode('utf-8'))
                return
            
            response = supabase.table("orders").delete().eq("id", int(order_id)).execute()
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            response_data = {'success': True}
            self.wfile.write(json.dumps(response_data).encode('utf-8'))
            
        except Exception as e:
            print(f"Error in order DELETE handler: {e}")
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            response = {'success': False, 'error': str(e)}
            self.wfile.write(json.dumps(response).encode('utf-8'))
    
    def send_admin_notification(self, order_data, delivery_option, delivery_address, discount_amount):
        try:
            bot_token = os.environ.get('BOT_TOKEN')
            
            admins_response = supabase.table("admins").select("telegram_id").eq("is_active", True).execute()
            admin_chat_ids = [admin['telegram_id'] for admin in admins_response.data]
            
            if not bot_token or not admin_chat_ids:
                print("Missing BOT_TOKEN or no active admins")
                return False
            
            clean_phone = order_data['phone'].replace(' ', '').replace('(', '').replace(')', '').replace('-', '')
            telegram_link = f"tg://openmessage?user_id={order_data['user']['id']}"
            phone_link = f"https://t.me/+{clean_phone}" if clean_phone.startswith('7') else f"https://t.me/+7{clean_phone}"
            
            delivery_info = "🚚 Доставка" if delivery_option == "delivery" else "🏪 Самовывоз"
            if delivery_option == "delivery" and delivery_address:
                delivery_info += f"\n📍 Адрес: {delivery_address}"
            else:
                settings_response = supabase.table("shop_settings").select("value").eq("key", "contacts").execute()
                if settings_response.data:
                    contacts = settings_response.data[0]['value']
                    pickup_address = contacts.get('address', 'Ярославль, ул. Цветочная, 15')
                    delivery_info += f"\n📍 Адрес самовывоза: {pickup_address}"
            
            items_text = "\n".join([
                f"• {item['name']} - {item['quantity']} шт. × {item['price']} ₽ = {item['total']} ₽" 
                for item in order_data['items']
            ])
            
            cart_total = order_data['total']
            delivery_cost = 0
            free_delivery_min = 3000
            
            if delivery_option == "delivery":
                settings_response = supabase.table("shop_settings").select("value").eq("key", "delivery_price").execute()
                if settings_response.data:
                    delivery_price = settings_response.data[0]['value'].get('value', 200)
                    free_delivery_min_response = supabase.table("shop_settings").select("value").eq("key", "free_delivery_min").execute()
                    if free_delivery_min_response.data:
                        free_delivery_min = free_delivery_min_response.data[0]['value'].get('value', 3000)
                    
                    delivery_cost = 0 if cart_total >= free_delivery_min else delivery_price
            
            total_with_delivery = cart_total + delivery_cost - discount_amount
            
            discount_text = f"🎫 Скидка по промокоду: -{discount_amount} ₽\n" if discount_amount > 0 else ""
            
            message = f"""🎉 *НОВЫЙ ЗАКАЗ!*

👤 *Информация о клиенте:*
🆔 ID: `{order_data['user']['id']}`
📛 Имя: {order_data['user']['first_name']}
👤 Юзернейм: @{order_data['user']['username']}
📞 Телефон: `{clean_phone}`

{delivery_info}

🛍️ *Состав заказа:*
{items_text}

💵 *Сумма заказа:* {cart_total} ₽
🚚 *Доставка:* {f'{delivery_cost} ₽' if delivery_cost > 0 else 'Бесплатно'} {f'(бесплатно от {free_delivery_min} ₽)' if delivery_cost > 0 else ''}
{discount_text}💎 *Итого к оплате:* {total_with_delivery} ₽

📋 *Комментарий:* {order_data.get('comment', 'Нет комментария')}

🕐 *Время заказа:* {order_data['time']}

💬 *Связаться с клиентом:*
[📱 По ID]({telegram_link}) | [☎️ По номеру]({phone_link})"""
            
            success_count = 0
            for admin_chat_id in admin_chat_ids:
                url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
                payload = {
                    'chat_id': admin_chat_id,
                    'text': message,
                    'parse_mode': 'Markdown',
                    'disable_web_page_preview': True,
                    'reply_markup': {
                        'inline_keyboard': [[
                            {'text': '📱 Написать по ID', 'url': telegram_link},
                            {'text': '☎️ Написать по номеру', 'url': phone_link}
                        ]]
                    }
                }
                
                response = requests.post(url, json=payload, timeout=10)
                if response.status_code == 200:
                    success_count += 1
            
            return success_count > 0
            
        except Exception as e:
            print(f"Error sending admin notification: {e}")
            return False

    def save_order_to_db(self, order_data):
        try:
            clean_phone = order_data['phone'].replace(' ', '').replace('(', '').replace(')', '').replace('-', '')
            
            cart_total = order_data['total']
            delivery_option = order_data.get('delivery_option', 'pickup')
            delivery_address = order_data.get('delivery_address', '')
            promocode_id = order_data.get('promocode_id')
            discount_amount = order_data.get('discount_amount', 0)
            
            delivery_cost = 0
            free_delivery_min = 3000
            
            if delivery_option == "delivery":
                settings_response = supabase.table("shop_settings").select("value").eq("key", "delivery_price").execute()
                if settings_response.data:
                    delivery_price = settings_response.data[0]['value'].get('value', 200)
                    free_delivery_min_response = supabase.table("shop_settings").select("value").eq("key", "free_delivery_min").execute()
                    if free_delivery_min_response.data:
                        free_delivery_min = free_delivery_min_response.data[0]['value'].get('value', 3000)
                    
                    delivery_cost = 0 if cart_total >= free_delivery_min else delivery_price
            
            final_amount = cart_total + delivery_cost - discount_amount
            
            order_record = {
                "user_id": str(order_data['user']['id']),
                "user_name": order_data['user']['first_name'],
                "user_username": order_data['user'].get('username', ''),
                "phone": clean_phone,
                "comment": order_data.get('comment', ''),
                "delivery_option": delivery_option,
                "delivery_address": delivery_address,
                "items": order_data['items'],
                "total_amount": cart_total,
                "discount_amount": discount_amount,
                "final_amount": final_amount,
                "promocode_id": promocode_id,
                "status_id": 1,
                "profit": 0
            }
            
            result = supabase.table("orders").insert(order_record).execute()
            print(f"Order saved to DB with ID: {result.data[0]['id'] if result.data else 'Unknown'}")
            return True
            
        except Exception as e:
            print(f"Error saving order to DB: {e}")
            return False

    def send_order_notification(self, order_id, status_id):
        try:
            bot_token = os.environ.get('BOT_TOKEN')
            
            if not bot_token:
                print("Missing BOT_TOKEN")
                return False
            
            order_response = supabase.table("orders").select("*").eq("id", order_id).execute()
            if not order_response.data:
                return False
            
            order = order_response.data[0]
            
            status_messages = {
                1: "✅ Ваш заказ принят! Мы начинаем его обработку.",
                2: "🔄 Заказ подтвержден! Мы готовим его к отправке.",
                3: "📦 Ваш заказ собирается! Скоро он будет у вас.",
                4: "🚗 Заказ в пути! Курьер уже везет его к вам.",
                5: "🎉 Заказ доставлен! Спасибо за покупку!",
                6: "❌ Заказ отменен."
            }
            
            message = status_messages.get(status_id, f"Статус заказа изменен")
            
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

    def update_promocode_usage(self, promocode_id):
        try:
            promocode_response = supabase.table("promocodes").select("used_count").eq("id", promocode_id).execute()
            if promocode_response.data:
                current_count = promocode_response.data[0].get('used_count', 0)
                supabase.table("promocodes").update({"used_count": current_count + 1}).eq("id", promocode_id).execute()
                
        except Exception as e:
            print(f"Error updating promocode usage: {e}")
