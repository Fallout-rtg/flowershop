from http.server import BaseHTTPRequestHandler
import json
import os
import requests
import sys
from datetime import datetime
import io, tempfile, json, os, requests
from datetime import datetime
import csv

sys.path.append(os.path.dirname(__file__))

try:
    from supabase_init import supabase
    from health import log_error
except ImportError as e:
    print(f"Import error: {e}")

# Добавляем импорт для работы с Excel
try:
    import openpyxl
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
except ImportError as e:
    print(f"⚠️ Openpyxl import error: {e}")
    # Создаем заглушки для совместимости
    openpyxl = None

class Handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS, GET, PUT, DELETE')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Telegram-Id, Is-Admin, User-Id')
        self.end_headers()
    
    def do_GET(self):
        try:
            print(f"📥 GET запрос на путь: {self.path}")
            
            # Добавляем обработку экспорта заказов
            if self.path == '/api/order/export' or self.path.startswith('/api/order/export'):
                print("🔄 Вызов handle_export_orders из do_GET")
                return self.handle_export_orders()
            
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
            log_error("order_GET", e, self.headers.get('User-Id', ''), "Failed to fetch orders")
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
            log_error("order_PUT", e, self.headers.get('User-Id', ''), f"Order ID: {order_data.get('order_id')}")
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            response = {'success': False, 'error': str(e)}
            self.wfile.write(json.dumps(response).encode('utf-8'))
    
    def do_POST(self):
        try:
            print(f"📥 POST запрос на путь: {self.path}")
            
            # Убираем обработку экспорта из POST, теперь она в GET
            if self.path == '/api/order/export' or self.path.startswith('/api/order/export'):
                print("❌ Экспорт должен вызываться через GET метод")
                self.send_response(405)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                response = {'success': False, 'error': 'Используйте GET метод для экспорта'}
                self.wfile.write(json.dumps(response).encode('utf-8'))
                return
                
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            order_data = json.loads(post_data)
            
            user_id = str(order_data['user']['id'])
            
            db_success = self.save_order_to_db(order_data)
            
            if db_success:
                delivery_option = order_data.get('delivery_option', 'pickup')
                delivery_address = order_data.get('delivery_address', '')
                discount_amount = order_data.get('discount_amount', 0)
                promocode_id = order_data.get('promocode_id')
                
                admin_success = self.send_admin_notification(order_data, delivery_option, delivery_address, discount_amount)
                
                # Отправляем уведомление клиенту
                customer_success = self.send_customer_notification(order_data)
                
                if promocode_id:
                    self.update_promocode_usage(promocode_id)
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            response = {'success': True, 'message': 'Order processed successfully', 'db_success': db_success}
            self.wfile.write(json.dumps(response).encode('utf-8'))
            
        except Exception as e:
            log_error("order_POST", e, order_data.get('user', {}).get('id', ''), "Failed to create order")
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
            log_error("order_DELETE", e, self.headers.get('User-Id', ''), f"Order ID: {order_id}")
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
                log_error("order_notification", "Missing BOT_TOKEN or no active admins", order_data['user']['id'], "Admin notification failed")
                return False
            
            clean_phone = order_data['phone'].replace(' ', '').replace('(', '').replace(')', '').replace('-', '')
            telegram_link = f"tg://openmessage?user_id={order_data['user']['id']}"
            
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
[📱 Написать в Telegram]({telegram_link})"""
            
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
                            {'text': '📱 Написать клиенту', 'url': telegram_link}
                        ]]
                    }
                }
                
                response = requests.post(url, json=payload, timeout=10)
                if response.status_code == 200:
                    success_count += 1
            
            return success_count > 0
            
        except Exception as e:
            log_error("admin_notification", e, order_data['user']['id'], "Failed to send admin notification")
            return False

    def send_customer_notification(self, order_data):
        try:
            bot_token = os.environ.get('BOT_TOKEN')
            user_id = order_data['user']['id']
            
            if not bot_token:
                log_error("customer_notification", "Missing BOT_TOKEN", user_id, "Failed to send customer notification")
                return False
            
            # Форматируем товары
            items_text = "\n".join([
                f"• {item['name']} - {item['quantity']} шт." 
                for item in order_data['items']
            ])
            
            # Форматируем телефон для красивого отображения
            phone = order_data['phone']
            # Убираем все нецифровые символы
            digits = ''.join(filter(str.isdigit, phone))
            
            if len(digits) >= 11:
                # Если номер начинается с 7, 8 или +7
                if digits.startswith('7') or digits.startswith('8'):
                    if digits.startswith('8'):
                        digits = '7' + digits[1:]
                    formatted_phone = f"+7 ({digits[1:4]}) {digits[4:7]}-{digits[7:9]}-{digits[9:11]}"
                else:
                    formatted_phone = phone
            else:
                formatted_phone = phone
            
            # Используем время из заказа или текущее время
            order_time = order_data.get('time', datetime.now().strftime('%d.%m.%Y, %H:%M:%S'))
            
            # Формируем сообщение
            message = f"""✅ Ваш заказ принят!

