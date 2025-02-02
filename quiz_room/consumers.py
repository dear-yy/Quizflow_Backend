# quiz_room.consumers.py 

# 웹소켓 클라이언트와 텍스트 데이터 송수신 시에 Json 직렬화&역직렬화까지 모두 처리 
from channels.generic.websocket import JsonWebsocketConsumer
# import openai
from django.contrib.auth.models import User
from quiz_room.models import Quizroom

'''
# 1. 토큰 받아오기 
# 2. 토큰과 연결된 사용자 반환 
# 3. 해당 사용자에게 해당 id의 방 존재 여부 파악 
# 4. 방 반환
'''

# 서버측 웹소켓 연결 처리 
class QuizroomConsumer(JsonWebsocketConsumer):
    # 생성자
    def __init__(self, *args, **kargs): 
        # 부모 클래스 초기화
        super().__init__(*args, **kargs) 


    # 웹소켓 연결 요청을 받으면 호출
    def connect(self): 
    #     room = self.get_room() # 채팅방 조회 
    #     if room is None: 
    #         print("연결 거부")
    #         self.close() # 존재하지 않는 방이면 연결 거부
    #     else: 
    #         print("연결됨")
    #         self.accept() # 방이 존재하면 연결 수락
        print("연결됨")
        self.accept() # 방이 존재하면 연결 수락


    # 웹소켓에 연결된 클라이언트로부터 데이터를 수신할 때마다 호출됨
    def receive_json(self, content_dict, **kargs):
        #  receive_json호출 전에, json.loads로 역질렬화 처리를 거쳐 파이썬 객체(content)를 인자로 넘겨줌 # content 인자는 파이썬 객체이며, 보통 딕셔너리 타입임 
        print(f"📩 received: {content_dict}")  # 디버깅용 출력
        
        # Echo 응답 (수신한 데이터를 그대로 클라이언트에 전송)
        self.send_json(content_dict)




    # # 채팅방 조회
    # def get_room(self) -> Quizroom | None: # 채팅방 존재하면 인스턴스 반환, 없으면 None 반환 
    #     room: Quizroom = None # 초기값을 None으로 설정하여, 방 못찾으면 그대로 반환 

    #     # 현재 요청 User 인스턴스
    #         #  self.scope["user"]를 통해 사용(뷰에서 request.uesr와 같은 의미)
    #     user: User = self.scope["user"]
        
    #     # 퀴즈룸 pk 
    #         # routing.py에서 url captured value로서 quizroom_id를 지정했었음
    #     quizroom_id = self.scope["url_route"]["kwargs"]["quizroom_id"]   

    #     # 현재 유저가 로그인 상태라면(사용자 인증 확인)
    #     if user.is_authenticated:
    #         print(f"사용자 {user}의 {quizroom_id}번 방 조회... ")    
    #         try:
    #             room = Quizroom.objects.get(pk=quizroom_id, user=user)
    #         except Quizroom.DoesNotExist: # 로그인 유저에 대해 채팅방을 못찾은 경우 
    #             pass
    #     else:
    #         print("사용자가 인증되지 않았습니다.")

    #     # 조회한 채팅방 객체 반환
    #     return room 
   