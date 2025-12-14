from http.server import BaseHTTPRequestHandler
import json
import os
import sys
from datetime import datetime

sys.path.append(os.path.dirname(__file__))

try:
    from supabase_client import supabase
    from health import log_error
except ImportError as e:
    print(f"Import error: {e}")

class Handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def do_GET(self):
        try:
            path = self.path
            telegram_id = self.headers.get('Telegram-Id', '').strip()
            
            # Начало блока, где была указана ошибка
            if '/categories' in path:
                response = supabase.table("categories").select("*").order("sort_order").execute()
                data = response.data
            elif '/admins' in path:
                response = supabase.table("admins").select("*").execute()
                data = response.data
            elif '/stats' in path:
                orders_response = supabase.table("orders").select("*").execute()
                products_response = supabase.table("products").select("*").execute()
                promocodes_response = supabase.table("promocodes").select("*").execute()
                
                total_orders = len(orders_response.data)
                completed_orders = len([o for o in orders_response.data if o.get('status_id') == 5])
                total_revenue = sum(order.get('profit', 0) for order in orders_response.data if order.get('status_id') == 5)
                potential_revenue = sum(order['total_amount'] for order in orders_response.data if order.get('status_id') != 5)
                total_products = len(products_response.data)
                active_promocodes = len([p for p in promocodes_response.data if p.get('is_active')])
                
                data = {
                    'total_orders': total_orders,
                    'completed_orders': completed_orders,
                    'total_revenue': total_revenue,
                    'potential_revenue': potential_revenue,
                    'total_products': total_products,
                    'active_promocodes': active_promocodes
                }
            elif '/themes' in path:
                response = supabase.table("shop_themes").select("*").execute()
                data = response.data
            elif '/settings' in path:
                response = supabase.table("shop_settings").select("*").execute()
                data = {item['key']: item['value'] for item in response.data}
            elif '/confirmation-codes' in path:
                response = supabase.table("confirmation_codes").select("*").execute()
                data = response.data
            else:
                response = supabase.table("admins").select("role,is_active,first_name,username").eq("telegram_id", telegram_id).eq("is_active", True).execute()
                is_admin = len(response.data) > 0
                
                if is_admin:
                    admin_data = response.data[0]
                    data = {
                        'is_admin': True,
                        'is_active': admin_data.get('is_active', True),
                        'role': admin_data.get('role', 'manager'),
                        'first_name': admin_data.get('first_name', ''),
                        'username': admin_data.get('username', '')
                    }
                else:
                    data = {'is_admin': False}
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            self.wfile.write(json.dumps(data).encode('utf-8'))
            
        except Exception as e:
            log_error("admin_GET", e, self.headers.get('Telegram-Id', ''), f"Path: {path}")
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
            data = json.loads(post_data)
            
            if 'telegram_id' in data:
                admin_data = data
                if 'is_active' not in admin_data:
                    admin_data['is_active'] = True
                    
                response = supabase.table("admins").insert(admin_data).execute()
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                
                response_data = {'success': True, 'admin': response.data[0] if response.data else None}
                self.wfile.write(json.dumps(response_data).encode('utf-8'))
            elif 'name' in data and 'slug' in data:
                category_data = {
                    'name': data['name'],
                    'slug': data['slug'],
                    'icon': data.get('icon', 'fas fa-folder'),
                    'sort_order': data.get('sort_order', 0),
                    'is_active': data.get('is_active', True)
                }
                
                max_order_response = supabase.table("categories").select("sort_order").order("sort_order", desc=True).limit(1).execute()
                max_order = max_order_response.data[0]['sort_order'] if max_order_response.data else 0
                category_data['sort_order'] = max_order + 1
                
                response = supabase.table("categories").insert(category_data).execute()
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                
                response_data = {'success': True, 'category': response.data[0] if response.data else None}
                self.wfile.write(json.dumps(response_data).encode('utf-8'))
            else:
                key = data.get('key')
                value = data.get('value')
                
                if key and value is not None:
                    existing = supabase.table("shop_settings").select("*").eq("key", key).execute()
                    
                    if existing.data:
                        response = supabase.table("shop_settings").update({"value": value}).eq("key", key).execute()
                    else:
                        response = supabase.table("shop_settings").insert({"key": key, "value": value}).execute()
                    
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    
                    response_data = {'success': True}
                    self.wfile.write(json.dumps(response_data).encode('utf-8'))
                else:
                    self.send_response(400)
                    self.send_header('Content-type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    response = {'success': False, 'error': 'Missing key or value'}
                    self.wfile.write(json.dumps(response).encode('utf-8'))
            
        except Exception as e:
            log_error("admin_POST", e, self.headers.get('Telegram-Id', ''), f"Data: {data}")
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
            data = json.loads(post_data)
            
            path_parts = self.path.split('/')
            
            if 'categories/reorder' in self.path:
                categories_order = data.get('reorder', {})
                for category_id, sort_order in categories_order.items():
                    supabase.table("categories").update({"sort_order": sort_order}).eq("id", int(category_id)).execute()
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                response_data = {'success': True}
                self.wfile.write(json.dumps(response_data).encode('utf-8'))
                
            elif 'category' in path_parts:
                category_id = path_parts[-1] if path_parts[-1] else path_parts[-2]
                
                if not category_id.isdigit():
                    self.send_response(400)
                    self.send_header('Content-type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    response = {'success': False, 'error': 'Invalid category ID'}
                    self.wfile.write(json.dumps(response).encode('utf-8'))
                    return
                
                response = supabase.table("categories").update(data).eq("id", int(category_id)).execute()
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                
                response_data = {'success': True, 'category': response.data[0] if response.data else None}
                self.wfile.write(json.dumps(response_data).encode('utf-8'))
                
            elif 'theme_id' in data:
                theme_id = data['theme_id']
                supabase.table("shop_themes").update({"is_active": False}).neq("id", 0).execute()
                supabase.table("shop_themes").update({"is_active": True}).eq("id", theme_id).execute()
                
                existing = supabase.table("shop_settings").select("*").eq("key", "active_theme").execute()
                if existing.data:
                    supabase.table("shop_settings").update({"value": {"value": str(theme_id)}}).eq("key", "active_theme").execute()
                else:
                    supabase.table("shop_settings").insert({"key": "active_theme", "value": {"value": str(theme_id)}}).execute()
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                
                response_data = {'success': True}
                self.wfile.write(json.dumps(response_data).encode('utf-8'))
            else:
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                response = {'success': False, 'error': 'Invalid request'}
                self.wfile.write(json.dumps(response).encode('utf-8'))
                
        except Exception as e:
            log_error("admin_PUT", e, self.headers.get('Telegram-Id', ''), f"Data: {data}")
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            response = {'success': False, 'error': str(e)}
            self.wfile.write(json.dumps(response).encode('utf-8'))
    
    def do_DELETE(self):
        resource_id = None
        try:
            # 1. Проверка доступа
            if not check_admin_token(self.headers):
                self.send_response(403)
                response_data = {'success': False, 'error': "Доступ запрещен. Неверный или отсутствует токен администратора."}
            else:
                # 2. Парсинг пути
                path_parts = self.path.split('/')
                resource_id = path_parts[-1] if path_parts[-1] else path_parts[-2]
                
                table_name = ''
                if '/admin/category/' in self.path:
                    table_name = 'categories'
                elif '/admin/product/' in self.path:
                    table_name = 'products'
                elif '/admin/order/' in self.path:
                    table_name = 'orders'
                else:
                    self.send_response(404)
                    response_data = {'success': False, 'error': "Неизвестный или неподдерживаемый ресурс для удаления."}
                    table_name = None # Защита от дальнейших действий
                
                if table_name:
                    # 3. Выполнение удаления в Supabase
                    data, count = supabase.table(table_name).delete().eq("id", resource_id).execute()
                    
                    # 4. Проверка результата
                    if count > 0:
                        self.send_response(200)
                        response_data = {'success': True, 'message': f"Ресурс {resource_id} успешно удален."}
                    else:
                        self.send_response(404)
                        response_data = {'success': False, 'error': f"Ресурс с ID {resource_id} не найден."}

        except Exception as e:
            error_message = str(e)
            
            # 5. Обработка ошибки внешнего ключа (FK)
            # В Supabase/PostgreSQL ошибка FK часто содержит слова 'foreign key constraint'
            if "foreign key constraint" in error_message or "IntegrityError" in error_message:
                self.send_response(400) # 400 Bad Request
                response_data = {'success': False, 'error': "Невозможно удалить ресурс. Сначала удалите или измените связанные с ним записи (например, товары, привязанные к этой категории)."}
            else:
                # 6. Обработка общей ошибки сервера
                log_error("admin_DELETE", e, self.headers.get('Telegram-Id', ''), f"Resource ID: {resource_id}")
                self.send_response(500)
                response_data = {'success': False, 'error': f"Ошибка сервера: {e}"}

        # 7. Финализация ответа
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(response_data).encode('utf-8'))
