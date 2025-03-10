# diskapp/urls.py
from django.urls import path
from . import views

app_name = 'diskapp'

urlpatterns = [
    path('', views.index, name='index'),
    path('files/', views.file_list, name='file_list'),
    path('download/', views.download_files, name='download_files'),
]
