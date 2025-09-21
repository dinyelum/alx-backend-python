# urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from chats import views

router = DefaultRouter()
router.register(r'conversations', views.ConversationViewSet,
                basename='conversation')
router.register(r'messages', views.MessageViewSet, basename='message')

urlpatterns = [
    path('api/', include(router.urls)),
]
