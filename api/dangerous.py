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
            
            print(f"⚠️ Dangerous action requested: {action} by {telegram_id}")
            self.log_action("dangerous_request_start", telegram_id, f"Action: {action}")
            
            admin_response = supabase.table("admins").select("role,id,first_name").eq("telegram_id", telegram_id).eq("is_active", True).execute()
            is_owner = admin_response.data and admin_response.data[0].get('role') == 'owner'
            
            print(f"⚠️ Admin check - Is owner: {is_owner}, Role: {admin_response.data[0].get('role') if admin_response.data else 'No data'}")
            self.log_action("admin_check", telegram_id, f"Is owner: {is_owner}, Role: {admin_response.data[0].get('role') if admin_response.data else 'No data'}")
            
            if not is_owner:
                print("❌ Access denied - user is not owner")
                self.log_action("access_denied", telegram_id, "User is not owner")
                self.send_response(403)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                response = {'success': False, 'error': 'Access denied. Only owners can perform dangerous actions.'}
                self.wfile.write(json.dumps(response).encode('utf-8'))
                return
            
            code_response = supabase.table("confirmation_codes").select("*").eq("code", confirmation_code).eq("is_active", True).execute()
            print(f"⚠️ Code validation - Found: {len(code_response.data)} codes")
            
            if not code_response.data:
                print("❌ Invalid confirmation code")
                self.log_action("invalid_code", telegram_id, f"Code: {confirmation_code}")
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                response = {'success': False, 'error': 'Invalid confirmation code'}
                self.wfile.write(json.dumps(response).encode('utf-8'))
                return
            
            print("✅ Code validated successfully")
            self.log_action("code_validated", telegram_id, f"Action: {action}, Code: {confirmation_code}")
            
            if action == 'reset_orders':
                print("🗑️ Deleting all orders...")
                self.log_action("deleting_orders", telegram_id, "Starting orders deletion")
                result = supabase.table("orders").delete().neq("id", 0).execute()
                deleted_count = len(result.data) if result.data else 0
                print(f"🗑️ Deleted {deleted_count} orders")
                self.log_action("orders_deleted", telegram_id, f"Deleted {deleted_count} orders")
                response_data = {'success': True, 'message': f'All orders deleted ({deleted_count} records)'}
                
            elif action == 'reset_stats':
                print("📊 Resetting statistics...")
                self.log_action("resetting_stats", telegram_id, "Starting stats reset")
                update_result = supabase.table("orders").update({"profit": 0}).neq("id", 0).execute()
                delete_result = supabase.table("customer_stats").delete().neq("id", 0).execute()
                print("📊 Statistics reset completed")
                self.log_action("stats_reset", telegram_id, "Statistics reset completed")
                response_data = {'success': True, 'message': 'All statistics reset successfully'}
                
            elif action == 'delete_promocodes':
                print("🏷️ Deleting all promocodes...")
                self.log_action("deleting_promocodes", telegram_id, "Starting promocodes deletion")
                result = supabase.table("promocodes").delete().neq("id", 0).execute()
                deleted_count = len(result.data) if result.data else 0
                print(f"🏷️ Deleted {deleted_count} promocodes")
                self.log_action("promocodes_deleted", telegram_id, f"Deleted {deleted_count} promocodes")
                response_data = {'success': True, 'message': f'All promocodes deleted ({deleted_count} records)'}
                
            elif action == 'delete_products':
                print("📦 Deleting all products...")
                self.log_action("deleting_products", telegram_id, "Starting products deletion")
                result = supabase.table("products").delete().neq("id", 0).execute()
                deleted_count = len(result.data) if result.data else 0
                print(f"📦 Deleted {deleted_count} products")
                self.log_action("products_deleted", telegram_id, f"Deleted {deleted_count} products")
                response_data = {'success': True, 'message': f'All products deleted ({deleted_count} records)'}
                
            elif action == 'clear_customers':
                print("👥 Clearing all customers...")
                self.log_action("clearing_customers", telegram_id, "Starting customers clearance")
                result = supabase.table("customers").delete().neq("id", 0).execute()
                deleted_count = len(result.data) if result.data else 0
                print(f"👥 Cleared {deleted_count} customers")
                self.log_action("customers_cleared", telegram_id, f"Cleared {deleted_count} customers")
                response_data = {'success': True, 'message': f'All customers deleted ({deleted_count} records)'}
                
            elif action == 'reset_shop':
                print("💥 Resetting entire shop...")
                self.log_action("resetting_shop", telegram_id, "Starting full shop reset")
                
                orders_result = supabase.table("orders").delete().neq("id", 0).execute()
                products_result = supabase.table("products").delete().neq("id", 0).execute()
                promocodes_result = supabase.table("promocodes").delete().neq("id", 0).execute()
                customers_result = supabase.table("customers").delete().neq("id", 0).execute()
                
                deleted_orders = len(orders_result.data) if orders_result.data else 0
                deleted_products = len(products_result.data) if products_result.data else 0
                deleted_promocodes = len(promocodes_result.data) if promocodes_result.data else 0
                deleted_customers = len(customers_result.data) if customers_result.data else 0
                
                print(f"💥 Reset completed: {deleted_orders} orders, {deleted_products} products, {deleted_promocodes} promocodes, {deleted_customers} customers")
                self.log_action("shop_reset", telegram_id, f"Reset completed: {deleted_orders} orders, {deleted_products} products, {deleted_promocodes} promocodes, {deleted_customers} customers")
                response_data = {'success': True, 'message': f'Shop completely reset: {deleted_orders} orders, {deleted_products} products, {deleted_promocodes} promocodes, {deleted_customers} customers deleted'}
                
            else:
                print(f"❌ Unknown action: {action}")
                self.log_action("unknown_action", telegram_id, f"Unknown action: {action}")
                response_data = {'success': False, 'error': 'Unknown action'}
            
            print(f"✅ Dangerous action completed: {action}")
            self.log_action("dangerous_action_completed", telegram_id, f"Action: {action}, Success: {response_data.get('success', False)}")
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(response_data).encode('utf-8'))
            
        except Exception as e:
            error_msg = f"Dangerous action failed: {str(e)}"
            print(f"❌ {error_msg}")
            self.log_action("dangerous_action_error", telegram_id, error_msg)
            log_error("dangerous_operations", e, self.headers.get('Telegram-Id', ''), f"Action: {action}")
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            response = {'success': False, 'error': str(e)}
            self.wfile.write(json.dumps(response).encode('utf-8'))
    
    def log_action(self, action, user_id, details):
        try:
            timestamp = datetime.now().isoformat()
            log_data = {
                'timestamp': timestamp,
                'module': 'dangerous',
                'action': action,
                'user_id': user_id,
                'details': str(details)
            }
            print(f"⚠️ DANGEROUS_ACTION: {json.dumps(log_data, ensure_ascii=False)}")
        except Exception as e:
            print(f"❌ Failed to log dangerous action: {e}")
