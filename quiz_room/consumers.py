# quiz_room.consumers.py 

# 웹소켓 클라이언트와 텍스트 데이터 송수신 시에 Json 직렬화&역직렬화까지 모두 처리 
from channels.generic.websocket import JsonWebsocketConsumer
# import openai
from rest_framework.authtoken.models import Token
from django.contrib.auth.models import User
from quiz_room.models import Quizroom, QuizroomMessage

''' 
# 1. 토큰 받아오기 
# 2. 토큰과 연결된 사용자 반환 
# 3. 해당 사용자에게 해당 id의 방 존재 여부 파악 
# 4. 방 반환
'''

# 서버측 웹소켓 연결 처리 
class QuizroomConsumer(JsonWebsocketConsumer):
    def connect(self):
        print("연결 중입니다.")
        self.user = None # 인증 전이므로, None으로 초기화
        self.room = None # 조회 전이므로, None으로 초기화
        self.now_stage = None  # 퀴즈 진행 상태 초기화
        self.accept()

    def disconnect(self, close_code):
        print("연결을 중단합니다.")
        self.user = None  # 사용자 정보 초기화
        self.room = None # 방 정보 초기화
        self.now_stage = None  # 퀴즈 진행 상태 초기화
        
    def receive_json(self, content_dict, **kwargs):
        if self.user is None: # 사용자 인증 전 상태
            # 토큰 검사
            token = content_dict.get("token") # 클라이언트에서 보낸 토큰 가져오기
            if token: # 토큰 입력 존재
                try: 
                    self.user = Token.objects.get(key=token).user # 토큰으로 사용자 인증
                    print(f'{self.user}의 토큰이 존재합니다')
                    print("~ 방을 조회하는 중입니다. 잠시만 기다려 주세요 ~")
                except Token.DoesNotExist: # 유효하지 않은 토큰
                    print(f'유효하지 않은 토큰이므로 연결이 종료됩니다...')
                    self.close()
                    return 
            else: # 토큰 입력 없음
                print("토큰이 제공되지 않아 연결이 종료됩니다...")
                self.close()
                return 

            # 채팅방 조회
            self.room = self.get_room() # 채팅방 조회
            if self.room is None: 
                print("조회할 수 없는 방이므로 연결이 종료됩니다...")
                self.close() # 존재하지 않는 방이면 연결 거부
                return 
            else: 
                print(f"[{self.user}의 방]") # 해당 방으로 연결

        # cnt 값 검증(퀴즈 세트 완료 여부)
        if self.room.cnt >= 3:
            print("최대 퀴즈 수를 초과했습니다. 연결을 종료합니다.")
            self.send_json({"error": "최대 퀴즈 수를 초과했습니다." })
            self.close()
            return
        
        # 퀴즈 진행 상태 복원
        # self.quiz_stage = self.room.quiz_stage # 아직 모델 수정 안해뒀음 
        # print(f"🔄 이전 퀴즈 상태 복원: {self.room.cnt + 1}번 아티클 {self.quiz_stage}")
        # 현재 stage완료 시 다음 stage로 갱신하는 로직 구현하기

        else: # 이미 인증된 사용자인 경우
            print(f"📩 {self.user}의 메시지: {content_dict}")
            # self.send_json(content_dict)  # 받은 메시지를 그대로 반환 (Echo/ onmessage)
            
            # 메시지 내용 모델 객체로 저장
            message_content = content_dict.get("message")
            if message_content:
                if self.room: 
                    QuizroomMessage.objects.create(
                        quizroom=self.room,
                        message=message_content,
                        is_gpt=False # 일단 사용자 메세지로 셋팅
                    )
                    # cnt 값 증가 및 저장
                    self.room.cnt += 1
                    self.room.save()
                    print(f"퀴즈 수 업데이트: 현재 cnt 값은 {self.room.cnt}입니다.")


    # 채팅방 조회
    def get_room(self) -> Quizroom | None: # 채팅방 존재하면 인스턴스 반환, 없으면 None 반환 
        room: Quizroom = None # 초기값을 None으로 설정하여, 방 못찾으면 그대로 반환 

        # 퀴즈룸 pk 
            # routing.py에서 url captured value로서 quizroom_id를 지정했었음
        quizroom_id = self.scope["url_route"]["kwargs"]["quizroom_id"]

        # 사용자 소유 방인지 
        print(f"사용자 {self.user}의 {quizroom_id}번 방 조회... ")    
        try:
            room = Quizroom.objects.get(pk=quizroom_id, user=self.user)
        except Quizroom.DoesNotExist: # 로그인 유저에 대해 채팅방을 못찾은 경우 
            print("현재 조회중인 방은 사용자의 방이 아닙니다.")
            pass
       
        # 조회한 채팅방 객체 반환
        return room 
   