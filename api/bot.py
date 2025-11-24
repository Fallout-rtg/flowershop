from http.server import BaseHTTPRequestHandler
import json
import os
import requests

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
                    self.send_welcome_message(chat_id, bot_token)
                elif text.startswith('/help'):
                    self.send_help_message(chat_id, bot_token)
                elif text.startswith('/catalog'):
                    self.send_catalog_message(chat_id, bot_token)
                elif text.startswith('/test'):
                    self.run_system_test(chat_id, bot_token)
                elif text.startswith('/stats'):
                    self.send_stats_message(chat_id, bot_token)
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

    def send_welcome_message(self, chat_id, bot_token):
        web_app_url = "https://flowershop-nine-ashy.vercel.app/"
        
        admin_ids = ["2032240231", "711090928", "766109005"]
        is_admin = str(chat_id) in admin_ids
        
        if is_admin:
            markup = {
                "inline_keyboard": [
                    [{
                        "text": "🌸 Открыть магазин цветов", 
                        "web_app": {"url": web_app_url}
                    }],
                    [
                        {"text": "🛠 Панель управления", "web_app": {"url": web_app_url}},
                        {"text": "📊 Статистика", "callback_data": "stats"}
                    ],
                    [
                        {"text": "🔧 Проверить систему", "callback_data": "system_check"},
                        {"text": "📞 Поддержка", "url": "https://t.me/Fallout_RTG"}
                    ],
                    [
                        {"text": "🛍️ Каталог", "callback_data": "catalog"},
                        {"text": "ℹ️ Помощь", "callback_data": "help"}
                    ]
                ]
            }
            
            message = """👑 *Добро пожаловать, администратор!*

✨ *Доступные функции управления:*
• 🛠 Полное управление магазином через WebApp
• 📊 Просмотр статистики и аналитики в реальном времени
• 🔧 Проверка состояния системы и диагностика
• ⚙️ Настройки магазина, темы и промокоды
• 👥 Управление администраторами и правами доступа

*Быстрые команды:*
/stats - Получить текущую статистику
/test - Запустить проверку системы
/catalog - Открыть каталог товаров
/help - Получить справку

Используйте кнопки ниже для быстрого доступа к функциям управления."""
        else:
            markup = {
                "inline_keyboard": [
                    [{
                        "text": "🌸 Открыть магазин цветов", 
                        "web_app": {"url": web_app_url}
                    }],
                    [
                        {"text": "📞 Поддержка", "url": "https://t.me/Fallout_RTG"},
                        {"text": "ℹ️ О магазине", "callback_data": "about"}
                    ]
                ]
            }
            
            message = "🌸 *Добро пожаловать в магазин элитных цветов!*\n\n✨ У нас вы найдете:\n• Свежие цветы от проверенных поставщиков\n• Быструю доставку по Ярославлю  \n• Индивидуальный подход к каждому заказу\n\nНажмите на кнопку ниже, чтобы открыть каталог и сделать заказ!"
        
        self.send_telegram_message(chat_id, bot_token, message, markup)

    def send_about_message(self, chat_id, bot_token):
        message = "🏪 *О нашем магазине*\n\nМы - цветочный магазин с многолетним опытом работы. \nНаши преимущества:\n• Свежие цветы от проверенных поставщиков\n• Быстрая доставка по Ярославлю\n• Индивидуальный подход к каждому клиенту\n\nРаботаем для вас с 2010 года!"
        
        self.send_telegram_message(chat_id, bot_token, message)

    def send_help_message(self, chat_id, bot_token):
        admin_ids = ["2032240231", "711090928", "766109005"]
        is_admin = str(chat_id) in admin_ids
        
        if is_admin:
            message = """🛠 *Помощь для администраторов*

*Основные команды:*
/start - начать работу с ботом
/help - получить помощь
/stats - просмотреть статистику
/test - проверить состояние системы
/catalog - открыть каталог товаров

*Панель управления:*
Для полного доступа к функциям управления используйте WebApp через кнопку 'Панель управления'

*Быстрые действия через кнопки:*
• 📊 Статистика - текущие показатели магазина
• 🔧 Проверка системы - диагностика всех сервисов
• 🛍️ Каталог - быстрый доступ к товарам"""
        else:
            message = "🛠 *Помощь по боту*\n\n*Основные команды:*\n/start - начать работу с ботом\n/help - получить помощь\n\n*Как сделать заказ:*\n1. Нажмите кнопку «Открыть магазин цветов»\n2. Выберите понравившиеся букеты\n3. Оформите заказ в корзине\n4. Укажите ваш телефон для связи\n\n*Доставка:* \n🏙️ По Ярославлю - бесплатно от 3000₽\n⏱ В течение 2-х часов"
        
        self.send_telegram_message(chat_id, bot_token, message)

    def send_catalog_message(self, chat_id, bot_token):
        web_app_url = "https://flowershop-nine-ashy.vercel.app/"
        
        markup = {
            "inline_keyboard": [[
                {
                    "text": "🌸 Открыть каталог цветов",
                    "web_app": {"url": web_app_url}
                }
            ]]
        }
        
        message = "Нажмите на кнопку ниже, чтобы открыть наш каталог цветов:"
        self.send_telegram_message(chat_id, bot_token, message, markup)

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
        message = "Извините, я не понимаю эту команду. Используйте /help для списка доступных команд."
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

    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b'Bot is running')
