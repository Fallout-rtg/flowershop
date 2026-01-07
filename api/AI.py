# AI.py
import os
import json
from flask import Blueprint, request, jsonify
import requests

ai_bp = Blueprint('ai', __name__)

# Конфигурация OpenRouter
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY', '')
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "deepseek/deepseek-r1-0528:free"

def get_ai_response(prompt, context=""):
    """
    Отправляет запрос к DeepSeek через OpenRouter
    """
    if not OPENROUTER_API_KEY:
        return {"error": "OpenRouter API ключ не настроен"}
    
    # Системный промт с контекстом магазина цветов
    system_prompt = f"""You are an AI assistant for a flower shop called "АртФлора". 
You help with questions about flowers, bouquets, orders, delivery, and shop management.
You should always respond in Russian language.
Shop context: {context}

Instructions:
1. Always respond in Russian
2. Be helpful, friendly and professional
3. If asked about specific flowers, provide accurate information
4. For order-related questions, guide users to proper procedures
5. For administrative questions, provide guidance on using the admin panel
6. Keep responses concise but informative
7. If you don't know something, admit it politely"""

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://artflora.vercel.app",
        "X-Title": "АртФлора Цветочный Магазин"
    }

    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 1000
    }

    try:
        response = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            if 'choices' in result and len(result['choices']) > 0:
                return {
                    "success": True,
                    "response": result['choices'][0]['message']['content'].strip()
                }
            else:
                return {"error": "Пустой ответ от AI"}
        else:
            return {"error": f"Ошибка API: {response.status_code}", "details": response.text}
    
    except requests.exceptions.Timeout:
        return {"error": "Таймаут запроса к AI"}
    except Exception as e:
        return {"error": f"Ошибка: {str(e)}"}

@ai_bp.route('/api/ai/chat', methods=['POST'])
def ai_chat():
    """
    Обработчик чата с AI
    """
    try:
        data = request.json
        user_message = data.get('message', '').strip()
        context = data.get('context', 'Цветочный магазин "АртФлора"')
        
        if not user_message:
            return jsonify({"error": "Пустое сообщение"}), 400
        
        # Получаем ответ от AI
        ai_response = get_ai_response(user_message, context)
        
        if "error" in ai_response:
            return jsonify(ai_response), 500
        
        return jsonify(ai_response)
    
    except Exception as e:
        return jsonify({"error": f"Ошибка сервера: {str(e)}"}), 500

@ai_bp.route('/api/ai/status', methods=['GET'])
def ai_status():
    """
    Проверка статуса AI сервиса
    """
    return jsonify({
        "status": "online" if OPENROUTER_API_KEY else "offline",
        "model": MODEL,
        "service": "OpenRouter + DeepSeek R1"
    })
