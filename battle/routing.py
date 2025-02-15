# battle.routing.py
from django.urls import path
from . import consumers

websocket_urlpatterns = [
    path("ws/battle/<int:battle_room_id>/", consumers.BattleConsumer.as_asgi()),
    path("ws/battle/<int:battle_room_id>/<int:player_id>/", consumers.BattleConsumer.as_asgi()),
]