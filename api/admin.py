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
            print(f"Error in admin POST handler: {e}")
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
            
            if 'theme_id' in data:
                theme_id = data['theme_id']
                supabase.table("shop_themes").update({"is_active": False}).neq("id", 0).execute()
                supabase.table("shop_themes").update({"is_active": True}).eq("id", theme_id).execute()
                
                supabase.table("shop_settings").upsert({
                    "key": "active_theme",
                    "value": {"value": str(theme_id)}
                }).execute()
                
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
            print(f"Error in admin PUT handler: {e}")
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            response = {'success': False, 'error': str(e)}
            self.wfile.write(json.dumps(response).encode('utf-8'))
    
    def do_DELETE(self):
        try:
            path_parts = self.path.split('/')
            resource_id = path_parts[-1] if path_parts[-1] else path_parts[-2]
            
            if 'admin' in self.path:
                response = supabase.table("admins").delete().eq("id", resource_id).execute()
            elif 'order' in self.path:
                response = supabase.table("orders").delete().eq("id", resource_id).execute()
            else:
                raise ValueError("Unknown resource")
            
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
