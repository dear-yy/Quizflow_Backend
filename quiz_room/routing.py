# quiz_room.routing.py
from django.urls import path
from . import consumers

websocket_urlpatterns = [
    # 각 퀴즈룸(quizroom_id)마다 연결하는 웹소켓 주소가 다르도록!
    # 프론트엔드에서 받아온 quizroom_id를 사용하여 각 퀴즈룸에 대한 연결 처리    
    path("ws/chat/<int:quizroom_id>/", consumers.QuizroomConsumer.as_asgi())
]



# [확인 방법 -> 콘솔창에서]
''' 
//서버 접속  
서버(http://127.0.0.1:8000)에 한 번 접속해야 웹소켓 연결이 정상적으로 이루어짐 

// 웹소켓 연결
const ws = new WebSocket("ws://localhost:8000/ws/chat/1/");

ws.onopen = function(e) { console.log("장고 채널스 서버와 웹소켓 연결되었습니다."); };
ws.onclose = function(e) { console.log("장고 채널스 서버와 웹소켓이 끊어졌습니다."); };
ws.onerror = function(e) { console.error("장고 채널스 서버와의 웹소켓 연결 중에 오류가 발생했습니다.", e); };

// (서버 -> 클라이언트) 메세지 확인 // send_json 코드 수행시
ws.onmessage = function(event) {                 // e.data는 수신 데이터
  console.group("[클라이언트 수신 메세지]");            // 콘솔 로그 그룹화(시작)
  const data = JSON.parse(event.data); // 서버에서 받은 JSON 메시지 파싱
  console.log(data); // 메시지를 콘솔에 출력
  console.groupEnd();                       // 콘솔 로그 그룹화(종료)
};


// (클라이언트 -> 서버) 메시지 전송
ws.send(JSON.stringify({ type: 'auth', token: '256bf1667be1b280c80f642d551c7c65c4ecb101' })); // 토큰 검사(사용자 인증)
ws.send(JSON.stringify({ type: 'user', message: '메세지 입력란' })); //  JSON 문자열로 변환하여, 서버로 메시지를 전송
'''