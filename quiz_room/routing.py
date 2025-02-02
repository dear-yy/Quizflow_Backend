# quiz_room.routing.py
from django.urls import path
from . import consumers

websocket_urlpatterns = [
    # 각 퀴즈룸(quizroom_id)마다 연결하는 웹소켓 주소가 다르도록!
    # 프론트엔드에서 받아온 quizroom_id를 사용하여 각 퀴즈룸에 대한 연결 처리    
    path("ws/chat/<int:quizroom_id>/", consumers.QuizroomConsumer.as_asgi()) # `ws://${window.location.host}/ws/chat/${room_pk}/`
]



# [확인 방법 -> 콘솔창에서]
'''
// 웹소켓 연결
const ws = new WebSocket("ws://localhost:8000/ws/chat/1/");

// 서버에서 (클라이언트)메시지가 수신 시 호출됨
ws.onmessage = function(e) { // e.data는 수신 데이터
  console.group("[수신 메세지]"); // 콘솔 로그 그룹화(시작)
  console.log(typeof e.data); // JSON 형식일 경우 "string" 반환
  console.log(e.data); // 콘솔창에서 한글은 유니코드로 반환됨
  const message_obj = JSON.parse(e.data); // 수신된 메시지(JSON 형식) 변환
  console.groupEnd(); // 콘솔 로그 그룹화(종료)
};

// 클라이언트 메시지 전송
ws.send(JSON.stringify({ message: "원하는 메세지 입력하는 부분" })); //  JSON 문자열로 변환하여, 서버로 메시지를 전송
'''

# 토큰 받아와서 인증 수행한다면 다음 경로를 통해, 인자 받아오기
# const socket = new WebSocket(`ws://localhost:8000/ws/chat/${quizroomId}/?token=${token}`);