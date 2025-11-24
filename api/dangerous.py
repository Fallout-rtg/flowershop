from http.server import BaseHTTPRequestHandler
import json
import os
import sys

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
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def do_POST(self):
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data)
            
            telegram_id = self.headers.get('Telegram-Id', '')
            action = data.get('action')
            confirmation_code = data.get('confirmation_code')
            
            admin_response = supabase.table("admins").select("role").eq("telegram_id", telegram_id).eq("is_active", True).execute()
            is_owner = admin_response.data and admin_response.data[0].get('role') == 'owner'
            
            if not is_owner:
                self.send_response(403)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                response = {'success': False, 'error': 'Access denied. Only owners can perform dangerous actions.'}
                self.wfile.write(json.dumps(response).encode('utf-8'))
                return
            
            code_response = supabase.table("confirmation_codes").select("*").eq("code", confirmation_code).eq("is_active", True).execute()
            
            if not code_response.data:
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                response = {'success': False, 'error': 'Invalid confirmation code'}
                self.wfile.write(json.dumps(response).encode('utf-8'))
                return
            
            if action == 'reset_orders':
                result = supabase.table("orders").delete().neq("id", 0).execute()
                response_data = {'success': True, 'message': f'All orders deleted ({len(result.data) if result.data else 0} records)'}
                
            elif action == 'reset_stats':
                update_result = supabase.table("orders").update({"profit": 0}).neq("id", 0).execute()
                delete_result = supabase.table("customer_stats").delete().neq("id", 0).execute()
                response_data = {'success': True, 'message': 'All statistics reset successfully'}
                
            elif action == 'delete_promocodes':
                result = supabase.table("promocodes").delete().neq("id", 0).execute()
                response_data = {'success': True, 'message': f'All promocodes deleted ({len(result.data) if result.data else 0} records)'}
                
            elif action == 'delete_products':
                result = supabase.table("products").delete().neq("id", 0).execute()
                response_data = {'success': True, 'message': f'All products deleted ({len(result.data) if result.data else 0} records)'}
                
            elif action == 'clear_customers':
                result = supabase.table("customers").delete().neq("id", 0).execute()
                response_data = {'success': True, 'message': f'All customers deleted ({len(result.data) if result.data else 0} records)'}
                
            else:
                response_data = {'success': False, 'error': 'Unknown action'}
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(response_data).encode('utf-8'))
            
        except Exception as e:
            log_error("dangerous_operations", e, self.headers.get('Telegram-Id', ''), f"Action: {action}")
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            response = {'success': False, 'error': str(e)}
            self.wfile.write(json.dumps(response).encode('utf-8'))
