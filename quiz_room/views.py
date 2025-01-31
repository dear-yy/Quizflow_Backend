from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from .models import Quizroom
from .serializers import QuizroomSerializer

# Create your views here.
class QuizroomsViewAPI(APIView):
    '''
        - 룸 목록 조회 (로그인 유저 본인)
        - 룸 생성 (로그인 유저 본인 / 입력값 없이 POST 요청 시 생성)
    '''
    def get(self, request):
        quizrooms = Quizroom.objects.filter(user=request.user)  # 로그인한 유저의 룸만 필터링
        serializer = QuizroomSerializer(quizrooms, many=True) # 직렬화
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        quizroom = Quizroom.objects.create(user=request.user) # Room 생성
        serializer = QuizroomSerializer(quizroom) # 직렬화
        return Response( # 생성된 룸 정보 반환
            {"message": "방이 성공적으로 생성되었습니다!", "quizroom": serializer.data},
            status=status.HTTP_201_CREATED
        )

# 특정 룸 조회
class QuizRoomDetailViewAPI(APIView):

    def get(self, request, pk):
        quizroom = get_object_or_404(Quizroom, pk=pk, user=request.user)  # 본인의 방만 조회 가능
        serializer = QuizroomSerializer(quizroom)

        # 🔹 QuizroomMessage 추가: 해당 방의 대화 기록도 포함
        messages = QuizroomMessage.objects.filter(quizroom=quizroom)
        message_serializer = QuizroomMessageSerializer(messages, many=True)

        return Response(
            {
                "quizroom": serializer.data,
                "messages": message_serializer.data  # 🔹 메시지 내역 포함
            },
            status=status.HTTP_200_OK
        )

# 특정 Room의 아티클 목록 조회 및 생성
class ArticlesViewAPI(APIView):
    def get(self, request, pk):
        quizroom = get_object_or_404(Quizroom, pk=pk, user=request.user)  # 본인의 방만 접근 가능
        # articles = Article.objects.filter(quizroom=quizroom)  # 해당 방의 아티클 목록 조회
        # serializer = ArticleSerializer(articles, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request, pk):
        quizroom = get_object_or_404(Quizroom, pk=pk, user=request.user)  # 본인의 방만 접근 가능

        # 요청에서 필요한 데이터 추출
        title = request.data.get("title")
        url = request.data.get("url")
        body = request.data.get("body")
        reason = request.data.get("reason")
        user_feedback = request.data.get("user_feedback")

        # 필수 데이터 체크
        if not all([title, url, body, reason, user_feedback]):
            return Response({"error": "모든 필드를 입력해야 합니다."}, status=status.HTTP_400_BAD_REQUEST)

        # 아티클 생성
        # article = Article.objects.create(
            quizroom=quizroom,
            user=request.user,
            title=title,
            url=url,
            body=body,
            reason=reason,
            user_feedback=user_feedback
       #  )

        # serializer = ArticleSerializer(article)
        return Response(
            # {"message": "아티클이 성공적으로 생성되었습니다!", "article": serializer.data},
            status=status.HTTP_201_CREATED
        )
    
    #위의 코드의 주석 부분은 아직 구현이 완성되지 않은 부분임