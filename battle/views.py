# battle/views.py
from datetime import datetime # end_date 설정
from django.utils import timezone
from django_redis import get_redis_connection # 장고와 레디스 연결
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .serializers import BattleroomListSerializer, NewBattleroomSerializer
from .models import Battleroom
from django.contrib.auth.models import User


class MatchBattleViewAPI(APIView):
    """
    1:1 배틀 매칭 API
    post 사용자가 매칭을 요청하면 Redis 대기열에 추가
    get  매칭 결과 조회를 통해, 매칭이 성사되면 배틀 룸 생성
    """
    # 로그인 상태 인증
    permission_classes = [IsAuthenticated]


    # 현재 사용자 대기열(queue)에 추가
    def post(self, request):
        # Redis에서 대기열(Queue) 가져오기
        r = get_redis_connection("default") # djagno를 Redis 서버에 연결하고, 그 연결을 통해 대기열(Queue)에 접근
        user_id = request.user.id  # 로그인한 사용자의 ID를 가져옴

        # 대기열에서 해당 사용자가 이미 존재하는지 확인
        queue = r.lrange("battle_queue", 0, -1)  # 대기열에 있는 모든 사용자 ID를 가져옴
        if str(user_id).encode('utf-8') in queue:  # Redis는 바이트 배열로 저장되므로, 비교할 때 인코딩을 맞춰야 함
            return Response({"message": "이미 대기열에 사용자가 존재합니다."}, status=status.HTTP_400_BAD_REQUEST)

        # 대기열에 사용자를 추가
        r.rpush("battle_queue", user_id)  # user.id를 저장함
        return Response({"message": "배틀 대기열에 추가되었습니다. 매칭을 기다려주세요."}, status=status.HTTP_200_OK)
    


    # 대기 큐에서 본인을 포함한 2명 매칭하여 배틀룸을 생성
        # GET 요청: 프론트에서 배틀룸 생성 여부를 확인하기 위해 일정 시간 간격으로 GET 요청을 서버에 보내야 함!
    def get(self, request):
        # Redis에서 대기열(Queue) 가져오기
        r = get_redis_connection("default") # djagno를 Redis 서버에 연결하고, 그 연결을 통해 대기열(Queue)에 접근
        
        # 대기 큐에서 대기중인 사용자 확인 
        player_1_id = r.lindex("battle_queue", 0) 
        player_2_id = r.lindex("battle_queue", 1)

        # 바이트 문자열을 디코딩하여 일반 문자열로 변환(redis는 데이터가 텍스트가 아니라 바이트 시퀀스로 처리됨)
        player_1_id = player_1_id.decode('utf-8') if player_1_id else None
        player_2_id = player_2_id.decode('utf-8') if player_2_id else None
        print(player_1_id)
        print(player_2_id)

        if player_2_id:
            # player_1_id과 player_2_id 중 본인이 존재하는 지 확인
            user_id = request.user.id  # 현재 로그인된 본인의 사용자 ID
                
            if player_1_id == str(user_id) or player_2_id == str(user_id): # 본인이 존재
                # 대기열(Queue)에서 제거
                r.lpop("battle_queue") 
                r.lpop("battle_queue") 

                # 배틀룸 생성
                battleroom = self.create_battleroom(player_1_id, player_2_id)
                return Response({"message": "매칭이 성공적으로 처리되었습니다."}, status=status.HTTP_200_OK)
            else: # 둘 다 본인이 아니면 
                return Response({"message": "대기 중입니다."}, status=status.HTTP_200_OK)
        else:
            # 두 번째 사용자 없음 (첫번째 사용자는 본인임)
            return Response({"message": "대기 중인 사용자가 없습니다."}, status=status.HTTP_200_OK)
        

    def create_battleroom(self, player_1_id, player_2_id):
        # 두 플레이어의 User 객체 가져오기
        player_1 = User.objects.get(id=player_1_id)
        player_2 = User.objects.get(id=player_2_id)
    
        # 배틀룸 생성
        battleroom = Battleroom.objects.create(
            player_1=player_1,
            player_2=player_2,
            # 초기 스테이지는 기본값 "quiz_1"으로 
            now_stage_1="quiz_1",
            now_stage_2="quiz_1",
            start_date=timezone.now()  # 배틀룸 생성 시각
        )

        return battleroom


