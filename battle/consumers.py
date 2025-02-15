# battle.consumers.py 

# 웹소켓 클라이언트와 텍스트 데이터 송수신 시에 Json 직렬화&역직렬화까지 모두 처리 
from channels.generic.websocket import JsonWebsocketConsumer

class BattleConsumer(JsonWebsocketConsumer):
    def connect(self):
        print("연결 중입니다.")
        self.accept()

    def disconnect(self, close_code):
        print("연결을 중단합니다.")
        