#!/bin/bash

# 로그 시작
echo "[$(date)] reset_ranking 시작" >> ~/Quizflow_Backend/reset_ranking.log

# 가상환경 활성화
source ~/venvs/bin/activate

# 프로젝트 폴더로 이동
cd ~/Quizflow_Backend

# Django 커맨드 실행
python manage.py reset_ranking >> ~/Quizflow_Backend/reset_ranking.log 2>&1

# 로그 종료
echo "[$(date)] reset_ranking 완료" >> ~/Quizflow_Backend/reset_ranking.log
