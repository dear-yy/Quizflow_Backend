from django.contrib import admin
from .models import Battleroom, BattleArticle, BattleQuiz


class BattleArticleInline(admin.StackedInline): 
    model = BattleArticle
    extra = 0  # 추가 입력 필드 개수

class BattleQuizInline(admin.StackedInline): 
    model = BattleQuiz
    extra = 0 # 추가 입력 필드 개수

class BattleroomAdmin(admin.ModelAdmin):
    inlines = [BattleArticleInline, BattleQuizInline]  # 인라인 추가
    list_display = ('id', 'player_1', 'player_2', 'is_ended', 'start_date')  # 목록에 표시할 필드
    list_filter = ('is_ended', 'start_date')
    search_fields = ('player_1__username', 'player_2__username')

# 인라인 설정 후,  Battleroom 등록 
admin.site.register(Battleroom, BattleroomAdmin)  
