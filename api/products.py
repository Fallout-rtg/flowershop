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
            
            # Для supabase 1.0.3 используем такой синтаксис
            response = supabase.table("products").select("*").eq("is_available", True).execute()
            
            print(f"Supabase response: {response}")
            
            # В версии 1.0.3 данные в response.data
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
            
            # Fallback данные
            fallback_products = [
                {
                    "id": 1,
                    "name": "Букет из 25 красных роз",
                    "price": 3500,
                    "image_url": "https://s.widget-club.com/images/YyiR86zpwIMIfrCZoSs4ulVD9RF3/1a4e33422efdd0fbf0c2af3394a67b13/ab18ec0a91069208210a71ac46ce9176.jpg",
                    "category": "roses",
                    "description": "Роскошные красные розы в элегантной упаковке",
                    "fact": "Красные розы символизируют глубокую любовь и страсть",
                    "is_available": True
                },
                {
                    "id": 2,
                    "name": "Весенний микс тюльпанов",
                    "price": 2200,
                    "image_url": "https://avatars.mds.yandex.net/i?id=a6a74bd671cd7b4288738a981e5ddeec_sr-5435996-images-thumbs&n=13",
                    "category": "tulips",
                    "description": "Разноцветные тюльпаны в плетеной корзине",
                    "fact": "Тюльпаны продолжают расти после срезки",
                    "is_available": True
                }
            ]
            
            self.wfile.write(json.dumps(fallback_products).encode('utf-8'))
