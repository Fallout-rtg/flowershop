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
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def do_GET(self):
        try:
            response = supabase.table("products").select("*").eq("is_available", True).order("sort_order").execute()
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
            
            fallback_products = [
                {
                    "id": 1,
                    "name": "Букет из 25 красных роз",
                    "price": 3500,
                    "image_url": "https://s.widget-club.com/images/YyiR86zpwIMIfrCZoSs4ulVD9RF3/1a4e33422efdd0fbf0c2af3394a67b13/ab18ec0a91069208210a71ac46ce9176.jpg",
                    "category": "roses",
                    "description": "Роскошные красные розы в элегантной упаковке",
                    "fact": "Красные розы символизируют глубокую любовь и страсть. В Древнем Риме они были символом Венеры - богини любви.",
                    "is_available": True,
                    "is_featured": True,
                    "sort_order": 1
                }
            ]
            
            self.wfile.write(json.dumps(fallback_products).encode('utf-8'))
    
    def do_POST(self):
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            product_data = json.loads(post_data)
            
            required_fields = ['name', 'price', 'category']
            for field in required_fields:
                if field not in product_data or not product_data[field]:
                    self.send_response(400)
                    self.send_header('Content-type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    response = {'success': False, 'error': f'Missing required field: {field}'}
                    self.wfile.write(json.dumps(response).encode('utf-8'))
                    return
            
            if 'is_available' not in product_data:
                product_data['is_available'] = True
            
            if 'is_featured' not in product_data:
                product_data['is_featured'] = False
            
            max_order_response = supabase.table("products").select("sort_order").order("sort_order", desc=True).limit(1).execute()
            max_order = max_order_response.data[0]['sort_order'] if max_order_response.data else 0
            product_data['sort_order'] = max_order + 1
            
            response = supabase.table("products").insert(product_data).execute()
            
            if not response.data:
                raise Exception("No data returned from insert operation")
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            response_data = {'success': True, 'product': response.data[0]}
            self.wfile.write(json.dumps(response_data).encode('utf-8'))
            
        except Exception as e:
            print(f"Error in products POST handler: {e}")
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            response = {'success': False, 'error': str(e)}
            self.wfile.write(json.dumps(response).encode('utf-8'))
    
    def do_PUT(self):
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data)
            
            if 'reorder' in data:
                products_order = data['products_order']
                for product_id, sort_order in products_order.items():
                    supabase.table("products").update({"sort_order": sort_order}).eq("id", int(product_id)).execute()
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                
                response_data = {'success': True}
                self.wfile.write(json.dumps(response_data).encode('utf-8'))
            else:
                product_data = data
                product_id = product_data.get('id')
                if not product_id:
                    raise ValueError("Product ID is required")
                
                update_data = {k: v for k, v in product_data.items() if k != 'id'}
                response = supabase.table("products").update(update_data).eq("id", product_id).execute()
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                
                response_data = {'success': True, 'product': response.data[0] if response.data else None}
                self.wfile.write(json.dumps(response_data).encode('utf-8'))
            
        except Exception as e:
            print(f"Error in products PUT handler: {e}")
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            response = {'success': False, 'error': str(e)}
            self.wfile.write(json.dumps(response).encode('utf-8'))
    
    def do_DELETE(self):
        try:
            path_parts = self.path.split('/')
            product_id = path_parts[-1] if path_parts[-1] else path_parts[-2]
            
            if not product_id.isdigit():
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                response = {'success': False, 'error': 'Invalid product ID'}
                self.wfile.write(json.dumps(response).encode('utf-8'))
                return
            
            response = supabase.table("products").delete().eq("id", int(product_id)).execute()
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            response_data = {'success': True}
            self.wfile.write(json.dumps(response_data).encode('utf-8'))
            
        except Exception as e:
            print(f"Error in products DELETE handler: {e}")
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            response = {'success': False, 'error': str(e)}
            self.wfile.write(json.dumps(response).encode('utf-8'))
