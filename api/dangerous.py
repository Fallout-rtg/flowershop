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
            
            response_data = {'success': False, 'error': 'Unknown action'}
            
            if action == 'reset_orders':
                result = supabase.table("orders").delete().neq("id", 0).execute()
                deleted_count = len(result.data) if result.data else 0
                response_data = {'success': True, 'message': f'Удалено {deleted_count} заказов!'}
            elif action == 'reset_stats':
                response_data = {'success': True, 'message': 'Статистика сброшена!'}
            elif action == 'delete_promocodes':
                result = supabase.table("promocodes").delete().neq("id", 0).execute()
                deleted_count = len(result.data) if result.data else 0
                response_data = {'success': True, 'message': f'Удалено {deleted_count} промокодов!'}
            elif action == 'delete_products':
                result = supabase.table("products").delete().neq("id", 0).execute()
                deleted_count = len(result.data) if result.data else 0
                response_data = {'success': True, 'message': f'Удалено {deleted_count} товаров!'}
            elif action == 'clear_customers':
                result = supabase.table("customers").delete().neq("id", 0).execute()
                deleted_count = len(result.data) if result.data else 0
                response_data = {'success': True, 'message': f'Удалено {deleted_count} клиентов!'}
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
            print(f"DANGEROUS ACTION SUCCESS: {action}, Response: {response_data}")
            
        except Exception as e:
            print(f"Error in dangerous action: {str(e)}")
            log_error("dangerous_POST", e, telegram_id, f"Action: {action}, Code: {confirmation_code}")
            response_data = {'success': False, 'error': str(e)}
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(response_data).encode('utf-8'))
