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
            
            print(f"DANGEROUS ACTION: telegram_id={telegram_id}, action={action}, code={confirmation_code}")
            
            if not action or not confirmation_code:
                response_data = {'success': False, 'error': 'Missing action or confirmation code'}
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps(response_data).encode('utf-8'))
                return
            
            admin_response = supabase.table("admins").select("role,id,first_name").eq("telegram_id", telegram_id).eq("is_active", True).execute()
            is_owner = admin_response.data and admin_response.data[0].get('role') == 'owner'
            
            if not is_owner:
                response_data = {'success': False, 'error': 'Access denied. Only owners can perform dangerous actions.'}
                self.send_response(403)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps(response_data).encode('utf-8'))
                return
            
            code_response = supabase.table("confirmation_codes").select("*").eq("code", confirmation_code).eq("is_active", True).execute()
            
            if not code_response.data:
                response_data = {'success': False, 'error': 'Invalid confirmation code'}
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps(response_data).encode('utf-8'))
                return
            
            if action == 'reset_orders':
                result = supabase.table("orders").delete().neq("id", 0).execute()
                deleted_count = len(result.data) if result.data else 0
                response_data = {'success': True, 'message': f'Все заказы удалены ({deleted_count} записей)'}
            elif action == 'reset_stats':
                update_result = supabase.table("orders").update({"profit": 0}).neq("id", 0).execute()
                delete_result = supabase.table("customer_stats").delete().neq("id", 0).execute()
                response_data = {'success': True, 'message': 'Вся статистика сброшена'}
            elif action == 'delete_promocodes':
                result = supabase.table("promocodes").delete().neq("id", 0).execute()
                deleted_count = len(result.data) if result.data else 0
                response_data = {'success': True, 'message': f'Все промокоды удалены ({deleted_count} записей)'}
            elif action == 'delete_products':
                result = supabase.table("products").delete().neq("id", 0).execute()
                deleted_count = len(result.data) if result.data else 0
                response_data = {'success': True, 'message': f'Все товары удалены ({deleted_count} записей)'}
            elif action == 'clear_customers':
                result = supabase.table("customers").delete().neq("id", 0).execute()
                deleted_count = len(result.data) if result.data else 0
                response_data = {'success': True, 'message': f'Все клиенты удалены ({deleted_count} записей)'}
            elif action == 'reset_shop':
                orders_result = supabase.table("orders").delete().neq("id", 0).execute()
                products_result = supabase.table("products").delete().neq("id", 0).execute()
                promocodes_result = supabase.table("promocodes").delete().neq("id", 0).execute()
                customers_result = supabase.table("customers").delete().neq("id", 0).execute()
                deleted_orders = len(orders_result.data) if orders_result.data else 0
                deleted_products = len(products_result.data) if products_result.data else 0
                deleted_promocodes = len(promocodes_result.data) if promocodes_result.data else 0
                deleted_customers = len(customers_result.data) if customers_result.data else 0
                response_data = {'success': True, 'message': f'Магазин полностью сброшен: {deleted_orders} заказов, {deleted_products} товаров, {deleted_promocodes} промокодов, {deleted_customers} клиентов удалено'}
            else:
                response_data = {'success': False, 'error': 'Неизвестное действие'}
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(response_data).encode('utf-8'))
            
        except Exception as e:
            print(f"Error in dangerous action: {str(e)}")
            response_data = {'success': False, 'error': str(e)}
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(response_data).encode('utf-8'))
