"""
ASGI config for myquiz project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/asgi/
"""
# myquiz.asgi.py
import os
from django.core.asgi import get_asgi_application
from channels.auth import AuthMiddlewareStack
# http 프로토콜 요청 외에 websocket 프로토콜 요청도 처리할 수 있도록
from channels.routing import ProtocolTypeRouter, URLRouter
# from quiz_room.middlewares import 

# Django의 설정 파일을 지정
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "myquiz.settings")

# Django의 ASGI 애플리케이션을 반환
django_asgi_app = get_asgi_application()

# 임포트 순서 중요!(django_asgi_app 초기화 후에)
import quiz_room.routing # 생성할 퀴즈 앱의 웹 소켓 연결 경로 파일임!

# 요청 프로토콜에 따라, 다른 asgi application을 통해 처리되도록 라우팅
application = ProtocolTypeRouter( 
    {
        # "http" 프로토콜 요청에 대해 django_asgi_app 사용
        "http": django_asgi_app,

        # "websocket" 프로토콜에 요청 대해 
            # AuthMiddlewareStack로 인증처리 (scope["user"]에 로그인된 사용자 정보를 포함) 
            # chat.routing.websocket_urlpatterns로 라우팅을 처리
            
        "websocket": AuthMiddlewareStack( #AuthMiddlewareStack
                URLRouter(quiz_room.routing.websocket_urlpatterns)
        )
    }
)

