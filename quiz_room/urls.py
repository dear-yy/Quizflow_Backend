from django.urls import path
from .views import QuizroomsViewAPI, MessageListViewAPI #, QuizRoomDetailViewAPI, ArticlesViewAPI, 

urlpatterns = [
    # 로그인 유저의 채팅방 목록 조회 & 생성
    path('quizrooms/', QuizroomsViewAPI.as_view(), name='quizrooms'),

    # 로그인 유저의 특정 채팅방의 메세지 내역 조회 
    path('quizroom/<int:room_id>/message_list/', MessageListViewAPI.as_view(), name='message_list'),

]