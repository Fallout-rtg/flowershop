from http.server import BaseHTTPRequestHandler
import json
import os
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
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def do_GET(self):
        try:
            path = self.path
            telegram_id = self.headers.get('Telegram-Id', '').strip()
            
            if '/admins' in path:
                response = supabase.table("admins").select("*").execute()
                data = response.data
            elif '/stats' in path:
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
            elif '/statuses' in path:
                response = supabase.table("order_statuses").select("*").execute()
                data = response.data
            else:
                response = supabase.table("admins").select("*").eq("telegram_id", telegram_id).eq("is_active", True).execute()
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
            print(f"Error in admin GET handler: {e}")
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
            
            if 'is_active' not in admin_data:
                admin_data['is_active'] = True
                
            response = supabase.table("admins").insert(admin_data).execute()
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            response_data = {'success': True, 'admin': response.data[0] if response.data else None}
            self.wfile.write(json.dumps(response_data).encode('utf-8'))
            
        except Exception as e:
            print(f"Error in admin POST handler: {e}")
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            response = {'success': False, 'error': str(e)}
            self.wfile.write(json.dumps(response).encode('utf-8'))
    
    def do_DELETE(self):
        try:
            admin_id = self.path.split('/')[-1]
            
            response = supabase.table("admins").delete().eq("id", admin_id).execute()
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            response_data = {'success': True}
            self.wfile.write(json.dumps(response_data).encode('utf-8'))
            
        except Exception as e:
            print(f"Error in admin DELETE handler: {e}")
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            response = {'success': False, 'error': str(e)}
            self.wfile.write(json.dumps(response).encode('utf-8'))
