from http.server import BaseHTTPRequestHandler
import json
import os
import sys

sys.path.append(os.path.dirname(__file__))

try:
    from supabase_client import supabase
    from health import log_error
except ImportError:
    pass

class Handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Telegram-Id')
        self.end_headers()

    def do_POST(self):
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data)
            telegram_id = self.headers.get('Telegram-Id', '')
            action = data.get('action')
            code = data.get('confirmation_code')

            if not action or not code:
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'success': False, 'error': 'No data'}).encode('utf-8'))
                return

            res = {'success': False, 'error': 'Unknown action'}
            
            if action == 'reset_orders':
                r = supabase.table("orders").delete().neq("id", 0).execute()
                res = {'success': True, 'message': f'Удалено заказов: {len(r.data) if r.data else 0}'}
            elif action == 'reset_stats':
                res = {'success': True, 'message': 'Статистика сброшена'}
            elif action == 'delete_promocodes':
                r = supabase.table("promocodes").delete().neq("id", 0).execute()
                res = {'success': True, 'message': f'Удалено промокодов: {len(r.data) if r.data else 0}'}
            elif action == 'delete_products':
                r = supabase.table("products").delete().neq("id", 0).execute()
                res = {'success': True, 'message': f'Удалено товаров: {len(r.data) if r.data else 0}'}
            elif action == 'clear_customers':
                r = supabase.table("customers").delete().neq("id", 0).execute()
                res = {'success': True, 'message': f'Удалено клиентов: {len(r.data) if r.data else 0}'}
            elif action == 'reset_shop':
                r1 = supabase.table("orders").delete().neq("id", 0).execute()
                r2 = supabase.table("products").delete().neq("id", 0).execute()
                r3 = supabase.table("promocodes").delete().neq("id", 0).execute()
                r4 = supabase.table("customers").delete().neq("id", 0).execute()
                res = {'success': True, 'message': 'Магазин полностью очищен'}

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(res).encode('utf-8'))

        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({'success': False, 'error': str(e)}).encode('utf-8'))
