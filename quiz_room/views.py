from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Q
from .models import Quizroom
from .serializers import QuizroomCreateSerializer, QuizroomListSerializer, MessageListSerializer

# Create your views here.
class QuizroomsViewAPI(APIView):
    '''
        - 룸 목록 조회 (로그인 유저 본인)
        - 룸 생성 (로그인 유저 본인 / 입력값 없이 POST 요청 시 생성)
    '''
    # 로그인 인증
    permission_classes = [IsAuthenticated]

    def get(self, request):
        quizrooms = Quizroom.objects.filter(user=request.user)  # 유저 본인의 룸만 필터링
        serializer = QuizroomListSerializer(quizrooms, many=True) # 직렬화
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        # 일일 배틀 제한 확인 
        user = request.user # 로그인한 사용자 가져옴
        today = timezone.now().date()  # 오늘 날짜 (연-월-일)

        # 사용자의 '오늘' 등록된 퀴즈룸 개수 카운트
        quiz_generate_cnt = Quizroom.objects.filter(user=user, start_date__date=today).count()
        print("생성 퀴즈 카운트", quiz_generate_cnt)
        if quiz_generate_cnt >= 3:
            return Response({"error": "일일 제한 초과"}, status=status.HTTP_400_BAD_REQUEST)
        
        quizroom = Quizroom.objects.create(user=request.user) # Room 생성
        serializer = QuizroomCreateSerializer(quizroom) # 직렬화
        return Response( # 생성된 룸 정보 반환
            {"message": "방이 성공적으로 생성되었습니다!", "quizroom": serializer.data},
            status=status.HTTP_201_CREATED
        )

# 메세지 내역 조회
class MessageListViewAPI(APIView):
    '''
    사용자의 특정 퀴즈룸의 메세지 내역 조회
    '''
    
    def get(self, request, room_id):
        try:
            quizroom = get_object_or_404(Quizroom, id=room_id, user=request.user)  # 본인의 방만 조회 가능
            serializer = MessageListSerializer(quizroom)
            return Response( serializer.data , status=status.HTTP_200_OK)
        except Quizroom.DoesNotExist:
            return Response({"error": "방을 찾을 수 없거나 접근이 승인되지 않았습니다"}, status=status.HTTP_404_NOT_FOUND)
