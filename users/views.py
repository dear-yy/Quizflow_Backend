from rest_framework.response import Response
from rest_framework import generics,status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from .permissions import CustomReadOnly
from .serializers import RegisterSerializer, LoginSerializer, ProfileSerializer
from django.contrib.auth.models import User
from .models import Profile



# 회원가입(생성)
class RegisterView(generics.CreateAPIView): # 생성 기능만 상속 
    queryset = User.objects.all()
    serializer_class = RegisterSerializer 
    # 생성 완료 시, username과 email 반환 


# 로그인(인증)
class LoginView(generics.GenericAPIView): # 모델에 (CRUD)영향을 주지 않으니, 기본 GenericAPIView 상속
    # 존재하는 유저라면, 토큰 찾아서 반환함으로써, 유저 인증을 수행하는 기능 
    serializer_class = LoginSerializer

    def post(self, request): # 클라이언트가 로그인 정보를 담아 POST 요청을 보내면 호출됨
        serializer = self.get_serializer(data=request.data) # 클라이언트의 요청 데이터를 역직렬화 # get_serializer()는 serializer_class에 지정된 LoginSerializer를 자동으로 불러옴
        serializer.is_valid(raise_exception=True) # 시리얼라이저에 전달된 데이터를 검증 # 데이터가 유효하지 않을 경우 유효성 검증 오류가 발생하는 옵션을 True로 설정
        token, user_pk = serializer.validated_data # LoginSerializer의 validate 메소드의 리턴값인 token 받아옴
        return Response({"token":token.key, "user_pk": user_pk}, status=status.HTTP_200_OK) #토큰 객체에서 key를 추출하여 클라이언트에게 전달
    

# 프로필(조회,수정)
class ProfileView(generics.RetrieveUpdateAPIView):
    queryset = Profile.objects.all()
    serializer_class = ProfileSerializer 
    permission_classes = [CustomReadOnly] # 조회&수정 권한


# 회원 탈퇴
class DeactivateAccountView(APIView):
    def delete(self, request, *args, **kwargs):
        user = request.user  # 현재 로그인된 사용자 가져오기
        try:
            # 해당 사용자의 프로필과 사용자 데이터 삭제
            user.profile.delete()  # 프로필 삭제
            user.delete()  # 사용자 삭제
            return Response({"message": "Account successfully deleted."}, status=status.HTTP_204_NO_CONTENT)
        except Profile.DoesNotExist:
            return Response({"error": "Profile not found."}, status=status.HTTP_404_NOT_FOUND)
        except User.DoesNotExist:
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)
    