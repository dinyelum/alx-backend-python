# chats/views.py
from rest_framework import viewsets, status, permissions, filters
from rest_framework.decorators import action, api_view
from rest_framework.response import Response
from django.db.models import Prefetch, Q, Count
from django_filters.rest_framework import DjangoFilterBackend
from django.contrib.auth import get_user_model
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_cookie, vary_on_headers
from .models import Conversation, Message, Notification, MessageHistory
from .serializers import (
    ConversationSerializer,
    ConversationDetailSerializer,
    ThreadedMessageSerializer,
    MessageCreateSerializer,
    UserSerializer
)
from .permissions import IsParticipantOfConversation, IsMessageOwner
from .pagination import MessagePagination, ConversationPagination
from .filters import MessageFilter, ConversationFilter
import logging

logger = logging.getLogger(__name__)
User = get_user_model()


@api_view(['POST'])
def delete_user(request):
    # ... existing delete_user implementation ... This page is a duplicate / update of ../../views.py
    pass


class UserViewSet(viewsets.ModelViewSet):
    # ... existing UserViewSet implementation ...
    pass


class ConversationViewSet(viewsets.ModelViewSet):
    # ... existing ConversationViewSet implementation ...
    pass


class MessageViewSet(viewsets.ModelViewSet):
    """
    ViewSet for listing, retrieving, and creating messages with threaded replies.
    Users can only see messages from conversations they are participants in.
    """
    permission_classes = [permissions.IsAuthenticated,
                          IsParticipantOfConversation, IsMessageOwner]
    filter_backends = [DjangoFilterBackend,
                       filters.SearchFilter, filters.OrderingFilter]
    filterset_class = MessageFilter
    search_fields = ['content', 'sender__first_name', 'sender__last_name']
    ordering_fields = ['timestamp', 'sender__first_name']
    ordering = ['-timestamp']
    pagination_class = MessagePagination

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return MessageCreateSerializer
        return ThreadedMessageSerializer

    def get_queryset(self):
        """
        Return only messages from conversations where the current user is a participant
        Optimized with select_related and prefetch_related for threaded conversations
        """
        # Use the custom manager for optimized queries
        queryset = Message.objects.filter(
            conversation__participants=self.request.user
        ).select_related(
            'sender', 'receiver', 'parent_message', 'conversation'
        )

        return queryset

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    def perform_create(self, serializer):
        """Automatically set the current user as the sender"""
        serializer.save(sender=self.request.user)

    @method_decorator(cache_page(60))  # Cache for 60 seconds
    # Vary cache by authorization header
    @method_decorator(vary_on_headers('Authorization'))
    @action(detail=False, methods=['get'])
    def unread(self, request):
        """
        Get all unread messages for the current user using the custom manager
        Optimized with .only() to retrieve only necessary fields
        Cached for 60 seconds
        """
        # Use the custom manager to get unread messages
        unread_messages = Message.unread.unread_for_user(request.user)

        # Apply additional filtering if needed
        conversation_id = request.query_params.get('conversation')
        if conversation_id:
            unread_messages = unread_messages.filter(
                conversation_id=conversation_id)

        # Use .only() to optimize the query further
        unread_messages = unread_messages.only(
            'message_id',
            'content',
            'timestamp',
            'sender__user_id',
            'sender__first_name',
            'sender__last_name',
            'conversation__conversation_id',
            'parent_message_id'
        )

        # Paginate the results
        page = self.paginate_queryset(unread_messages)
        if page is not None:
            serializer = ThreadedMessageSerializer(
                page,
                many=True,
                context={'request': request, 'max_depth': 2}
            )
            return self.get_paginated_response(serializer.data)

        serializer = ThreadedMessageSerializer(
            unread_messages,
            many=True,
            context={'request': request, 'max_depth': 2}
        )
        return Response(serializer.data)

    @method_decorator(cache_page(60))  # Cache for 60 seconds
    # Vary cache by authorization header
    @method_decorator(vary_on_headers('Authorization'))
    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        """
        Get the count of unread messages for the current user
        Cached for 60 seconds
        """
        count = Message.unread.unread_count_for_user(request.user)
        return Response({'unread_count': count})

    @action(detail=False, methods=['post'])
    def mark_as_read(self, request):
        """
        Mark messages as read for the current user
        Not cached since it's a write operation
        """
        message_ids = request.data.get('message_ids', [])

        if message_ids:
            # Mark specific messages as read
            updated_count = Message.unread.mark_as_read(
                request.user, message_ids)
        else:
            # Mark all unread messages as read
            updated_count = Message.unread.mark_as_read(request.user)

        return Response({
            'message': f'Successfully marked {updated_count} messages as read',
            'updated_count': updated_count
        })

    @action(detail=True, methods=['post'])
    def mark_single_as_read(self, request, pk=None):
        """
        Mark a single message as read
        Not cached since it's a write operation
        """
        try:
            message = Message.objects.get(message_id=pk)

            # Check if user has access to this message
            if not message.conversation.participants.filter(user_id=request.user.user_id).exists():
                return Response(
                    {'error': 'Access denied'},
                    status=status.HTTP_403_FORBIDDEN
                )

            if message.unread:
                message.mark_as_read()
                return Response({'message': 'Message marked as read'})
            else:
                return Response({'message': 'Message was already read'})

        except Message.DoesNotExist:
            return Response(
                {'error': 'Message not found'},
                status=status.HTTP_404_NOT_FOUND
            )

    # Cache for 60 seconds - MAIN CACHED VIEW
    @method_decorator(cache_page(60))
    # Vary cache by authorization header
    @method_decorator(vary_on_headers('Authorization'))
    # Also vary by cookie for additional security
    @method_decorator(vary_on_cookie)
    @action(detail=False, methods=['get'], url_path='conversation/(?P<conversation_id>[^/.]+)')
    def conversation_messages(self, request, conversation_id=None):
        """
        Get all root messages for a specific conversation with their threaded replies
        CACHED for 60 seconds - This is the main view that displays messages in a conversation
        """
        try:
            # Verify user has access to this conversation
            conversation = Conversation.objects.get(
                conversation_id=conversation_id,
                participants=request.user
            )

            # Get root messages (non-replies) with optimized prefetching
            root_messages = Message.objects.filter(
                conversation=conversation,
                parent_message__isnull=True
            ).select_related(
                'sender', 'receiver'
            ).prefetch_related(
                Prefetch(
                    'replies',
                    queryset=Message.objects.select_related('sender', 'receiver').prefetch_related(
                        Prefetch(
                            'replies',
                            queryset=Message.objects.select_related(
                                'sender', 'receiver')
                        )
                    )
                )
            ).order_by('timestamp')

            # Apply filters
            queryset = MessageFilter(request.GET, queryset=root_messages).qs

            # Paginate the results
            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = ThreadedMessageSerializer(
                    page,
                    many=True,
                    context={'request': request, 'max_depth': 3}
                )
                return self.get_paginated_response(serializer.data)

            serializer = ThreadedMessageSerializer(
                queryset,
                many=True,
                context={'request': request, 'max_depth': 3}
            )
            return Response(serializer.data)

        except Conversation.DoesNotExist:
            return Response(
                {'error': 'Conversation not found or access denied'},
                status=status.HTTP_404_NOT_FOUND
            )

    @method_decorator(cache_page(60))  # Cache for 60 seconds
    @method_decorator(vary_on_headers('Authorization'))
    @action(detail=True, methods=['get'])
    def thread(self, request, pk=None):
        """
        Get a specific message with its entire reply thread
        Cached for 60 seconds
        """
        try:
            message = Message.objects.get_message_with_thread(pk)

            # Check if user has access to this message's conversation
            if not message.conversation.participants.filter(user_id=request.user.user_id).exists():
                return Response(
                    {'error': 'Access denied'},
                    status=status.HTTP_403_FORBIDDEN
                )

            serializer = ThreadedMessageSerializer(
                message,
                context={'request': request, 'max_depth': 10}
            )
            return Response(serializer.data)

        except Message.DoesNotExist:
            return Response(
                {'error': 'Message not found'},
                status=status.HTTP_404_NOT_FOUND
            )

    @method_decorator(cache_page(60))  # Cache list view for 60 seconds
    @method_decorator(vary_on_headers('Authorization'))
    def list(self, request, *args, **kwargs):
        """
        List all messages for the current user
        Cached for 60 seconds
        """
        return super().list(request, *args, **kwargs)

    @method_decorator(cache_page(60))  # Cache retrieve view for 60 seconds
    @method_decorator(vary_on_headers('Authorization'))
    def retrieve(self, request, *args, **kwargs):
        """
        Retrieve a specific message
        Cached for 60 seconds
        """
        return super().retrieve(request, *args, **kwargs)

    @action(detail=True, methods=['post'])
    def reply(self, request, pk=None):
        """
        Create a reply to a specific message
        Not cached since it's a write operation
        """
        try:
            parent_message = Message.objects.get(message_id=pk)

            # Check if user has access to this message's conversation
            if not parent_message.conversation.participants.filter(user_id=request.user.user_id).exists():
                return Response(
                    {'error': 'Access denied'},
                    status=status.HTTP_403_FORBIDDEN
                )

            serializer = MessageCreateSerializer(data=request.data)
            if serializer.is_valid():
                # Ensure the reply is in the same conversation as the parent
                reply_data = serializer.validated_data
                if reply_data.get('conversation') != parent_message.conversation:
                    return Response(
                        {'error': 'Reply must be in the same conversation'},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                # Create the reply
                reply = Message.objects.create(
                    conversation=parent_message.conversation,
                    sender=request.user,
                    parent_message=parent_message,
                    content=reply_data['content']
                )

                response_serializer = ThreadedMessageSerializer(
                    reply,
                    context={'request': request}
                )
                return Response(response_serializer.data, status=status.HTTP_201_CREATED)

            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        except Message.DoesNotExist:
            return Response(
                {'error': 'Parent message not found'},
                status=status.HTTP_404_NOT_FOUND
            )

# Additional cached view function using @cache_page decorator directly


@api_view(['GET'])
@cache_page(60)  # Cache for 60 seconds
@vary_on_headers('Authorization')
def cached_conversation_messages(request, conversation_id):
    """
    Alternative cached view for conversation messages using function-based view
    """
    from .models import Conversation, Message
    from .serializers import ThreadedMessageSerializer

    try:
        # Verify user has access to this conversation
        conversation = Conversation.objects.get(
            conversation_id=conversation_id,
            participants=request.user
        )

        # Get root messages with optimized prefetching
        root_messages = Message.objects.filter(
            conversation=conversation,
            parent_message__isnull=True
        ).select_related('sender', 'receiver').order_by('timestamp')

        serializer = ThreadedMessageSerializer(
            root_messages,
            many=True,
            context={'request': request, 'max_depth': 3}
        )
        return Response(serializer.data)

    except Conversation.DoesNotExist:
        return Response(
            {'error': 'Conversation not found or access denied'},
            status=status.HTTP_404_NOT_FOUND
        )
