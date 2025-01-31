from django.urls import path
from .views import RegisterView, LoginView, ProfileView

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path("profile/<int:pk>/", ProfileView.as_view(),name='profile'), # 유저 pk
    # 회원 탈퇴 URL
    path('user/profile/delete/', views.ProfileView.as_view(), name='profile_delete'), 
]