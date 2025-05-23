from django.urls import path
from . import views

app_name = 'student_learning'

urlpatterns = [
    path('', views.learning_type_dashboard, name='dashboard'),
]