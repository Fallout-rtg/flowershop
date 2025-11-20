from http.server import BaseHTTPRequestHandler
import json
from supabase_client import supabase

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            response = supabase.table("products")\
                .select("*")\
                .eq("is_available", True)\
                .execute()
            
            products = response.data
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            self.wfile.write(json.dumps(products).encode('utf-8'))
            
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            error_response = {'error': 'Failed to fetch products'}
            self.wfile.write(json.dumps(error_response).encode('utf-8'))
