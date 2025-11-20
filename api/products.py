from http.server import BaseHTTPRequestHandler
import json
import os
import sys

sys.path.append(os.path.dirname(__file__))

try:
    from supabase_client import supabase
except ImportError as e:
    print(f"Import error: {e}")

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            print("Fetching products from Supabase...")
            
            response = supabase.table("products").select("*").eq("is_available", True).execute()
            
            print(f"Supabase response: {response}")
            
            products = response.data
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            self.wfile.write(json.dumps(products).encode('utf-8'))
            
        except Exception as e:
            print(f"Error in products handler: {e}")
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            # Полные fallback данные
            fallback_products = [
                {
                    "id": 1,
                    "name": "Букет из 25 красных роз",
                    "price": 3500,
                    "image_url": "https://s.widget-club.com/images/YyiR86zpwIMIfrCZoSs4ulVD9RF3/1a4e33422efdd0fbf0c2af3394a67b13/ab18ec0a91069208210a71ac46ce9176.jpg",
                    "category": "roses",
                    "description": "Роскошные красные розы в элегантной упаковке",
                    "fact": "Красные розы символизируют глубокую любовь и страсть. В Древнем Риме они были символом Венеры - богини любви.",
                    "is_available": True
                },
                {
                    "id": 2,
                    "name": "Весенний микс тюльпанов",
                    "price": 2200,
                    "image_url": "https://avatars.mds.yandex.net/i?id=a6a74bd671cd7b4288738a981e5ddeec_sr-5435996-images-thumbs&n=13",
                    "category": "tulips",
                    "description": "Разноцветные тюльпаны в плетеной корзине",
                    "fact": "Тюльпаны продолжают расти после срезки и могут вырасти на 2-3 см в вазе. В Голландии в 17 веке одна луковица тюльпана могла стоить как целый дом!",
                    "is_available": True
                },
                {
                    "id": 3,
                    "name": "Свадебный букет невесты",
                    "price": 5200,
                    "image_url": "https://img0.liveinternet.ru/images/attach/c/2/71/783/71783188_1299657661_lily_and_roses.jpg",
                    "category": "premium",
                    "description": "Белые розы, лилии и орхидеи для особого дня",
                    "fact": "Традиция свадебного букета зародилась в Древней Греции, где невесты носили гирлянды из цветов, символизирующие новую жизнь.",
                    "is_available": True
                },
                {
                    "id": 4,
                    "name": "Орхидея фаленопсис",
                    "price": 2900,
                    "image_url": "https://avatars.mds.yandex.net/i?id=67103fa9353694d0cde953b11caf366ad4270819-5290060-images-thumbs&n=13",
                    "category": "orchids",
                    "description": "Элегантная белая орхидея в керамическом горшке",
                    "fact": "Орхидеи - одно из самых многочисленных семейств растений, насчитывающее около 25,000 видов. Некоторые виды могут жить до 100 лет!",
                    "is_available": True
                },
                {
                    "id": 5,
                    "name": "Романтический сюрприз",
                    "price": 4200,
                    "image_url": "https://avatars.mds.yandex.net/i?id=7ef2fb3eaae443b8b1e5ba1e49125931_l-4988204-images-thumbs&n=13",
                    "category": "roses",
                    "description": "Красные розы с шоколадом и открыткой",
                    "fact": "Аромат роз может поднимать настроение и снижать стресс. В древности лепестки роз использовали для украшения банкетных залов и постелей новобрачных.",
                    "is_available": True
                },
                {
                    "id": 6,
                    "name": "Тюльпаны радуга",
                    "price": 1800,
                    "image_url": "https://img.freepik.com/premium-photo/rainbow-tulips-white-foyer-colorful-flower-theme-spring-generative-ai_132375-18140.jpg",
                    "category": "tulips",
                    "description": "Пять цветов тюльпанов в одной композиции",
                    "fact": "Тюльпаны бывают практически всех цветов радуги, кроме синего. Существует около 3,000 сортов тюльпанов, официально зарегистрированных по всему миру.",
                    "is_available": True
                }
            ]
            
            self.wfile.write(json.dumps(fallback_products).encode('utf-8'))
