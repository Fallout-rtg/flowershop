from http.server import BaseHTTPRequestHandler
import json
import os
import requests
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
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def do_POST(self):
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            notification_data = json.loads(post_data)
            
            user_id = notification_data.get('user_id')
            message = notification_data.get('message')
            notification_type = notification_data.get('type', 'info')
            
            success = self.send_telegram_notification(user_id, message)
            
            if success:
                notification_record = {
                    "user_id": user_id,
                    "type": notification_type,
                    "title": "Уведомление",
                    "message": message,
                    "is_sent": True
                }
                supabase.table("notifications").insert(notification_record).execute()
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            response = {'success': success}
            self.wfile.write(json.dumps(response).encode('utf-8'))
            
        except Exception as e:
            print(f"Error in notifications handler: {e}")
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            response = {'success': False, 'error': str(e)}
            self.wfile.write(json.dumps(response).encode('utf-8'))
    
    def send_telegram_notification(self, user_id, message):
        try:
            bot_token = os.environ.get('BOT_TOKEN')
            
            if not bot_token:
                print("Missing BOT_TOKEN")
                return False

            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            payload = {
                'chat_id': user_id,
                'text': message,
                'parse_mode': 'Markdown'
            }
            
            response = requests.post(url, json=payload, timeout=10)
            return response.status_code == 200
            
        except Exception as e:
            print(f"Error sending Telegram notification: {e}")
            return False
