from django.urls import path
from . import consumers

websocket_urlpatterns = [
    # 웹소켓은 url별로 그 요청을 처리할 RolePlayingConsumer 클래스를 다르게 지정할 수 있음 
    # /ws/chat/10/ 과 같은 주소로 웹소켓 연결을 받을 수 있음 
    # 즉, 각 퀴즈룸마다 연결하는 웹소켓 주소가 다르도록!
    path("ws/chat/<int:quizroom_pk>/", consumers.QuizroomConsumer.as_asgi()) # <int:quizroom_pk>는 프론트에서 받아와야 하는 인자자
]