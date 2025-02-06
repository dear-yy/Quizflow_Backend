from django.contrib import admin
from .models import Quizroom, QuizroomMessage, Article, MultipleChoiceQuiz,  DescriptiveQuiz

# Register your models here.

# Article을 Quizroom의 인라인으로 설정
class ArticleInline(admin.TabularInline):
    model = Article
    extra = 0  # 기본 메시지 추가 항목 수 # (사용자가 실제로 메시지를 추가해야 할 경우에만 폼을 표시 -> 불필요한 빈 폼을 방지)


# MultipleChoiceQuiz 모델을 Article의 인라인으로 설정
class MultipleChoiceQuizInline(admin.TabularInline):  
    model = MultipleChoiceQuiz
    extra = 0  

# DescriptiveQuiz 모델을 Article의 인라인으로 설정
class DescriptiveQuizInline(admin.TabularInline):  
    model = DescriptiveQuiz
    extra = 0  


# QuizroomMessage 모델을 Quizroom 모델에 인라인으로 등록
class QuizroomMessageInline(admin.TabularInline):  
    model = QuizroomMessage
    extra = 0  


# Article 관리자 설정 (MultipleChoiceQuiz, DescriptiveQuiz 인라인 포함)
class ArticleAdmin(admin.ModelAdmin):
    inlines = [MultipleChoiceQuizInline, DescriptiveQuizInline]
    
# Quizroom 관리자 설정 (Article, QuizroomMessage 인라인 포함)
class QuizroomAdmin(admin.ModelAdmin):
    inlines = [ArticleInline, QuizroomMessageInline]

# 관리자 페이지에 모델 등록
admin.site.register(Quizroom, QuizroomAdmin)
admin.site.register(Article, ArticleAdmin)
admin.site.register(QuizroomMessage) # QuizroomMessage 객체만 보고 싶다면 등록하기
