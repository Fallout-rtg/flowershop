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
            telegram_id = self.headers.get('Telegram-Id', '')
            print(f"🔍 Checking admin access for Telegram ID: {telegram_id}")
            
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
                # Проверяем активных администраторов
                print(f"🔐 Checking admin status for: {telegram_id}")
                response = supabase.table("admins").select("*").eq("telegram_id", telegram_id).eq("is_active", True).execute()
                print(f"📡 Supabase response: {len(response.data)} records found")
                
                if response.data:
                    for record in response.data:
                        print(f"👤 Admin record: {record}")
                
                is_admin = len(response.data) > 0
                
                # Если нашли активного админа, возвращаем его данные
                if is_admin:
                    admin_data = response.data[0]
                    data = {
                        'is_admin': True,
                        'is_active': admin_data.get('is_active', True),
                        'role': admin_data.get('role', 'manager'),
                        'first_name': admin_data.get('first_name', ''),
                        'username': admin_data.get('username', ''),
                        'telegram_id': admin_data.get('telegram_id', '')
                    }
                    print(f"✅ Admin access granted: {data}")
                else:
                    data = {
                        'is_admin': False,
                        'is_active': False,
                        'found_records': len(response.data)
                    }
                    print(f"❌ Admin access denied. Found {len(response.data)} records")
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            self.wfile.write(json.dumps(data).encode('utf-8'))
            print("✅ Response sent successfully")
            
        except Exception as e:
            print(f"❌ Error in admin GET handler: {e}")
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
            
            # Убедимся, что новый админ активен по умолчанию
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
