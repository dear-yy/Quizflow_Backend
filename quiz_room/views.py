from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
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

# class QuizRoomDetailViewAPI(APIView):
#     '''
#         - 특정 룸 조회 (로그인 유저 본인) -> 메세지 내역 볼 수 있게 시리얼라이저 구현해야 할 듯 
#     '''


# class ArticlesViewAPI(APIView):
#     '''
#         - 특정 Room의 아티클 목록 조회 (로그인 유저 본인)
#         - 특정 Room에 아티클 생성 (로그인 유저 본인)
#     '''