from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from .serializers import RankingBoardSerializer

# Create your views here.
class RankingBoardViewAPI(APIView):
    # 로그인 인증
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        serializer = RankingBoardSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)