from http.server import BaseHTTPRequestHandler
import json
import os
import sys
from datetime import datetime

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
            telegram_id = self.headers.get('Telegram-Id', '')
            
            admin_response = supabase.table("admins").select("role").eq("telegram_id", telegram_id).eq("is_active", True).execute()
            is_owner = admin_response.data and admin_response.data[0].get('role') == 'owner'
            
            if not is_owner:
                self.send_response(403)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                response = {'success': False, 'error': 'Access denied'}
                self.wfile.write(json.dumps(response).encode('utf-8'))
                return
            
            response = supabase.table("promocodes").select("*").order("created_at", desc=True).execute()
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(response.data).encode('utf-8'))
            
        except Exception as e:
            print(f"Error in promocodes GET: {e}")
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
            
            telegram_id = self.headers.get('Telegram-Id', '')
            
            admin_response = supabase.table("admins").select("role,id").eq("telegram_id", telegram_id).eq("is_active", True).execute()
            is_owner = admin_response.data and admin_response.data[0].get('role') == 'owner'
            
            if not is_owner:
                self.send_response(403)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                response = {'success': False, 'error': 'Only owners can create promocodes'}
                self.wfile.write(json.dumps(response).encode('utf-8'))
                return
            
            if data.get('action') == 'validate':
                code = data.get('code')
                order_amount = data.get('order_amount', 0)
                
                promocode_response = supabase.table("promocodes").select("*").eq("code", code).eq("is_active", True).execute()
                
                if not promocode_response.data:
                    response_data = {'valid': False, 'error': 'Promocode not found'}
                else:
                    promocode = promocode_response.data[0]
                    now = datetime.now().isoformat()
                    
                    if promocode.get('valid_until') and promocode['valid_until'] < now:
                        response_data = {'valid': False, 'error': 'Promocode expired'}
                    elif promocode.get('max_uses') and promocode.get('used_count', 0) >= promocode['max_uses']:
                        response_data = {'valid': False, 'error': 'Promocode usage limit reached'}
                    elif promocode.get('min_order_amount', 0) > order_amount:
                        response_data = {'valid': False, 'error': f'Minimum order amount: {promocode["min_order_amount"]}₽'}
                    else:
                        discount_amount = 0
                        if promocode['discount_type'] == 'percentage':
                            discount_amount = int(order_amount * promocode['discount_value'] / 100)
                        else:
                            discount_amount = promocode['discount_value']
                        
                        response_data = {
                            'valid': True,
                            'discount_amount': discount_amount,
                            'promocode_id': promocode['id'],
                            'discount_type': promocode['discount_type'],
                            'discount_value': promocode['discount_value']
                        }
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps(response_data).encode('utf-8'))
                
            else:
                promocode_data = {
                    'code': data['code'],
                    'discount_type': data['discount_type'],
                    'discount_value': data['discount_value'],
                    'min_order_amount': data.get('min_order_amount', 0),
                    'max_uses': data.get('max_uses'),
                    'valid_from': data.get('valid_from'),
                    'valid_until': data.get('valid_until'),
                    'created_by': admin_response.data[0]['id']
                }
                
                response = supabase.table("promocodes").insert(promocode_data).execute()
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                response_data = {'success': True, 'promocode': response.data[0] if response.data else None}
                self.wfile.write(json.dumps(response_data).encode('utf-8'))
                
        except Exception as e:
            print(f"Error in promocodes POST: {e}")
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            response = {'success': False, 'error': str(e)}
            self.wfile.write(json.dumps(response).encode('utf-8'))
    
    def do_DELETE(self):
        try:
            telegram_id = self.headers.get('Telegram-Id', '')
            
            admin_response = supabase.table("admins").select("role").eq("telegram_id", telegram_id).eq("is_active", True).execute()
            is_owner = admin_response.data and admin_response.data[0].get('role') == 'owner'
            
            if not is_owner:
                self.send_response(403)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                response = {'success': False, 'error': 'Access denied'}
                self.wfile.write(json.dumps(response).encode('utf-8'))
                return
            
            path_parts = self.path.split('/')
            promocode_id = path_parts[-1] if path_parts[-1] else path_parts[-2]
            
            response = supabase.table("promocodes").delete().eq("id", promocode_id).execute()
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            response_data = {'success': True}
            self.wfile.write(json.dumps(response_data).encode('utf-8'))
            
        except Exception as e:
            print(f"Error in promocodes DELETE: {e}")
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            response = {'success': False, 'error': str(e)}
            self.wfile.write(json.dumps(response).encode('utf-8'))
