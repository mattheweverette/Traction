from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='traction-home'),
    path('about/', views.about, name='traction-about'),
    path('search/', views.search, name='search')
]
