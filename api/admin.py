from http.server import BaseHTTPRequestHandler
import json
import os
import sys

sys.path.append(os.path.dirname(__file__))

try:
    from supabase_client import supabase
    print("✅ Supabase client imported successfully")
except ImportError as e:
    print(f"❌ Import error: {e}")

class Handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def do_GET(self):
        try:
            print(f"📨 Received GET request: {self.path}")
            path = self.path
            telegram_id = self.headers.get('Telegram-Id', '').strip()
            print(f"🔍 Checking admin access for Telegram ID: '{telegram_id}'")
            
            # Проверяем подключение к Supabase
            try:
                # Тестовый запрос к products чтобы проверить подключение
                test_response = supabase.table("products").select("id").limit(1).execute()
                print(f"✅ Supabase connection test: {len(test_response.data)} products found")
            except Exception as e:
                print(f"❌ Supabase connection failed: {e}")
                raise e
            
            if '/admins' in path:
                print("📋 Fetching all admins")
                response = supabase.table("admins").select("*").execute()
                data = response.data
                print(f"✅ Found {len(data)} admins")
                
            elif '/stats' in path:
                print("📊 Fetching stats")
                orders_response = supabase.table("orders").select("*").execute()
                products_response = supabase.table("products").select("*").execute()
                admins_response = supabase.table("admins").select("*").eq("is_active", True).execute()
                
                total_orders = len(orders_response.data)
                total_revenue = sum(order['total_amount'] for order in orders_response.data)
                total_products = len(products_response.data)
                active_admins = len(admins_response.data)
                
                data = {
                    'total_orders': total_orders,
                    'total_revenue': total_revenue,
                    'total_products': total_products,
                    'active_admins': active_admins
                }
                print(f"📊 Stats: {total_orders} orders, {total_revenue} revenue, {total_products} products, {active_admins} admins")
                
            elif '/statuses' in path:
                print("📋 Fetching order statuses")
                response = supabase.table("order_statuses").select("*").execute()
                data = response.data
                print(f"✅ Found {len(data)} statuses")
                
            else:
                # Детальная проверка администратора
                print(f"🔐 Detailed admin check for: '{telegram_id}'")
                
                # 1. Сначала проверим без условия is_active
                response_all = supabase.table("admins").select("*").eq("telegram_id", telegram_id).execute()
                print(f"📡 All records found (including inactive): {len(response_all.data)}")
                
                # 2. Проверим с условием is_active
                response_active = supabase.table("admins").select("*").eq("telegram_id", telegram_id).eq("is_active", True).execute()
                print(f"📡 Active records found: {len(response_active.data)}")
                
                # 3. Выведем все записи для отладки
                if response_all.data:
                    for i, record in enumerate(response_all.data):
                        print(f"👤 Record {i+1}: id={record.get('id')}, telegram_id='{record.get('telegram_id')}', is_active={record.get('is_active')}, role={record.get('role')}")
                
                # Проверяем есть ли активные администраторы
                is_admin = len(response_active.data) > 0
                
                if is_admin:
                    admin_data = response_active.data[0]
                    data = {
                        'is_admin': True,
                        'is_active': admin_data.get('is_active', True),
                        'role': admin_data.get('role', 'manager'),
                        'first_name': admin_data.get('first_name', ''),
                        'username': admin_data.get('username', ''),
                        'telegram_id': admin_data.get('telegram_id', ''),
                        'debug': {
                            'all_records': len(response_all.data),
                            'active_records': len(response_active.data)
                        }
                    }
                    print(f"✅ Admin access GRANTED: {data}")
                else:
                    data = {
                        'is_admin': False,
                        'is_active': False,
                        'debug': {
                            'all_records': len(response_all.data),
                            'active_records': len(response_active.data),
                            'searched_telegram_id': telegram_id
                        }
                    }
                    print(f"❌ Admin access DENIED. All records: {len(response_all.data)}, Active records: {len(response_active.data)}")
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            self.wfile.write(json.dumps(data).encode('utf-8'))
            print("✅ Response sent successfully")
            
        except Exception as e:
            print(f"❌ Error in admin GET handler: {e}")
            import traceback
            print(f"🔍 Stack trace: {traceback.format_exc()}")
            
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
            admin_data = json.loads(post_data)
            
            print(f"📝 Adding new admin: {admin_data}")
            
            if 'is_active' not in admin_data:
                admin_data['is_active'] = True
                
            response = supabase.table("admins").insert(admin_data).execute()
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            response_data = {'success': True, 'admin': response.data[0] if response.data else None}
            self.wfile.write(json.dumps(response_data).encode('utf-8'))
            print("✅ Admin added successfully")
            
        except Exception as e:
            print(f"❌ Error in admin POST handler: {e}")
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            response = {'success': False, 'error': str(e)}
            self.wfile.write(json.dumps(response).encode('utf-8'))
    
    def do_DELETE(self):
        try:
            admin_id = self.path.split('/')[-1]
            print(f"🗑️ Deleting admin with ID: {admin_id}")
            
            response = supabase.table("admins").delete().eq("id", admin_id).execute()
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            response_data = {'success': True}
            self.wfile.write(json.dumps(response_data).encode('utf-8'))
            print("✅ Admin deleted successfully")
            
        except Exception as e:
            print(f"❌ Error in admin DELETE handler: {e}")
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            response = {'success': False, 'error': str(e)}
            self.wfile.write(json.dumps(response).encode('utf-8'))
