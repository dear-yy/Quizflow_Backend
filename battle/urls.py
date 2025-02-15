# battle.urls.py

from django.urls import path
from .views import MatchBattleViewAPI, CancelMatchViewAPI

urlpatterns = [
    # 배틀 매칭 대기 & 배틀룸 생성
    path('match/', MatchBattleViewAPI.as_view(), name='battle_match'),

    # 배틀 대기열 나가기
    path('match/cancel/', CancelMatchViewAPI.as_view(), name='battle_match_cancel'),
]