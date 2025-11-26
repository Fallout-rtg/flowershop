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
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def do_GET(self):
        try:
            telegram_id = self.headers.get('Telegram-Id', '').strip()
            
            self.log_action("themes_GET", telegram_id, f"Path: {self.path}")
            
            if not self.is_admin(telegram_id):
                self.send_error_response(403, 'Access denied')
                return
            
            response = supabase.table("shop_themes").select("*").order("id").execute()
            self.send_success_response(response.data)
                
        except Exception as e:
            error_msg = f"Failed to fetch themes: {str(e)}"
            log_error("themes_GET", e, telegram_id, f"Path: {self.path}")
            self.send_error_response(500, error_msg)
    
    def do_PUT(self):
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data)
            
            telegram_id = self.headers.get('Telegram-Id', '').strip()
            
            self.log_action("themes_PUT", telegram_id, f"Update data: {data}")
            
            if not self.is_admin(telegram_id):
                self.send_error_response(403, 'Access denied')
                return
            
            if 'theme_id' in data:
                theme_id = data['theme_id']
                self.set_active_theme(theme_id, telegram_id)
            elif 'pattern' in data:
                pattern = data['pattern']
                self.set_active_pattern(pattern, telegram_id)
            elif 'effect' in data:
                effect = data['effect']
                self.set_active_effect(effect, telegram_id)
            else:
                self.send_error_response(400, 'Invalid request')
                
        except Exception as e:
            error_msg = f"Failed to update theme: {str(e)}"
            log_error("themes_PUT", e, telegram_id, f"Update data: {data}")
            self.send_error_response(500, error_msg)
    
    def is_admin(self, telegram_id):
        try:
            if not telegram_id:
                return False
            
            response = supabase.table("admins").select("role,is_active").eq("telegram_id", telegram_id).execute()
            return (response.data and 
                    response.data[0].get('is_active', False) and 
                    response.data[0].get('role') in ['admin', 'owner'])
        except Exception as e:
            log_error("admin_check", e, telegram_id, "Admin check failed")
            return False
    
    def set_active_theme(self, theme_id, telegram_id):
        try:
            theme_response = supabase.table("shop_themes").select("id").eq("id", theme_id).execute()
            if not theme_response.data:
                self.send_error_response(404, 'Theme not found')
                return
            
            supabase.table("shop_themes").update({"is_active": False}).neq("id", 0).execute()
            supabase.table("shop_themes").update({"is_active": True}).eq("id", theme_id).execute()
            
            existing = supabase.table("shop_settings").select("*").eq("key", "active_theme").execute()
            if existing.data:
                supabase.table("shop_settings").update({"value": {"value": str(theme_id)}}).eq("key", "active_theme").execute()
            else:
                supabase.table("shop_settings").insert({
                    "key": "active_theme", 
                    "value": {"value": str(theme_id)}
                }).execute()
            
            self.log_action("theme_activated", telegram_id, f"Theme ID: {theme_id}")
            self.send_success_response({'theme_id': theme_id, 'active': True})
            
        except Exception as e:
            raise e
    
    def set_active_pattern(self, pattern, telegram_id):
        try:
            existing = supabase.table("shop_settings").select("*").eq("key", "header_patterns").execute()
            patterns_data = {
                "active": pattern,
                "patterns": ["dots", "lines", "flowers"]
            }
            
            if existing.data:
                supabase.table("shop_settings").update({"value": patterns_data}).eq("key", "header_patterns").execute()
            else:
                supabase.table("shop_settings").insert({
                    "key": "header_patterns", 
                    "value": patterns_data
                }).execute()
            
            self.log_action("pattern_activated", telegram_id, f"Pattern: {pattern}")
            self.send_success_response({'pattern': pattern, 'active': True})
            
        except Exception as e:
            raise e

    def set_active_effect(self, effect, telegram_id):
        try:
            existing = supabase.table("shop_settings").select("*").eq("key", "active_effect").execute()
            
            if existing.data:
                supabase.table("shop_settings").update({"value": {"value": effect}}).eq("key", "active_effect").execute()
            else:
                supabase.table("shop_settings").insert({
                    "key": "active_effect", 
                    "value": {"value": effect}
                }).execute()
            
            self.log_action("effect_activated", telegram_id, f"Effect: {effect}")
            self.send_success_response({'effect': effect, 'active': True})
            
        except Exception as e:
            raise e
    
    def log_action(self, action, user_id, details):
        try:
            log_data = {
                'timestamp': datetime.now().isoformat(),
                'module': 'themes',
                'action': action,
                'user_id': user_id,
                'details': details
            }
            print(f"THEME_ACTION: {json.dumps(log_data)}")
        except Exception as e:
            print(f"Failed to log theme action: {e}")
    
    def send_success_response(self, data):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        response = {'success': True, 'data': data}
        self.wfile.write(json.dumps(response).encode('utf-8'))
    
    def send_error_response(self, code, message):
        self.send_response(code)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        response = {'success': False, 'error': message}
        self.wfile.write(json.dumps(response).encode('utf-8'))
