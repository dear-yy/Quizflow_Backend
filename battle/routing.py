# battle.routing.py
from django.urls import path
from .consumers import  BattleSetupConsumer, BattleConsumer

websocket_urlpatterns = [
    # 두 플레이어가 공유하는 데이터 (아티클, 퀴즈)를 생성
    path("ws/battle/<int:battle_room_id>/", BattleSetupConsumer.as_asgi()),
    # 각 플레이어가 개별적으로 퀴즈를 풀이
    path("ws/battle/<int:battle_room_id>/<int:player_id>/", BattleConsumer.as_asgi()),
]