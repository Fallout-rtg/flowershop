from http.server import BaseHTTPRequestHandler
import json
import os
import requests
import sys
import traceback
from datetime import datetime
import time

sys.path.append(os.path.dirname(__file__))

try:
    from supabase_client import supabase
except ImportError as e:
    supabase = None

OWNER_ID = "2032240231"

class HealthMonitor:
    def __init__(self):
        self.bot_token = os.environ.get('BOT_TOKEN')
        self.owner_id = OWNER_ID
        self.errors = []
        self.warnings = []
        self.info = []
    
    def log_error(self, module, error, details=None):
        error_data = {
            'module': module,
            'error': str(error),
            'details': details,
            'timestamp': datetime.now().isoformat(),
            'traceback': traceback.format_exc()
        }
        self.errors.append(error_data)
        self.send_immediate_alert(error_data)
    
    def log_warning(self, module, warning, details=None):
        warning_data = {
            'module': module,
            'warning': str(warning),
            'details': details,
            'timestamp': datetime.now().isoformat()
        }
        self.warnings.append(warning_data)
    
    def log_info(self, module, info, details=None):
        info_data = {
            'module': module,
            'info': str(info),
            'details': details,
            'timestamp': datetime.now().isoformat()
        }
        self.info.append(info_data)
    
    def send_immediate_alert(self, error_data):
        try:
            if not self.bot_token:
                return
            
            message = f"🚨 *CRITICAL ERROR*\n\n"
            message += f"*Module:* `{error_data['module']}`\n"
            message += f"*Error:* `{error_data['error']}`\n"
            message += f"*Time:* {error_data['timestamp']}\n"
            
            if error_data.get('details'):
                message += f"*Details:* {error_data['details']}\n"
            
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            payload = {
                'chat_id': self.owner_id,
                'text': message,
                'parse_mode': 'Markdown'
            }
            
            requests.post(url, json=payload, timeout=10)
        except Exception as e:
            print(f"Failed to send alert: {e}")
    
    def send_detailed_report(self, report_data):
        try:
            if not self.bot_token:
                return False
            
            message = self.format_report(report_data)
            
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            payload = {
                'chat_id': self.owner_id,
                'text': message,
                'parse_mode': 'Markdown',
                'disable_web_page_preview': True
            }
            
            response = requests.post(url, json=payload, timeout=10)
            return response.status_code == 200
        except Exception as e:
            print(f"Failed to send detailed report: {e}")
            return False
    
    def format_report(self, report_data):
        message = "🩺 *SYSTEM HEALTH REPORT*\n\n"
        
        status_emoji = "✅" if report_data['status'] == 'healthy' else "❌" if report_data['status'] == 'critical' else "⚠️"
        message += f"*Overall Status:* {status_emoji} {report_data['status'].upper()}\n"
        message += f"*Report Time:* {report_data['timestamp']}\n"
        message += f"*Duration:* {report_data['duration']:.2f}s\n\n"
        
        message += "*📊 CHECKS SUMMARY*\n"
        message += f"✅ Passed: {report_data['summary']['passed']}\n"
        message += f"⚠️ Warnings: {report_data['summary']['warnings']}\n"
        message += f"❌ Errors: {report_data['summary']['errors']}\n\n"
        
        if report_data['checks']:
            message += "*🔍 DETAILED CHECKS*\n"
            for check in report_data['checks']:
                emoji = "✅" if check['status'] == 'passed' else "⚠️" if check['status'] == 'warning' else "❌"
                message += f"{emoji} *{check['name']}*: {check['message']}\n"
                if check.get('details'):
                    message += f"   📝 `{check['details']}`\n"
            message += "\n"
        
        if report_data.get('recommendations'):
            message += "*💡 RECOMMENDATIONS*\n"
            for rec in report_data['recommendations']:
                message += f"• {rec}\n"
            message += "\n"
        
        message += f"*Server:* `{os.environ.get('VERCEL_REGION', 'Unknown')}`\n"
        message += f"*Environment:* `{os.environ.get('VERCEL_ENV', 'development')}`"
        
        return message
    
    def check_supabase_connection(self):
        try:
            if not supabase:
                return {'status': 'error', 'message': 'Supabase client not initialized'}
            
            start_time = time.time()
            response = supabase.table("products").select("count", count="exact").limit(1).execute()
            duration = time.time() - start_time
            
            if hasattr(response, 'count') or (hasattr(response, 'data') and response.data is not None):
                return {
                    'status': 'passed', 
                    'message': f'Connected successfully', 
                    'details': f'Response time: {duration:.3f}s'
                }
            else:
                return {'status': 'error', 'message': 'Invalid response from Supabase'}
                
        except Exception as e:
            return {'status': 'error', 'message': f'Connection failed: {str(e)}'}
    
    def check_database_tables(self):
        try:
            if not supabase:
                return {'status': 'error', 'message': 'Supabase client not initialized'}
            
            tables = ['products', 'orders', 'admins', 'shop_settings', 'shop_themes', 
                     'promocodes', 'confirmation_codes', 'order_statuses']
            missing_tables = []
            
            for table in tables:
                try:
                    supabase.table(table).select("id").limit(1).execute()
                except Exception:
                    missing_tables.append(table)
            
            if missing_tables:
                return {'status': 'warning', 'message': f'Missing tables: {len(missing_tables)}', 'details': ', '.join(missing_tables)}
            else:
                return {'status': 'passed', 'message': 'All tables accessible'}
                
        except Exception as e:
            return {'status': 'error', 'message': f'Table check failed: {str(e)}'}
    
    def check_bot_token(self):
        try:
            if not self.bot_token:
                return {'status': 'error', 'message': 'BOT_TOKEN not set'}
            
            url = f"https://api.telegram.org/bot{self.bot_token}/getMe"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('ok'):
                    return {'status': 'passed', 'message': f'Bot @{data["result"]["username"]} is active'}
                else:
                    return {'status': 'error', 'message': 'Invalid bot token'}
            else:
                return {'status': 'error', 'message': f'HTTP {response.status_code}'}
                
        except Exception as e:
            return {'status': 'error', 'message': f'Bot check failed: {str(e)}'}
    
    def check_api_endpoints(self):
        try:
            endpoints = [
                '/api/products',
                '/api/order', 
                '/api/admin',
                '/api/promocodes'
            ]
            
            base_url = os.environ.get('VERCEL_URL', 'https://flowershop-nine-ashy.vercel.app')
            if not base_url.startswith('http'):
                base_url = f'https://{base_url}'
            
            failed_endpoints = []
            
            for endpoint in endpoints:
                try:
                    response = requests.get(f"{base_url}{endpoint}", timeout=10)
                    if response.status_code >= 500:
                        failed_endpoints.append(f"{endpoint} ({response.status_code})")
                except Exception:
                    failed_endpoints.append(f"{endpoint} (Timeout)")
            
            if failed_endpoints:
                return {'status': 'warning', 'message': f'API issues: {len(failed_endpoints)}', 'details': ', '.join(failed_endpoints)}
            else:
                return {'status': 'passed', 'message': 'All endpoints responding'}
                
        except Exception as e:
            return {'status': 'error', 'message': f'API check failed: {str(e)}'}
    
    def check_critical_data(self):
        try:
            if not supabase:
                return {'status': 'error', 'message': 'Supabase client not initialized'}
            
            issues = []
            
            products = supabase.table("products").select("id", count="exact").eq("is_available", True).execute()
            if not products.count:
                issues.append("No available products")
            
            admins = supabase.table("admins").select("id", count="exact").eq("is_active", True).execute()
            if not admins.count:
                issues.append("No active admins")
            
            settings = supabase.table("shop_settings").select("key").execute()
            required_settings = ['shop_name', 'delivery_price', 'free_delivery_min', 'contacts']
            existing_keys = [s['key'] for s in settings.data]
            missing_settings = [s for s in required_settings if s not in existing_keys]
            
            if missing_settings:
                issues.append(f"Missing settings: {', '.join(missing_settings)}")
            
            if issues:
                return {'status': 'warning', 'message': f'Data issues: {len(issues)}', 'details': '; '.join(issues)}
            else:
                return {'status': 'passed', 'message': 'Critical data present'}
                
        except Exception as e:
            return {'status': 'error', 'message': f'Data check failed: {str(e)}'}
    
    def check_system_resources(self):
        try:
            import psutil
            issues = []
            
            cpu_percent = psutil.cpu_percent(interval=1)
            if cpu_percent > 80:
                issues.append(f"High CPU: {cpu_percent}%")
            
            memory = psutil.virtual_memory()
            if memory.percent > 85:
                issues.append(f"High memory: {memory.percent}%")
            
            disk = psutil.disk_usage('/')
            if disk.percent > 90:
                issues.append(f"Low disk: {disk.percent}%")
            
            if issues:
                return {'status': 'warning', 'message': f'Resource issues: {len(issues)}', 'details': '; '.join(issues)}
            else:
                return {'status': 'passed', 'message': 'Resources normal'}
                
        except ImportError:
            return {'status': 'warning', 'message': 'psutil not available', 'details': 'Resource monitoring disabled'}
        except Exception as e:
            return {'status': 'error', 'message': f'Resource check failed: {str(e)}'}
    
    def perform_complete_health_check(self):
        start_time = time.time()
        
        checks = [
            ('Bot Token', self.check_bot_token),
            ('Supabase Connection', self.check_supabase_connection),
            ('Database Tables', self.check_database_tables),
            ('API Endpoints', self.check_api_endpoints),
            ('Critical Data', self.check_critical_data),
            ('System Resources', self.check_system_resources)
        ]
        
        results = []
        for name, check_func in checks:
            try:
                result = check_func()
                result['name'] = name
                results.append(result)
            except Exception as e:
                results.append({
                    'name': name,
                    'status': 'error',
                    'message': f'Check crashed: {str(e)}'
                })
        
        passed = sum(1 for r in results if r['status'] == 'passed')
        warnings = sum(1 for r in results if r['status'] == 'warning')
        errors = sum(1 for r in results if r['status'] == 'error')
        
        overall_status = 'healthy' if errors == 0 else 'critical' if errors > 2 else 'degraded'
        
        report = {
            'status': overall_status,
            'timestamp': datetime.now().isoformat(),
            'duration': time.time() - start_time,
            'summary': {
                'passed': passed,
                'warnings': warnings,
                'errors': errors
            },
            'checks': results
        }
        
        recommendations = []
        if errors > 0:
            recommendations.append("Review error logs and fix critical issues")
        if warnings > 0:
            recommendations.append("Address warnings to improve system stability")
        if passed == len(checks):
            recommendations.append("System is healthy - consider adding monitoring alerts")
        
        if recommendations:
            report['recommendations'] = recommendations
        
        return report