class CancelMatchViewAPI(APIView):
    """
    배틀 대기열에서 사용자가 나가는 API
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user_id = request.user.id
        if self.remove_from_queue(user_id): 
            return Response({"message": "배틀 대기열에서 성공적으로 나가셨습니다"}, status=status.HTTP_200_OK)
        else:
            return Response({"message": "대기열에 존재하지 않는 사용자입니다."}, status=status.HTTP_400_BAD_REQUEST)

    def remove_from_queue(self, user_id):
        r = get_redis_connection("default")
        r.lrem("battle_queue", 0, str(user_id))  # 0은 처음부터 끝까지 검색하여 일치하는 값 제거

    def remove_from_queue(self, user_id):
        r = get_redis_connection("default")
    
        # 대기열에서 모든 사용자 ID를 가져오기 (0부터 끝까지)
        queue = r.lrange("battle_queue", 0, -1) 
    
        # queue에 user_id가 존재하는지 확인
        if str(user_id).encode('utf-8') in queue:  # Redis는 바이트 배열로 저장되므로, 비교할 때 인코딩을 맞춰야 함
            # 사용자가 대기열에 존재하면 제거
            r.lrem("battle_queue", 0, str(user_id))
            return True
        else:
            return False
 



class BattleroomListViewAPI(APIView):
    """
    배틀룸 종료 내역 조회 API
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # 사용자가 참여한 배틀룸 내역을 조회 (player_1 또는 player_2로 참여한 배틀룸)
        user = request.user  # 로그인한 사용자 가져오기
        battlerooms = Battleroom.objects.filter(player_1=user,  is_ended=True) | Battleroom.objects.filter(player_2=user, is_ended=True)
        
        serializer = BattleroomListSerializer(battlerooms, many=True) # 직렬화
        return Response(serializer.data, status=status.HTTP_200_OK)


class NewBattleroomViewAPI(APIView):
    """
    새로운 배틀룸 조회 API (웹소켓 연결을 위한 정보 반환)
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user  # 로그인한 사용자 가져오기
        
        # 사용자가 소속된 새로 생성된(is_ended=False) 배틀룸 조회 -> 무조건 1개 이하로 관리할 거임
        battleroom = Battleroom.objects.filter(player_1=user, is_ended=False) | Battleroom.objects.filter(player_2=user, is_ended=False)
        if battleroom:
            serializer = NewBattleroomSerializer(battleroom, many=True) # 직렬화 # many=True로 설정했지만, 배틀룸 무조건 1개 이하로 관리할 거임
            return Response(serializer.data, status=status.HTTP_200_OK)
        else: 
            return Response({"message": "아직 매칭이 완료되지 않아 배틀룸이 생성되지 않았습니다."}, status=status.HTTP_400_BAD_REQUEST)
        
        

# 배틀룸 나가기
class DisconnectViewAPI(APIView): 
    """
    배틀룸 종료 API
    """
    permission_classes = [IsAuthenticated]

    # 데이터 일부 수정 patch 요청으로 처리 
    def patch(self, request, battleroom_id): # URL에서 battleroom_id 가져오기
        user_id = request.user.id  # 로그인한 사용자 가져오기
        end_date = request.data.get("end_date")  # "2025-03-18 13:25:29" 형태

        # 데이터 누락 확인
        if not battleroom_id or not end_date or not user_id:
            return Response({"error": "battle_id, user_id, end_date 데이터 누락"}, status=status.HTTP_400_BAD_REQUEST)
        
        battleroom = Battleroom.objects.filter(pk=battleroom_id).first() #  first()를 통해 단일 객체 가져오기
        if not battleroom:
            return Response({"error": "존재하지 않은 배틀룸입니다."}, status=status.HTTP_400_BAD_REQUEST)
        else:     
            # 포맷팅
            try:
                end_date = datetime.strptime(end_date, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                return Response({"error": "date형식 오류"}, status=status.HTTP_400_BAD_REQUEST)
            
            if battleroom.player_1.id==user_id:
                # print("player1")
                battleroom.end_date_1 = end_date
                battleroom.now_stage_1 = "end"
            elif battleroom.player_2.id==user_id:
                battleroom.end_date_2 = end_date
                battleroom.now_stage_2 = "end"
            else:
                return Response({"error": "사용자 조회 오류"}, status=status.HTTP_400_BAD_REQUEST)  
            
            battleroom.save()
            return Response({"message": "end_date 설정 완료"}, status=status.HTTP_200_OK)
