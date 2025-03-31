@echo off
cd /d C:\projects\Quizflow_Backend
call C:\venvs\myquizvenv\Scripts\activate
python manage.py reset_ranking
deactivate
exit