health_monitor = HealthMonitor()

class Handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS, GET')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def do_GET(self):
        try:
            if self.path == '/health':
                report = health_monitor.perform_complete_health_check()
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                
                self.wfile.write(json.dumps(report).encode('utf-8'))
            else:
                self.send_response(404)
                self.end_headers()
                
        except Exception as e:
            health_monitor.log_error('health_monitor', e, 'GET request failed')
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': 'Health check failed'}).encode('utf-8'))
    
    def do_POST(self):
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data)
            
            action = data.get('action')
            
            if action == 'test':
                report = health_monitor.perform_complete_health_check()
                success = health_monitor.send_detailed_report(report)
                
                response_data = {
                    'success': success,
                    'report': report,
                    'message': 'Health check completed and report sent' if success else 'Health check completed but report failed to send'
                }
            elif action == 'alert':
                module = data.get('module', 'unknown')
                error = data.get('error', 'Unknown error')
                details = data.get('details')
                
                health_monitor.log_error(module, error, details)
                response_data = {'success': True, 'message': 'Alert logged and sent'}
            else:
                response_data = {'success': False, 'error': 'Unknown action'}
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(response_data).encode('utf-8'))
            
        except Exception as e:
            health_monitor.log_error('health_monitor', e, 'POST request failed')
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'success': False, 'error': str(e)}).encode('utf-8'))

def log_system_error(module, error, details=None):
    health_monitor.log_error(module, error, details)

def perform_health_check():
    return health_monitor.perform_complete_health_check()
