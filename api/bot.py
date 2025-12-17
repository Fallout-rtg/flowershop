from http.server import BaseHTTPRequestHandler
import json
import os
import requests
from datetime import datetime, timezone, timedelta

class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            update = json.loads(post_data)
            
            bot_token = os.environ.get('BOT_TOKEN')
            
            if 'message' in update:
                chat_id = update['message']['chat']['id']
                text = update['message'].get('text', '').strip()
                
                if text.startswith('/start'):
                    self.send_welcome_message(chat_id, bot_token, update)
                elif text.startswith('/stats'):
                    self.send_stats_message(chat_id, bot_token)
                elif text.startswith('/test'):
                    self.run_system_test(chat_id, bot_token)
                elif text.startswith('/catalog'):
                    self.send_catalog_message(chat_id, bot_token)
                else:
                    self.send_unknown_command(chat_id, bot_token)
            
            elif 'callback_query' in update:
                callback = update['callback_query']
                chat_id = callback['message']['chat']['id']
                data = callback['data']
                
                if data == 'about':
                    self.send_about_message(chat_id, bot_token)
                elif data == 'stats':
                    self.send_stats_message(chat_id, bot_token)
                elif data == 'system_check':
                    self.run_system_test(chat_id, bot_token)
                elif data == 'catalog':
                    self.send_catalog_message(chat_id, bot_token)
                
                requests.post(f"https://api.telegram.org/bot{bot_token}/answerCallbackQuery", 
                            json={'callback_query_id': callback['id']})
            
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'OK')
            
        except Exception as e:
            print(f"Error in bot handler: {e}")
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'OK')

    def get_shop_status(self):
        moscow_tz = timezone(timedelta(hours=3))
        now = datetime.now(moscow_tz)
        current_hour = now.hour
    
        if 9 <= current_hour < 20:
            return "✅ *Открыто* • Закроется в 20:00"
        else:
            if current_hour < 9:
                return "❌ *Закрыто* • Откроется в 9:00"
            else:
                return "❌ *Закрыто* • Откроется завтра в 9:00"

    def get_admin_name(self, chat_id):
        admin_names = {
            "2032240231": "Ахмад",
            "711090928": "Татьяна Сергеевна",
            "766109005": "Амина"
        }
        return admin_names.get(str(chat_id), "Администратор")

    def send_welcome_message(self, chat_id, bot_token, update):
        web_app_url = "https://flowershop-nine-ashy.vercel.app/"
        
        admin_ids = ["2032240231", "711090928", "766109005"]
        is_admin = str(chat_id) in admin_ids
        
        shop_status = self.get_shop_status()
        photo_url = "https://raw.githubusercontent.com/Fallout-rtg/flowershop/main/logo.jpg"
        
        if is_admin:
            admin_name = self.get_admin_name(chat_id)
            
            caption = f"""👋 *Здравствуйте, {admin_name}!*

👑 *Добро пожаловать в панель управления АртФлора*

*Доступные команды:*
/stats — статистика магазина
/test — проверка системы
/catalog — открыть каталог

{shop_status}

✨ Используйте кнопки ниже для быстрого доступа."""
            
            markup = {
                "inline_keyboard": [
                    [{
                        "text": "🌸 Открыть магазин цветов", 
                        "web_app": {"url": web_app_url}
                    }],
                    [
                        {"text": "📊 Статистика", "callback_data": "stats"},
                        {"text": "🔧 Проверить систему", "callback_data": "system_check"}
                    ],
                    [
                        {"text": "🛍️ Каталог", "callback_data": "catalog"}
                    ]
                ]
            }
            
        else:
            caption = f"""*АртФлора | цветы Ярославль*
*Цветы с доставкой по городу Ярославль* 🤍

🕐 *Ежедневно 9:00 — 20:00*

📍 *Адрес магазина:*
ул. Угличская, 4к1, Ярославль

📞 *Оформление заказа:*
• VK: https://vk.cc/cP6qOb
• По телефону: +7(999) 785-86-35
• FlowWow: https://vk.cc/cPrSev
• Яндекс.Еда: https://vk.cc/cPOF3z

*АртФлора — когда цветы становятся искусством!*

{shop_status}"""
            
            markup = {
                "inline_keyboard": [
                    [{
                        "text": "🌸 Открыть магазин цветов", 
                        "web_app": {"url": web_app_url}
                    }],
                    [
                        {"text": "📞 Поддержка", "url": "https://t.me/+79997858635"},
                        {"text": "ℹ️ О магазине", "callback_data": "about"}
                    ]
                ]
            }
        
        self.send_telegram_photo(chat_id, bot_token, photo_url, caption, markup)

    def send_about_message(self, chat_id, bot_token):
        shop_status = self.get_shop_status()
        photo_url = "https://raw.githubusercontent.com/Fallout-rtg/flowershop/main/logo.jpg"
        
        caption = f"""🏪 *О магазине АртФлора*

📍 *Наш адрес:*
ул. Угличская, 4к1, Ярославль

🕐 *Часы работы:*
Ежедневно 9:00 — 20:00

*АртФлора — это:*
• Свежие цветы от прямых поставщиков
• Быстрая доставка по Ярославлю
• Широкий ассортимент букетов и композиций
• Современный подход к флористике

🎉 *Работаем с 2025 года!*

{shop_status}"""
        
        self.send_telegram_photo(chat_id, bot_token, photo_url, caption)

    def send_catalog_message(self, chat_id, bot_token):
        web_app_url = "https://flowershop-nine-ashy.vercel.app/"
        photo_url = "https://raw.githubusercontent.com/Fallout-rtg/flowershop/main/logo.jpg"
        
        markup = {
            "inline_keyboard": [[
                {
                    "text": "🌸 Открыть каталог цветов",
                    "web_app": {"url": web_app_url}
                }
            ]]
        }
        
        caption = "Нажмите на кнопку ниже, чтобы открыть каталог цветов:"
        self.send_telegram_photo(chat_id, bot_token, photo_url, caption, markup)

    def send_stats_message(self, chat_id, bot_token):
        admin_ids = ["2032240231", "711090928", "766109005"]
        if str(chat_id) not in admin_ids:
            message = "❌ Эта команда доступна только администраторам."
            self.send_telegram_message(chat_id, bot_token, message)
            return
            
        try:
            import requests
            response = requests.get('https://flowershop-nine-ashy.vercel.app/api/admin/stats', timeout=10)
            
            if response.status_code == 200:
                stats = response.json()
                message = f"""📊 *Статистика магазина*

📦 Всего заказов: *{stats['total_orders']}*
✅ Завершено: *{stats['completed_orders']}*
💰 Реальная выручка: *{stats['total_revenue']} ₽*
💎 Потенциальная выручка: *{stats['potential_revenue']} ₽*
🛍️ Товаров в каталоге: *{stats['total_products']}*
🏷️ Активных промокодов: *{stats.get('active_promocodes', 0)}*"""
            else:
                message = "❌ Не удалось получить статистику. Попробуйте позже."
                
        except Exception as e:
            message = f"❌ Ошибка при получении статистики: {str(e)}"
        
        self.send_telegram_message(chat_id, bot_token, message)

    def run_system_test(self, chat_id, bot_token):
        admin_ids = ["2032240231", "711090928", "766109005"]
        if str(chat_id) not in admin_ids:
            message = "❌ Эта команда доступна только администраторам."
            self.send_telegram_message(chat_id, bot_token, message)
            return
            
        try:
            message = "🔄 *Запуск комплексной проверки системы...*\n\nПожалуйста, подождите 10-15 секунд..."
            self.send_telegram_message(chat_id, bot_token, message)
            
            headers = {'Telegram-Id': str(chat_id)}
            test_url = "https://flowershop-nine-ashy.vercel.app/api/health/test"
            response = requests.get(test_url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                message = "✅ *Проверка завершена!*\n\nПодробный отчёт отправлен вам в личные сообщения."
            else:
                message = "❌ *Ошибка при выполнении проверки!*\n\nСистема мониторинга недоступна."
            
            self.send_telegram_message(chat_id, bot_token, message)
            
        except Exception as e:
            error_message = f"❌ *Ошибка при запуске проверки:*\n`{str(e)}`"
            self.send_telegram_message(chat_id, bot_token, error_message)

    def send_unknown_command(self, chat_id, bot_token):
        message = "Извините, я не понимаю эту команду.\n\nДоступные команды:\n/start — начать работу\n/stats — статистика (админы)\n/test — проверка системы (админы)\n/catalog — каталог (админы)"
        self.send_telegram_message(chat_id, bot_token, message)

    def send_telegram_message(self, chat_id, bot_token, text, reply_markup=None):
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            'chat_id': chat_id,
            'text': text,
            'parse_mode': 'Markdown'
        }
        
        if reply_markup:
            payload['reply_markup'] = json.dumps(reply_markup)
            
        try:
            requests.post(url, json=payload, timeout=10)
        except Exception as e:
            print(f"Error sending Telegram message: {e}")

    def send_telegram_photo(self, chat_id, bot_token, photo_url, caption, reply_markup=None):
        url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
        payload = {
            'chat_id': chat_id,
            'photo': photo_url,
            'caption': caption[:1024],
            'parse_mode': 'Markdown'
        }
        
        if reply_markup:
            payload['reply_markup'] = json.dumps(reply_markup)
            
        try:
            response = requests.post(url, json=payload, timeout=10)
            if response.status_code != 200:
                print(f"Error sending photo: {response.text}")
                self.send_telegram_message(chat_id, bot_token, caption, reply_markup)
        except Exception as e:
            print(f"Error sending Telegram photo: {e}")
            self.send_telegram_message(chat_id, bot_token, caption, reply_markup)

    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b'Bot is running')
