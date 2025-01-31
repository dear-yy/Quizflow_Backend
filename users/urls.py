from django.urls import path
from .views import RegisterView, LoginView, ProfileView, DeactivateAccountView

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path("profile/<int:pk>/", ProfileView.as_view(),name='profile'), # 유저 pk
    path('account/delete/',  DeactivateAccountView.as_view(), name='profile_delete'), # 현재 로그인된 유저의 프로필을 삭제
]