🛍 Состав заказа:
{items_text}

💵 Сумма заказа: {order_data['total']} ₽

📞 Ваш телефон: {formatted_phone}

⏱ Время заказа: {order_time}

Мы свяжемся с вами в ближайшее время для подтверждения заказа и уточнения деталей доставки.

Спасибо за ваш заказ! 💐"""
            
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            payload = {
                'chat_id': user_id,
                'text': message,
                'parse_mode': 'Markdown'
            }
            
            response = requests.post(url, json=payload, timeout=10)
            return response.status_code == 200
            
        except Exception as e:
            log_error("customer_notification", e, user_id, "Failed to send customer notification")
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
                try:
                    settings_response = supabase.table("shop_settings").select("value").eq("key", "delivery_price").execute()
                    if settings_response.data:
                        delivery_price = settings_response.data[0]['value'].get('value', 200)
                        free_delivery_min_response = supabase.table("shop_settings").select("value").eq("key", "free_delivery_min").execute()
                        if free_delivery_min_response.data:
                            free_delivery_min = free_delivery_min_response.data[0]['value'].get('value', 3000)
                        
                        delivery_cost = 0 if cart_total >= free_delivery_min else delivery_price
                except Exception as e:
                    print(f"⚠️ Delivery settings error: {e}")
            
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
            
            if result.data:
                return True
            else:
                return False
                
        except Exception as e:
            print(f"💥 Error saving order to database: {e}")
            return False

    def handle_export_orders(self):
        try:
            print(f"🔄 Начало обработки экспорта заказов через GET")
            
            bot_token = os.environ.get('BOT_TOKEN')
            user_id = self.headers.get('Telegram-Id', '')
            is_admin = self.headers.get('Is-Admin', 'false') == 'true'
            
            print(f"📊 Параметры запроса: bot_token={'установлен' if bot_token else 'отсутствует'}, user_id={user_id}, is_admin={is_admin}")
            
            if not bot_token:
                print("❌ Отсутствует BOT_TOKEN")
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                response_data = {'success': False, 'error': 'Отсутствует BOT_TOKEN'}
                self.wfile.write(json.dumps(response_data).encode('utf-8'))
                return
            
            if not user_id:
                print("❌ Отсутствует Telegram-Id")
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                response_data = {'success': False, 'error': 'Требуется авторизация'}
                self.wfile.write(json.dumps(response_data).encode('utf-8'))
                return
            
            if not is_admin:
                print("❌ Пользователь не является администратором")
                self.send_response(403)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                response_data = {'success': False, 'error': 'Требуются права администратора'}
                self.wfile.write(json.dumps(response_data).encode('utf-8'))
                return
            
            print("📋 Запрашиваем заказы из базы данных...")
            orders_response = supabase.table("orders").select("*").order('created_at', desc=True).execute()
            
            if not orders_response.data:
                print("⚠️ Нет данных для экспорта")
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                response_data = {'success': True, 'message': 'Нет данных для экспорта', 'data': []}
                self.wfile.write(json.dumps(response_data).encode('utf-8'))
                return
            
            print(f"✅ Найдено {len(orders_response.data)} заказов")
            
            # Проверяем, установлен ли openpyxl
            if openpyxl is None:
                print("⚠️ Библиотека openpyxl не установлена, используем CSV")
                return self.export_to_csv(orders_response.data, bot_token, user_id)
            
            # Создаем Excel файл с улучшенным форматированием
            return self.export_to_excel(orders_response.data, bot_token, user_id)
                
        except Exception as e:
            error_msg = str(e)
            print(f"💥 Критическая ошибка в экспорте: {error_msg}")
            log_error("export_orders", e, self.headers.get('Telegram-Id', ''), "Ошибка экспорта")
            
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            response_data = {'success': False, 'error': f'Ошибка сервера: {error_msg}'}
            self.wfile.write(json.dumps(response_data).encode('utf-8'))

    def export_to_excel(self, orders, bot_token, user_id):
        """Создание и отправка Excel файла с детализацией товаров в заказах"""
        try:
            print("📊 Создаем Excel файл с детализацией товаров...")
            
            # Создаем новую рабочую книгу Excel
            wb = Workbook()
            ws = wb.active
            ws.title = "Заказы с детализацией"
        
            # Определяем стили
            header_font = Font(name='Calibri', size=11, bold=True, color='FFFFFF')
            header_fill = PatternFill(start_color='366092', end_color='366092', fill_type='solid')
            header_alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        
            cell_font = Font(name='Calibri', size=10)
            money_font = Font(name='Calibri', size=10, bold=True, color='1F4E78')
            status_font = Font(name='Calibri', size=10, bold=True)
            product_font = Font(name='Calibri', size=10, color='2E4053')
        
            thin_border = Border(
                left=Side(style='thin'),
                right=Side(style='thin'),
                top=Side(style='thin'),
                bottom=Side(style='thin')
            )
        
            # Заголовки столбцов с детализацией товаров
            headers = [
                'ID заказа', 'Дата создания', 'Клиент', 'Телефон',
                'Товар', 'Кол-во', 'Цена за шт. (₽)', 'Сумма по товару (₽)',
                'Всего за заказ (₽)', 'Скидка (₽)', 'Итог с доставкой (₽)',
                'Способ получения', 'Адрес доставки', 'Статус', 'Комментарий к заказу'
            ]
        
            # Записываем заголовки
            for col_num, header in enumerate(headers, 1):
                cell = ws.cell(row=1, column=col_num, value=header)
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = header_alignment
                cell.border = thin_border
        
            # Карта статусов
            status_names = {
                1: ('Новый', 'FF6B6B'),
                2: ('Подтвержден', 'FFA726'),
                3: ('Собирается', '8E44AD'),
                4: ('В пути', '3498DB'),
                5: ('Доставлен', '27AE60'),
                6: ('Отменен', '7F8C8D')
            }
        
            row_num = 2
            total_orders_amount = 0
            total_final_amount = 0
            total_discount_amount = 0
            total_products_count = 0
        
            # Для подсчета товаров по заказам
            order_items_summary = {}
        
            # Заполняем данные с разверткой товаров
            for order in orders:
                # Форматируем дату
                order_time = ''
                if order.get('created_at'):
                    try:
                        order_time = datetime.fromisoformat(
                            order['created_at'].replace('Z', '+00:00')
                        ).strftime('%d.%m.%Y %H:%M')
                    except:
                        order_time = str(order['created_at'])
            
                # Получаем статус
                status_info = status_names.get(order['status_id'], ('Неизвестен', 'CCCCCC'))
                status_text, status_color = status_info
            
                # Форматируем телефон
                phone = order['phone']
                if len(phone) >= 10:
                    formatted_phone = f"+7 ({phone[1:4]}) {phone[4:7]}-{phone[7:9]}-{phone[9:11]}"
                else:
                    formatted_phone = phone
            
                # Форматируем адрес
                delivery_address = order.get('delivery_address', '')
                if order['delivery_option'] == 'pickup':
                    delivery_address = 'Самовывоз'
            
                # Получаем товары из JSON
                items = []
                try:
                    if isinstance(order['items'], str):
                        items = json.loads(order['items'])
                    else:
                        items = order['items']
                except:
                    items = []
            
                # Создаем запись для каждого товара в заказе
                for item_idx, item in enumerate(items):
                    # Общие данные заказа (будут повторяться для каждого товара)
                    ws.cell(row=row_num, column=1, value=order['id']).font = cell_font
                    ws.cell(row=row_num, column=2, value=order_time).font = cell_font
                    ws.cell(row=row_num, column=3, value=order['user_name']).font = cell_font
                    ws.cell(row=row_num, column=4, value=formatted_phone).font = cell_font
                
                    # Данные товара
                    item_name = item.get('name', 'Неизвестный товар')
                    item_quantity = item.get('quantity', 0)
                    item_price = item.get('price', 0)
                    item_total = item.get('total', 0)
                
                    ws.cell(row=row_num, column=5, value=item_name).font = product_font
                    ws.cell(row=row_num, column=6, value=item_quantity).font = cell_font
                    ws.cell(row=row_num, column=7, value=item_price).font = money_font
                    ws.cell(row=row_num, column=8, value=item_total).font = money_font
                
                    # Общие данные заказа (продолжение)
                    ws.cell(row=row_num, column=9, value=order['total_amount']).font = money_font
                    ws.cell(row=row_num, column=10, value=order.get('discount_amount', 0)).font = money_font
                    ws.cell(row=row_num, column=11, value=order['final_amount']).font = Font(name='Calibri', size=10, bold=True, color='E74C3C')
                
                    ws.cell(row=row_num, column=12, value='Доставка' if order['delivery_option'] == 'delivery' else 'Самовывоз').font = cell_font
                    ws.cell(row=row_num, column=13, value=delivery_address).font = cell_font
                
                    # Статус с цветом
                    status_cell = ws.cell(row=row_num, column=14, value=status_text)
                    status_cell.font = status_font
                    status_cell.fill = PatternFill(start_color=status_color, end_color=status_color, fill_type='solid')
                
                    ws.cell(row=row_num, column=15, value=order.get('comment', '')).font = cell_font
                
                    # Добавляем границы ко всем ячейкам
                    for col_num in range(1, 16):
                        ws.cell(row=row_num, column=col_num).border = thin_border
                
                    # Подсчет итогов (только для первого товара в заказе)
                    if item_idx == 0:
                        total_orders_amount += order['total_amount']
                        total_final_amount += order['final_amount']
                        total_discount_amount += order.get('discount_amount', 0)
                    
                        # Запоминаем детали заказа для итоговой таблицы
                        order_items_summary[order['id']] = {
                            'date': order_time,
                            'items': items,
                            'total_amount': order['total_amount'],
                            'final_amount': order['final_amount']
                        }
                
                    # Подсчет общего количества товаров
                    total_products_count += item_quantity
                    
                    row_num += 1
        
            # Настраиваем ширину столбцов
            column_widths = [10, 16, 20, 15, 35, 8, 12, 15, 15, 12, 15, 12, 25, 12, 30]
            for i, width in enumerate(column_widths, 1):
                ws.column_dimensions[get_column_letter(i)].width = width
        
            # Замораживаем заголовок
            ws.freeze_panes = 'A2'
        
            # Добавляем ИТОГОВУЮ СТРОКУ
            total_row = row_num + 1
            ws.cell(row=total_row, column=1, value='ИТОГО:').font = Font(bold=True, size=11)
            ws.merge_cells(start_row=total_row, start_column=1, end_row=total_row, end_column=5)
        
            # Итоговые показатели
            ws.cell(row=total_row, column=6, value=f"Товаров: {total_products_count} шт").font = Font(bold=True, color='1F4E78')
            ws.cell(row=total_row, column=7, value=f"Заказов: {len(orders)}").font = Font(bold=True, color='1F4E78')
            ws.cell(row=total_row, column=9, value=total_orders_amount).font = Font(bold=True, color='E74C3C')
            ws.cell(row=total_row, column=10, value=total_discount_amount).font = Font(bold=True, color='E74C3C')
            ws.cell(row=total_row, column=11, value=total_final_amount).font = Font(bold=True, color='E74C3C')
        
            # Создаем второй лист с детализацией по заказам
            ws2 = wb.create_sheet(title="Сводка по заказам")
        
            # Заголовки для сводки
            summary_headers = [
                'ID заказа', 'Дата', 'Клиент', 'Всего товаров в заказе',
                'Состав заказа (товар × кол-во)', 'Сумма заказа (₽)', 'Итог с доставкой (₽)'
            ]
        
            for col_num, header in enumerate(summary_headers, 1):
                cell = ws2.cell(row=1, column=col_num, value=header)
                cell.font = header_font
                cell.fill = PatternFill(start_color='27AE60', end_color='27AE60', fill_type='solid')
                cell.alignment = header_alignment
                cell.border = thin_border
        
            # Заполняем сводку
            summary_row = 2
            for order in orders:
                items = []
                try:
                    if isinstance(order['items'], str):
                        items = json.loads(order['items'])
                    else:
                        items = order['items']
                except:
                    items = []
            
                # Формируем строку с составом заказа
                items_text = "\n".join([f"• {item.get('name', 'Неизвестно')} × {item.get('quantity', 0)}" for item in items])
                total_items = sum(item.get('quantity', 0) for item in items)
            
                ws2.cell(row=summary_row, column=1, value=order['id']).font = cell_font
                ws2.cell(row=summary_row, column=2, value=order_time).font = cell_font
                ws2.cell(row=summary_row, column=3, value=order['user_name']).font = cell_font
                ws2.cell(row=summary_row, column=4, value=total_items).font = cell_font
                ws2.cell(row=summary_row, column=5, value=items_text).font = product_font
                ws2.cell(row=summary_row, column=6, value=order['total_amount']).font = money_font
                ws2.cell(row=summary_row, column=7, value=order['final_amount']).font = Font(bold=True, color='E74C3C')
            
                # Добавляем границы
                for col_num in range(1, 8):
                    ws2.cell(row=summary_row, column=col_num).border = thin_border
            
                # Настройка переноса текста для колонки с составом
                ws2.cell(row=summary_row, column=5).alignment = Alignment(wrap_text=True, vertical='top')
            
                summary_row += 1
        
            # Настраиваем ширину столбцов для сводки
            summary_widths = [10, 16, 20, 15, 40, 15, 15]
            for i, width in enumerate(summary_widths, 1):
                ws2.column_dimensions[get_column_letter(i)].width = width
        
            # Автоматическая высота строк для сводки
            for row in ws2.iter_rows(min_row=2, max_row=summary_row):
                max_lines = 1
                items_cell = row[4]  # Колонка с составом заказа
                if items_cell.value:
                    lines = str(items_cell.value).count('\n') + 1
                    max_lines = max(max_lines, lines)
            
                ws2.row_dimensions[row[0].row].height = max_lines * 15
        
            print("📁 Создаем временный файл Excel...")
            with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx', mode='wb') as tmp:
                wb.save(tmp.name)
                tmp_path = tmp.name
                print(f"✅ Временный файл создан: {tmp_path}")
        
            try:
                print("📤 Отправляем Excel файл в Telegram...")
                with open(tmp_path, 'rb') as f:
                    resp = requests.post(
                        f'https://api.telegram.org/bot{bot_token}/sendDocument',
                        data={
                            'chat_id': user_id, 
                            'caption': '📊 Детализированный отчет по заказам\n\n• Первый лист: детализация по товарам\n• Второй лист: сводка по заказам'
                        },
                        files={'document': ('orders_detailed_report.xlsx', f, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')},
                        timeout=30
                    )
            
                print(f"📩 Ответ Telegram API: {resp.status_code}")
            
                if resp.status_code == 200:
                    print("✅ Excel файл успешно отправлен в Telegram")
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    response_data = {'success': True, 'message': 'Excel файл отправлен в Telegram'}
                    self.wfile.write(json.dumps(response_data).encode('utf-8'))
                else:
                    error_text = resp.text[:200] if resp.text else 'Неизвестная ошибка'
                    print(f"❌ Ошибка Telegram API: {resp.status_code} - {error_text}")
                    self.send_response(500)
                    self.send_header('Content-type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    response_data = {'success': False, 'error': f'Ошибка отправки файла: {resp.status_code}'}
                    self.wfile.write(json.dumps(response_data).encode('utf-8'))
                
            finally:
                # Удаляем временный файл
                try:
                    os.unlink(tmp_path)
                    print("🗑 Временный файл удален")
                except:
                    pass
                
        except Exception as e:
            print(f"💥 Ошибка при создании Excel: {e}")
            # Пробуем создать CSV как fallback
            return self.export_to_csv(orders, bot_token, user_id)

    def export_to_csv(self, orders, bot_token, user_id):
        """Резервный метод для создания CSV файла"""
        try:
            print("📊 Создаем CSV файл (резервный метод)...")
            
            # Создаем CSV файл в памяти
            output = io.StringIO()
            csv_writer = csv.writer(output)
            
            # Заголовки CSV
            headers = ['ID', 'Дата и время', 'Клиент', 'Телефон', 'Сумма', 'Скидка', 'Итог', 
                      'Способ', 'Адрес', 'Статус', 'Комментарий']
            csv_writer.writerow(headers)
            
            status_names = {
                1: 'Новый',
                2: 'Подтвержден',
                3: 'Собирается',
                4: 'В пути',
                5: 'Доставлен',
                6: 'Отменен'
            }
            
            for order in orders:
                order_time = ''
                if order.get('created_at'):
                    try:
                        order_time = datetime.fromisoformat(order['created_at'].replace('Z', '+00:00')).strftime('%d.%m.%Y %H:%M')
                    except:
                        order_time = order['created_at']
                
                row = [
                    order['id'],
                    order_time,
                    order['user_name'],
                    order['phone'],
                    order['total_amount'],
                    order.get('discount_amount', 0),
                    order['final_amount'],
                    'Доставка' if order['delivery_option'] == 'delivery' else 'Самовывоз',
                    order.get('delivery_address', ''),
                    status_names.get(order['status_id'], 'Новый'),
                    (order.get('comment', '')[:50] + '...') if len(order.get('comment', '')) > 50 else order.get('comment', '')
                ]
                csv_writer.writerow(row)
            
            # Создаем файл в памяти
            csv_data = output.getvalue().encode('utf-8')
            
            print("📁 Создаем временный файл CSV...")
            with tempfile.NamedTemporaryFile(delete=False, suffix='.csv', mode='wb') as tmp:
                tmp.write(csv_data)
                tmp_path = tmp.name
                print(f"✅ Временный файл создан: {tmp_path}")
            
            try:
                print("📤 Отправляем CSV файл в Telegram...")
                with open(tmp_path, 'rb') as f:
                    resp = requests.post(
                        f'https://api.telegram.org/bot{bot_token}/sendDocument',
                        data={'chat_id': user_id, 'caption': '📊 Отчет по заказам в формате CSV'},
                        files={'document': ('orders_report.csv', f, 'text/csv')},
                        timeout=30
                    )
                
                print(f"📩 Ответ Telegram API: {resp.status_code}")
                
                if resp.status_code == 200:
                    print("✅ CSV файл успешно отправлен в Telegram")
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    response_data = {'success': True, 'message': 'CSV файл отправлен в Telegram'}
                    self.wfile.write(json.dumps(response_data).encode('utf-8'))
                else:
                    error_text = resp.text[:200] if resp.text else 'Неизвестная ошибка'
                    print(f"❌ Ошибка Telegram API: {resp.status_code} - {error_text}")
                    self.send_response(500)
                    self.send_header('Content-type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    response_data = {'success': False, 'error': f'Ошибка отправки файла: {resp.status_code}'}
                    self.wfile.write(json.dumps(response_data).encode('utf-8'))
                    
            finally:
                # Удаляем временный файл
                try:
                    os.unlink(tmp_path)
                    print("🗑 Временный файл удален")
                except:
                    pass
                
        except Exception as e:
            error_msg = str(e)
            print(f"💥 Ошибка при создании CSV: {error_msg}")
            
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            response_data = {'success': False, 'error': f'Ошибка создания файла: {error_msg}'}
            self.wfile.write(json.dumps(response_data).encode('utf-8'))

    def send_order_notification(self, order_id, status_id):
        try:
            bot_token = os.environ.get('BOT_TOKEN')
            
            if not bot_token:
                log_error("order_notification", "Missing BOT_TOKEN", "", "Failed to send order notification")
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
            log_error("order_notification", e, "", f"Order ID: {order_id}")
            return False

    def update_promocode_usage(self, promocode_id):
        try:
            promocode_response = supabase.table("promocodes").select("used_count").eq("id", promocode_id).execute()
            if promocode_response.data:
                current_count = promocode_response.data[0].get('used_count', 0)
                supabase.table("promocodes").update({"used_count": current_count + 1}).eq("id", promocode_id).execute()
                
        except Exception as e:
            log_error("promocode_update", e, "", f"Promocode ID: {promocode_id}")
