# urls.py
from django.urls import path, include
from rest_framework import routers
from rest_framework_extensions.routers import NestedRouterMixin
from chats import views

# Create NestedDefaultRouter


class NestedDefaultRouter(NestedRouterMixin, routers.DefaultRouter):
    pass


router = NestedDefaultRouter()
conversations_router = router.register(r'conversations', views.ConversationViewSet,
                                       basename='conversation')
conversations_router.register(r'messages', views.MessageViewSet,
                              basename='conversation-messages', parents_query_lookups=['conversation'])

urlpatterns = [
    path('api/', include(router.urls)),
]
