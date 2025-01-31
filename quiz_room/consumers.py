 # JsonWebsocketConsumer 
    # 웹소켓 연결 관리에 필요한 모든 처리 구현되어 있음
    # 웹소켓 클라이언트와 텍스트 데이터 송수신 시에 Json 직렬화&역직렬화까지 모두 처리 
from channels.generic.websocket import JsonWebsocketConsumer
# import openai
from django.contrib.auth.models import User
from quiz_room.models import Quizroom


# 서버측 웹소켓 연결 처리 
class QuizroomConsumer(JsonWebsocketConsumer):
    # 생성자
    def __init__(self, *args, **kargs): # 재정의
        super().__init__(*args, **kargs) # 부모(JsonWebsocketConsumer)생성자 호출


    # 웹소켓 연결 요청을 받으면 호출됨 
    def connect(self): # 수락 여부 결정 
        room = self.get_room() # 채팅방 조회 

        if room is None: # 조회가 안된다면
            self.close() # 웹소켓 연결 요청 거부 
        else: # 조회가 된다면 
            self.accept() # 웹소켓 연결 요청을 수락


    # receive_json()메서드는 웹소켓 클라이언트로부터 텍스트 데이터를 수신할 때마다 호출됨
        # 웹소켓을 통해 어떤 데이터를 받았을때, 어떤 처리를 할지 구현할 메서드
    def receive_json(self, content_dict, **kargs): # 재정의 
        #  receive_json호출 전에,  json.loads로 역질렬화 처리를 거쳐 파이썬 객체(content)를 인자로 넘겨줌 
            # content 인자는 파이썬 객체이며, 보통 딕셔너리 타입임 
        print("received:", content_dict) # 디버깅용~
        
        # 웹소켓 클라이언트(유저)에게게 데이터(응답 메세지) 전송 시
        # self.send_json({임의의_딕셔너리_데이터})
        self.send_json(content_dict) # Echo 응답(수신한 데이터인 content_dict를 그대로 응답)



    # 채팅방 조회
    def get_room(self) -> Quizroom | None: # 채팅방 존재하면 인스턴스 반환, 없으면 None 반환 
        # 현재 요청 User 인스턴스
            #  self.scope["user"]를 통해 사용(뷰에서 request.uesr와 같은 의미)
        user: User = self.scope["user"]

        # 퀴즈룸 pk
            # self.scope["url_route"]["kwargs"]["quizroom_pk"]를 통해 접근  
                # self.scope["url_route"] (뷰에서 함수 뷰 인자로 받는 url captured value)
                # routing.py에서 url captured value로서 quizroom_pk를 지정했었음
        quizroom_pk = self.scope["url_route"]["kwargs"]["quizroom_pk"]        
        room: Quizroom = None # 초기값을 None으로 설정하여, 방 못찾으면 그대로 반환 

        # 현재 유저가 로그인 상태라면
        if user.is_authenticated:
            try:
                room = Quizroom.objects.get(pk=quizroom_pk, user=user)
            except Quizroom.DoesNotExist: # 로그인 유저에 대해 채팅방을 못찾은 경우 
                pass
        
        # 조회한 채팅방 객체 반환
        return room
    

    



