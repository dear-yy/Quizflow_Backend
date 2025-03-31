from django.urls import path
from .views import RankingBoardViewAPI

urlpatterns = [
    path('board/', RankingBoardViewAPI.as_view(), name='ranking_board'),
]