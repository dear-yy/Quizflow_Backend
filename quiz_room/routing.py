# quiz_room.routing.py
from django.urls import path
from . import consumers

websocket_urlpatterns = [
    # 각 퀴즈룸(quizroom_id)마다 연결하는 웹소켓 주소가 다르도록!
    # 프론트엔드에서 받아온 quizroom_id를 사용하여 각 퀴즈룸에 대한 연결 처리    
    path("ws/chat/<int:quizroom_id>/", consumers.QuizroomConsumer.as_asgi())
]