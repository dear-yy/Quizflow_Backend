from django.shortcuts import render

# Create your views here. 회원가입
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import UserSerializer, ProfileSerializer
from .models import Profile
from django.contrib.auth import authenticate

class RegisterView(APIView):
    def post(self, request):
        user_serializer = UserSerializer(data=request.data)
        
        if user_serializer.is_valid():
            user = user_serializer.save()

            # 프로필 자동 생성
            profile = Profile.objects.create(user=user, nickname=request.data.get("nickname", ""))
            profile_serializer = ProfileSerializer(profile)

            return Response({
                "user": user_serializer.data,
                "profile": profile_serializer.data
            }, status=status.HTTP_201_CREATED)
        
        return Response(user_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LoginView(APIView):
    def post(self, request):
        username = request.data.get("username")
        password = request.data.get("password")

        user = authenticate(username=username, password=password)
        if user is None:
            return Response(
                {"error": "아이디 또는 비밀번호가 올바르지 않습니다."},
                status=status.HTTP_401_UNAUTHORIZED
            )

        refresh = RefreshToken.for_user(user)
        return Response(
            {"access_token": str(refresh.access_token), "refresh_token": str(refresh)},
            status=status.HTTP_200_OK
        )
