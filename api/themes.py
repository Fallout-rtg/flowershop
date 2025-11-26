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
            path = self.path
            telegram_id = self.headers.get('Telegram-Id', '').strip()
            
            self.log_action("themes_GET", telegram_id, f"Path: {path}")
            
            if '/themes' in path:
                response = supabase.table("shop_themes").select("*").order("id").execute()
                self.log_action("themes_GET_success", telegram_id, f"Retrieved {len(response.data)} themes")
                self.send_success_response(response.data)
            else:
                self.send_error_response(404, 'Endpoint not found')
                
        except Exception as e:
            error_msg = f"Failed to fetch themes: {str(e)}"
            self.log_action("themes_GET_error", telegram_id, error_msg)
            log_error("themes_GET", e, telegram_id, f"Path: {path}")
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
                success = self.set_active_theme(data['theme_id'], telegram_id)
                if success:
                    self.send_success_response({'theme_id': data['theme_id'], 'active': True})
                else:
                    self.send_error_response(400, 'Failed to activate theme')
            elif 'pattern' in data:
                success = self.set_active_pattern(data['pattern'], telegram_id)
                if success:
                    self.send_success_response({'pattern': data['pattern'], 'active': True})
                else:
                    self.send_error_response(400, 'Failed to activate pattern')
            elif 'effect' in data:
                success = self.set_active_effect(data['effect'], telegram_id)
                if success:
                    self.send_success_response({'effect': data['effect'], 'active': True})
                else:
                    self.send_error_response(400, 'Failed to activate effect')
            else:
                self.send_error_response(400, 'Invalid request data')
                
        except Exception as e:
            error_msg = f"Failed to update theme settings: {str(e)}"
            self.log_action("themes_PUT_error", telegram_id, error_msg)
            log_error("themes_PUT", e, telegram_id, f"Update data: {data}")
            self.send_error_response(500, error_msg)
    
    def do_POST(self):
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data)
            
            telegram_id = self.headers.get('Telegram-Id', '').strip()
            
            self.log_action("themes_POST", telegram_id, f"Data: {data}")
            
            if not self.is_admin(telegram_id):
                self.send_error_response(403, 'Access denied')
                return
            
            if 'theme_data' in data:
                success = self.create_theme(data['theme_data'], telegram_id)
                if success:
                    self.send_success_response({'message': 'Theme created successfully'})
                else:
                    self.send_error_response(400, 'Failed to create theme')
            else:
                self.send_error_response(400, 'Missing theme_data')
                
        except Exception as e:
            error_msg = f"Failed to create theme: {str(e)}"
            self.log_action("themes_POST_error", telegram_id, error_msg)
            log_error("themes_POST", e, telegram_id, f"Data: {data}")
            self.send_error_response(500, error_msg)
    
    def is_admin(self, telegram_id):
        try:
            if not telegram_id:
                self.log_action("admin_check_failed", telegram_id, "No telegram_id provided")
                return False
            
            response = supabase.table("admins").select("role,is_active").eq("telegram_id", telegram_id).execute()
            
            if not response.data:
                self.log_action("admin_check_failed", telegram_id, "No admin record found")
                return False
            
            admin = response.data[0]
            is_admin = admin.get('is_active', False) and admin.get('role') in ['admin', 'owner']
            
            self.log_action("admin_check", telegram_id, f"Admin status: {is_admin}, Role: {admin.get('role')}, Active: {admin.get('is_active')}")
            return is_admin
            
        except Exception as e:
            self.log_action("admin_check_error", telegram_id, f"Error: {str(e)}")
            log_error("admin_check", e, telegram_id, "Admin check failed")
            return False
    
    def set_active_theme(self, theme_id, telegram_id):
        try:
            self.log_action("set_active_theme_start", telegram_id, f"Theme ID: {theme_id}")
            
            theme_response = supabase.table("shop_themes").select("id,name,background_value").eq("id", theme_id).execute()
            
            if not theme_response.data:
                self.log_action("set_active_theme_failed", telegram_id, f"Theme {theme_id} not found in database")
                return False
            
            theme = theme_response.data[0]
            self.log_action("set_active_theme_found", telegram_id, f"Theme found: {theme['name']} - {theme['background_value']}")
            
            deactivate_result = supabase.table("shop_themes").update({"is_active": False}).neq("id", 0).execute()
            self.log_action("set_active_theme_deactivated", telegram_id, f"Deactivated other themes")
            
            activate_result = supabase.table("shop_themes").update({"is_active": True}).eq("id", theme_id).execute()
            self.log_action("set_active_theme_activated", telegram_id, f"Activated theme {theme_id}")
            
            existing_settings = supabase.table("shop_settings").select("*").eq("key", "active_theme").execute()
            
            if existing_settings.data:
                update_result = supabase.table("shop_settings").update({"value": {"value": str(theme_id)}}).eq("key", "active_theme").execute()
                self.log_action("set_active_theme_updated", telegram_id, f"Updated existing theme setting")
            else:
                insert_result = supabase.table("shop_settings").insert({
                    "key": "active_theme", 
                    "value": {"value": str(theme_id)}
                }).execute()
                self.log_action("set_active_theme_created", telegram_id, f"Created new theme setting")
            
            self.log_action("set_active_theme_success", telegram_id, f"Theme {theme_id} ({theme['name']}) activated successfully")
            return True
            
        except Exception as e:
            self.log_action("set_active_theme_error", telegram_id, f"Error: {str(e)}")
            log_error("set_active_theme", e, telegram_id, f"Theme ID: {theme_id}")
            return False
    
    def set_active_pattern(self, pattern, telegram_id):
        try:
            self.log_action("set_active_pattern_start", telegram_id, f"Pattern: {pattern}")
            
            valid_patterns = ["dots", "lines", "flowers", "none"]
            if pattern not in valid_patterns:
                self.log_action("set_active_pattern_invalid", telegram_id, f"Invalid pattern: {pattern}")
                return False
            
            existing = supabase.table("shop_settings").select("*").eq("key", "header_patterns").execute()
            
            patterns_data = {
                "active": pattern,
                "patterns": valid_patterns
            }
            
            if existing.data:
                update_result = supabase.table("shop_settings").update({"value": patterns_data}).eq("key", "header_patterns").execute()
                self.log_action("set_active_pattern_updated", telegram_id, f"Updated pattern to {pattern}")
            else:
                insert_result = supabase.table("shop_settings").insert({
                    "key": "header_patterns", 
                    "value": patterns_data
                }).execute()
                self.log_action("set_active_pattern_created", telegram_id, f"Created pattern setting: {pattern}")
            
            self.log_action("set_active_pattern_success", telegram_id, f"Pattern {pattern} activated successfully")
            return True
            
        except Exception as e:
            self.log_action("set_active_pattern_error", telegram_id, f"Error: {str(e)}")
            log_error("set_active_pattern", e, telegram_id, f"Pattern: {pattern}")
            return False

    def set_active_effect(self, effect, telegram_id):
        try:
            self.log_action("set_active_effect_start", telegram_id, f"Effect: {effect}")
            
            valid_effects = ["snow", "rain", "none"]
            if effect not in valid_effects:
                self.log_action("set_active_effect_invalid", telegram_id, f"Invalid effect: {effect}")
                return False
            
            existing = supabase.table("shop_settings").select("*").eq("key", "active_effect").execute()
            
            effect_data = {"value": effect}
            
            if existing.data:
                update_result = supabase.table("shop_settings").update({"value": effect_data}).eq("key", "active_effect").execute()
                self.log_action("set_active_effect_updated", telegram_id, f"Updated effect to {effect}")
            else:
                insert_result = supabase.table("shop_settings").insert({
                    "key": "active_effect", 
                    "value": effect_data
                }).execute()
                self.log_action("set_active_effect_created", telegram_id, f"Created effect setting: {effect}")
            
            self.log_action("set_active_effect_success", telegram_id, f"Effect {effect} activated successfully")
            return True
            
        except Exception as e:
            self.log_action("set_active_effect_error", telegram_id, f"Error: {str(e)}")
            log_error("set_active_effect", e, telegram_id, f"Effect: {effect}")
            return False

    def create_theme(self, theme_data, telegram_id):
        try:
            self.log_action("create_theme_start", telegram_id, f"Theme data: {theme_data}")
            
            required_fields = ['name', 'background_value']
            for field in required_fields:
                if field not in theme_data:
                    self.log_action("create_theme_failed", telegram_id, f"Missing required field: {field}")
                    return False
            
            response = supabase.table("shop_themes").insert(theme_data).execute()
            
            if response.data:
                self.log_action("create_theme_success", telegram_id, f"Theme created with ID: {response.data[0]['id']}")
                return True
            else:
                self.log_action("create_theme_failed", telegram_id, "No data returned from insert")
                return False
                
        except Exception as e:
            self.log_action("create_theme_error", telegram_id, f"Error: {str(e)}")
            log_error("create_theme", e, telegram_id, f"Theme data: {theme_data}")
            return False
    
    def log_action(self, action, user_id, details):
        try:
            timestamp = datetime.now().isoformat()
            log_data = {
                'timestamp': timestamp,
                'module': 'themes',
                'action': action,
                'user_id': user_id,
                'details': str(details)
            }
            print(f"THEME_ACTION: {json.dumps(log_data, ensure_ascii=False)}")
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
