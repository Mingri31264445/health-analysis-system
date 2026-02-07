from django.urls import path
from . import views

#app_name = 'core'

urlpatterns = [
    path('', views.index, name='index'),
    path('questionnaires/', views.questionnaire_list, name='questionnaire_list'),
    path('questionnaires/create/', views.questionnaire_create, name='questionnaire_create'),
    path('questionnaires/<int:pk>/delete/', views.questionnaire_delete, name='questionnaire_delete'),
    path('meridian/create/', views.meridian_create, name='meridian_create'),
    path('bfs/create/', views.bfs_create, name='bfs_create'),
    path('face-diagnosis/create/', views.face_diagnosis_create, name='face_diagnosis_create'),
]