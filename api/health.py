from http.server import BaseHTTPRequestHandler
import json
import os
import requests
import sys
import traceback
from datetime import datetime
import time
import html

sys.path.append(os.path.dirname(__file__))

try:
    from supabase_init import supabase
except ImportError as e:
    supabase = None
    print(f"Supabase import error: {e}")

ADMIN_CHAT_IDS = ["2032240231]

class Handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def do_GET(self):
        try:
            if self.path == '/test' or self.path == '/api/health/test':
                initiator_chat_id = self.headers.get('Telegram-Id', '')
                report = self.run_comprehensive_test()
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                
                self.wfile.write(json.dumps(report).encode('utf-8'))
                
                if initiator_chat_id and initiator_chat_id in ADMIN_CHAT_IDS:
                    bot_token = os.environ.get('BOT_TOKEN')
                    self.send_test_report_to_admins(report, bot_token, initiator_chat_id)
            else:
                self.send_response(404)
                self.end_headers()
                
        except Exception as e:
            self.send_error_response(f"Health GET error: {str(e)}")
    
    def do_POST(self):
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            error_data = json.loads(post_data)
            
            self.log_error_to_admins(error_data)
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            response = {'success': True, 'message': 'Error logged'}
            self.wfile.write(json.dumps(response).encode('utf-8'))
            
        except Exception as e:
            self.send_error_response(f"Health POST error: {str(e)}")
    
    def run_comprehensive_test(self):
        test_report = {
            'timestamp': datetime.now().isoformat(),
            'overall_status': 'unknown',
            'services': {},
            'errors': [],
            'warnings': [],
            'statistics': {}
        }
        
        try:
            bot_token = os.environ.get('BOT_TOKEN')
            
            test_report['services']['environment'] = self.test_environment_variables()
            test_report['services']['supabase'] = self.test_supabase_connection()
            test_report['services']['telegram_api'] = self.test_telegram_api(bot_token)
            test_report['services']['api_endpoints'] = self.test_api_endpoints()
            test_report['services']['database_tables'] = self.test_database_tables()
            test_report['statistics'] = self.get_system_statistics()
            
            failed_services = [service for service, status in test_report['services'].items() 
                             if status.get('status') == 'error']
            
            if failed_services:
                test_report['overall_status'] = 'error'
                test_report['errors'].append(f"Critical services failed: {', '.join(failed_services)}")
            elif any('warning' in service.get('status', '') for service in test_report['services'].values()):
                test_report['overall_status'] = 'warning'
            else:
                test_report['overall_status'] = 'healthy'
            
        except Exception as e:
            test_report['overall_status'] = 'error'
            test_report['errors'].append(f"Test execution failed: {str(e)}")
            traceback_str = traceback.format_exc()
            test_report['errors'].append(f"Traceback: {traceback_str}")
        
        return test_report
    
    def test_environment_variables(self):
        result = {'status': 'healthy', 'details': {}}
        required_vars = ['SUPABASE_URL', 'SUPABASE_KEY', 'BOT_TOKEN']
        
        for var in required_vars:
            if os.environ.get(var):
                result['details'][var] = '✓ Найдено'
            else:
                result['details'][var] = '✗ Отсутствует'
                result['status'] = 'error'
        
        return result
    
    def test_supabase_connection(self):
        result = {'status': 'healthy', 'details': {}}
        
        if not supabase:
            result['status'] = 'error'
            result['details']['connection'] = '✗ Клиент Supabase не инициализирован'
            return result
        
        try:
            start_time = time.time()
            response = supabase.table("products").select("count", count="exact").limit(1).execute()
            response_time = round((time.time() - start_time) * 1000, 2)
            
            result['details']['connection'] = '✓ Успешно'
            result['details']['response_time'] = f'{response_time}ms'
            
            if hasattr(response, 'count'):
                result['details']['products_count'] = response.count
            else:
                result['details']['products_count'] = len(response.data) if response.data else 0
                
        except Exception as e:
            result['status'] = 'error'
            result['details']['connection'] = f'✗ Ошибка: {str(e)}'
        
        return result
    
    def test_telegram_api(self, bot_token):
        result = {'status': 'healthy', 'details': {}}
        
        if not bot_token:
            result['status'] = 'error'
            result['details']['connection'] = '✗ BOT_TOKEN не установлен'
            return result
        
        try:
            url = f"https://api.telegram.org/bot{bot_token}/getMe"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                result['details']['connection'] = '✓ Успешно'
                result['details']['bot_username'] = data['result']['username']
                result['details']['bot_name'] = data['result']['first_name']
                
                test_message = "✅ Бот активен и может отправлять сообщения"
                success = self.send_telegram_message(ADMIN_CHAT_IDS[0], bot_token, test_message, parse_mode='HTML')
                if success:
                    result['details']['message_permission'] = '✓ Может отправлять сообщения'
                else:
                    result['details']['message_permission'] = '✗ Не может отправлять сообщения'
                    result['status'] = 'warning'
                    
            else:
                result['status'] = 'error'
                result['details']['connection'] = f'✗ HTTP {response.status_code}'
                
        except Exception as e:
            result['status'] = 'error'
            result['details']['connection'] = f'✗ Ошибка: {str(e)}'
        
        return result
    
    def test_api_endpoints(self):
        result = {'status': 'healthy', 'details': {}}
        base_url = "https://flowershop-nine-ashy.vercel.app"
        endpoints = [
            '/api/products',
            '/api/admin',
            '/api/order',
            '/api/promocodes'
        ]
        
        for endpoint in endpoints:
            try:
                start_time = time.time()
                response = requests.get(f"{base_url}{endpoint}", timeout=10)
                response_time = round((time.time() - start_time) * 1000, 2)
                
                if response.status_code == 200:
                    result['details'][endpoint] = f'✓ 200 OK ({response_time}ms)'
                else:
                    result['details'][endpoint] = f'✗ HTTP {response.status_code}'
                    result['status'] = 'warning'
                    
            except Exception as e:
                result['details'][endpoint] = f'✗ Ошибка: {str(e)}'
                result['status'] = 'warning'
        
        return result
    
    def test_database_tables(self):
        result = {'status': 'healthy', 'details': {}}
        
        if not supabase:
            result['status'] = 'error'
            result['details']['overall'] = '✗ Supabase недоступен'
            return result
        
        tables = ['products', 'orders', 'admins', 'shop_settings', 'shop_themes', 'promocodes', 'order_statuses', 'categories']
        
        for table in tables:
            try:
                response = supabase.table(table).select("id", count="exact").limit(1).execute()
                
                count = len(response.data) if response.data else 0
                result['details'][table] = f'✓ Доступна ({count} записей)'
                    
            except Exception as e:
                result['details'][table] = f'✗ Ошибка: {str(e)}'
                result['status'] = 'error'
        
        return result
    
    def get_system_statistics(self):
        stats = {}
        
        try:
            if supabase:
                products = supabase.table("products").select("id", count="exact").execute()
                orders = supabase.table("orders").select("id", count="exact").execute()
                admins = supabase.table("admins").select("id", count="exact").execute()
                
                stats['total_products'] = len(products.data) if products.data else 0
                stats['total_orders'] = len(orders.data) if orders.data else 0
                stats['active_admins'] = len(admins.data) if admins.data else 0
            
            stats['server_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            stats['python_version'] = sys.version.split()[0]
            
        except Exception as e:
            stats['error'] = f"Failed to get statistics: {str(e)}"
        
        return stats
    
    def log_error_to_admins(self, error_data):
        try:
            bot_token = os.environ.get('BOT_TOKEN')
            if not bot_token:
                print("BOT_TOKEN not available for error logging")
                return
            
            timestamp = error_data.get('timestamp', datetime.now().isoformat())
            module = error_data.get('module', 'unknown')
            error_message = error_data.get('error', 'No error message')
            user_id = error_data.get('user_id', 'unknown')
            additional_info = error_data.get('additional_info', '')
            
            message = f"""🚨 <b>Ошибка в системе</b>

📋 <b>Модуль:</b> {html.escape(module)}
⏰ <b>Время:</b> {html.escape(timestamp)}
👤 <b>Пользователь:</b> {html.escape(user_id)}

❌ <b>Ошибка:</b>
<code>{html.escape(error_message)}</code>

📝 <b>Дополнительно:</b>
{html.escape(additional_info)}

🔧 <b>Требуется вмешательство!</b>"""
            
            for chat_id in ADMIN_CHAT_IDS:
                self.send_telegram_message(chat_id, bot_token, message, parse_mode='HTML')
            
        except Exception as e:
            print(f"Failed to log error to admins: {e}")
    
    def send_test_report_to_admins(self, report, bot_token, initiator_chat_id):
        try:
            for chat_id in ADMIN_CHAT_IDS:
                if str(chat_id) == str(initiator_chat_id):
                    continue
                self.send_single_report(chat_id, bot_token, report)
                
        except Exception as e:
            print(f"❌ Failed to send test report to admins: {e}")
    
    def send_single_report(self, chat_id, bot_token, report):
        try:
            status_emoji = {
                'healthy': '✅',
                'warning': '⚠️', 
                'error': '❌',
                'unknown': '❓'
            }
            
            emoji = status_emoji.get(report['overall_status'], '❓')
            
            message = f"""{emoji} <b>Отчёт о состоянии системы</b>

📊 <b>Общий статус:</b> {html.escape(report['overall_status'].upper())}
⏰ <b>Время проверки:</b> {html.escape(report['timestamp'])}

<b>Проверка сервисов:</b>
"""
            
            for service, data in report['services'].items():
                status = data.get('status', 'unknown')
                service_emoji = status_emoji.get(status, '❓')
                message += f"{service_emoji} <b>{html.escape(service.upper())}</b>: {html.escape(status)}\n"
                
                for detail, value in data.get('details', {}).items():
                    message += f"  └ {html.escape(detail)}: {html.escape(str(value))}\n"
            
            if report['errors']:
                message += "\n<b>❌ Критические ошибки:</b>\n"
                for error in report['errors']:
                    message += f"• {html.escape(error)}\n"
            
            if report['warnings']:
                message += "\n<b>⚠️ Предупреждения:</b>\n"
                for warning in report['warnings']:
                    message += f"• {html.escape(warning)}\n"
            
            message += f"\n<b>📈 Статистика:</b>\n"
            for stat, value in report['statistics'].items():
                message += f"• {html.escape(stat)}: {html.escape(str(value))}\n"
            
            success = self.send_telegram_message(chat_id, bot_token, message, parse_mode='HTML')
            
            if not success:
                print(f"❌ Failed to send report to {chat_id}")
            else:
                print(f"✅ Report sent successfully to {chat_id}")
                
            return success
            
        except Exception as e:
            print(f"❌ Failed to send test report: {e}")
            return False
    
    def send_telegram_message(self, chat_id, bot_token, text, parse_mode=None):
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            'chat_id': chat_id,
            'text': text,
            'disable_web_page_preview': True
        }
        
        if parse_mode:
            payload['parse_mode'] = parse_mode
        
        try:
            response = requests.post(url, json=payload, timeout=10)
            
            if response.status_code == 200:
                return True
            else:
                error_data = response.json()
                
                if response.status_code == 403:
                    print(f"❌ Bot doesn't have permission to send messages to {chat_id}")
                elif response.status_code == 400:
                    print(f"❌ Bad request: {error_data.get('description', 'Unknown error')}")
                
                return False
        except Exception as e:
            print(f"❌ Failed to send Telegram message: {e}")
            return False
    
    def send_error_response(self, error_message):
        self.send_response(500)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        response = {'success': False, 'error': error_message}
        self.wfile.write(json.dumps(response).encode('utf-8'))

def log_error(module, error, user_id='unknown', additional_info=''):
    try:
        error_data = {
            'timestamp': datetime.now().isoformat(),
            'module': module,
            'error': str(error),
            'user_id': str(user_id),
            'additional_info': additional_info
        }
        
        requests.post(
            'https://flowershop-nine-ashy.vercel.app/api/health',
            json=error_data,
            timeout=5
        )
    except Exception as e:
        print(f"Failed to send error to health monitor: {e}")
