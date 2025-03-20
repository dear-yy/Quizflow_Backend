# battle.urls.py

from django.urls import path
from .views import MatchBattleViewAPI, CancelMatchViewAPI, BattleroomListViewAPI, NewBattleroomViewAPI, BattleroomDisconnectViewAPI,  BattleroomResultViewAPI

urlpatterns = [
    # 배틀 매칭 대기 & 배틀룸 생성
    path('match/', MatchBattleViewAPI.as_view(), name='battle_match'),

    # 새로운 배틀룸 조회 
    path('new_room/', NewBattleroomViewAPI.as_view(), name='battle_match_new_room'),

    # 본인 배틀 내역 조회 
    path('list/', BattleroomListViewAPI.as_view(), name='battle_list'),

    # 배틀 대기열 나가기
    path('match/cancel/', CancelMatchViewAPI.as_view(), name='battle_match_cancel'),

    # 배틀룸 나가기
    path('<int:battleroom_id>/disconnect/', BattleroomDisconnectViewAPI.as_view(), name='battleroom_disconnect'),

    # 배틀 결과 조회 
    path('<int:battleroom_id>/result/',  BattleroomResultViewAPI.as_view(), name='battle_result'),

]