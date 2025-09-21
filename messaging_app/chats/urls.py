# urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from chats import views

routers = DefaultRouter()
routers.register(r'conversations', views.ConversationViewSet,
                 basename='conversation')
routers.register(r'messages', views.MessageViewSet, basename='message')

urlpatterns = [
    path('api/', include(routers.urls)),
]
