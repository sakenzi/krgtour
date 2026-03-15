"""
AI Assistant app - Ollama integration for tourist recommendations.

Architecture:
    Django View <-> OllamaClient <-> Ollama REST API (http://localhost:11434)

The Ollama API is a local REST service running a LLaMA model.
We communicate via HTTP POST requests to /api/chat endpoint.
The system prompt injects Karaganda context for relevant responses.
"""

import json
import logging
import requests
from django.shortcuts import render
from django.http import JsonResponse, StreamingHttpResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings

from apps.routes.models import Route, Category
from apps.places.models import Place

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """Ты — AI-ассистент туристического портала Карагандинского региона Казахстана.
Твоя задача — помогать туристам планировать поездки, рекомендовать маршруты и места.

Ты знаешь о следующих типах маршрутов: пешие, велосипедные, автомобильные, исторические, природные.
Регион Карагандинской области включает: город Карагандa, Темиртау, Балхаш, Жезказган, 
природный заповедник Каркаралинск, горы Улытау, озеро Балхаш.

Отвечай на русском языке. Будь дружелюбным, информативным и полезным.
Если спрашивают о бронировании или конкретных маршрутах — направляй пользователя к соответствующим страницам сайта.
Максимальная длина ответа — 3-4 абзаца, если не нужно больше.
"""


class OllamaClient:
    """
    Client for communicating with local Ollama AI server.

    Ollama runs locally on port 11434 and exposes a REST API.
    We use the /api/chat endpoint for multi-turn conversations.

    Example request:
        POST http://localhost:11434/api/chat
        {
            "model": "llama3.2",
            "messages": [
                {"role": "system", "content": "..."},
                {"role": "user", "content": "Посоветуй маршрут"}
            ],
            "stream": false
        }
    """

    def __init__(self):
        self.base_url = settings.OLLAMA_BASE_URL
        self.model = settings.OLLAMA_MODEL
        self.timeout = settings.OLLAMA_TIMEOUT

    def chat(self, messages: list, context: str = '') -> str:
        """
        Send chat messages to Ollama and return the response.

        Args:
            messages: List of {role, content} dicts (conversation history)
            context: Additional context about routes/places to inject

        Returns:
            str: AI response text
        """
        system_content = SYSTEM_PROMPT
        if context:
            system_content += f'\n\nТекущий контекст сайта:\n{context}'

        full_messages = [
            {'role': 'system', 'content': system_content}
        ] + messages

        try:
            response = requests.post(
                f'{self.base_url}/api/chat',
                json={
                    'model': self.model,
                    'messages': full_messages,
                    'stream': False,
                    'options': {
                        'temperature': 0.7,
                        'num_predict': 512,
                    }
                },
                timeout=self.timeout,
            )

            response.raise_for_status()
            data = response.json()
            return data['message']['content']

        except requests.exceptions.ConnectionError:
            logger.error('Cannot connect to Ollama at %s', self.base_url)
            return (
                'К сожалению, AI-ассистент временно недоступен. '
                'Пожалуйста, попробуйте позже или обратитесь к нам напрямую.'
            )
        except requests.exceptions.Timeout:
            logger.error('Ollama request timed out')
            return 'Запрос занял слишком много времени. Попробуйте задать более короткий вопрос.'
        except Exception as e:
            logger.error('Ollama error: %s', str(e))
            return 'Произошла ошибка при обработке запроса.'

    def is_available(self) -> bool:
        """Check if Ollama server is running."""
        try:
            response = requests.get(f'{self.base_url}/api/tags', timeout=5)
            return response.status_code == 200
        except Exception:
            return False


def get_routes_context() -> str:
    """Build context string with current routes for AI."""
    routes = Route.objects.filter(status='active').values(
        'title', 'difficulty', 'distance_km', 'duration_hours', 'price', 'slug'
    )[:20]

    context_lines = ['Доступные маршруты на сайте:']
    for r in routes:
        difficulty_map = {'easy': 'лёгкий', 'medium': 'средний', 'hard': 'сложный', 'expert': 'экстрим'}
        price_str = f"{int(r['price'])} ₸" if r['price'] else 'бесплатно'
        line = (
            f"- {r['title']} | "
            f"Сложность: {difficulty_map.get(r['difficulty'], r['difficulty'])} | "
            f"Дистанция: {r['distance_km']} км | "
            f"Длительность: {r['duration_hours']} ч | "
            f"Цена: {price_str} | "
            f"URL: /routes/{r['slug']}/"
        )
        context_lines.append(line)

    return '\n'.join(context_lines)


# Singleton client instance
ollama_client = OllamaClient()


def assistant_view(request):
    """AI assistant chat page."""
    is_available = ollama_client.is_available()
    return render(request, 'ai_assistant/chat.html', {
        'is_available': is_available,
        'model': settings.OLLAMA_MODEL,
    })


@require_POST
def chat_api(request):
    """
    AJAX endpoint for AI chat.

    Request body (JSON):
        {
            "message": "Посоветуй маршрут для новичков",
            "history": [
                {"role": "user", "content": "..."},
                {"role": "assistant", "content": "..."}
            ]
        }

    Response:
        {"response": "...", "success": true}
    """
    try:
        data = json.loads(request.body)
        user_message = data.get('message', '').strip()
        history = data.get('history', [])

        if not user_message:
            return JsonResponse({'success': False, 'error': 'Пустое сообщение'})

        if len(user_message) > 1000:
            return JsonResponse({'success': False, 'error': 'Сообщение слишком длинное'})

        # Build conversation
        messages = history[-10:]  # Keep last 10 messages for context
        messages.append({'role': 'user', 'content': user_message})

        # Get fresh routes context
        context = get_routes_context()

        # Query Ollama
        response_text = ollama_client.chat(messages, context=context)

        return JsonResponse({
            'success': True,
            'response': response_text,
        })

    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Неверный формат запроса'})
    except Exception as e:
        logger.error('Chat API error: %s', str(e))
        return JsonResponse({'success': False, 'error': 'Внутренняя ошибка сервера'})


def suggest_routes_api(request):
    """
    AI-powered route suggestion based on user preferences.
    Called via AJAX from the homepage/route list.
    """
    preferences = request.GET.get('preferences', '')
    difficulty = request.GET.get('difficulty', '')
    duration_max = request.GET.get('duration_max', '')

    prompt = f'Пользователь ищет туристический маршрут. '
    if preferences:
        prompt += f'Предпочтения: {preferences}. '
    if difficulty:
        prompt += f'Желаемая сложность: {difficulty}. '
    if duration_max:
        prompt += f'Максимальная длительность: {duration_max} часов. '

    prompt += 'Порекомендуй 2-3 конкретных маршрута из доступных на сайте с кратким объяснением.'

    context = get_routes_context()
    response = ollama_client.chat(
        [{'role': 'user', 'content': prompt}],
        context=context
    )

    return JsonResponse({'success': True, 'suggestion': response})


def travel_plan_api(request):
    """Generate an AI travel plan for Karaganda."""
    days = request.GET.get('days', '2')
    interests = request.GET.get('interests', 'природа, история')

    prompt = (
        f'Составь план путешествия по Карагандинскому региону на {days} дня/дней. '
        f'Интересы туриста: {interests}. '
        'Включи конкретные маршруты, места и время. Формат: по дням.'
    )

    context = get_routes_context()
    response = ollama_client.chat(
        [{'role': 'user', 'content': prompt}],
        context=context
    )

    return JsonResponse({'success': True, 'plan': response})