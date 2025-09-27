import os
from datetime import datetime, time, timedelta
from django.conf import settings
from django.http import HttpResponseForbidden, JsonResponse
import re
from collections import defaultdict


class RequestLoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        # Ensure the log file directory exists
        log_file = getattr(settings, 'REQUEST_LOG_FILE', 'requests.log')
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)

    def __call__(self, request):
        # Get the user information
        user = "Anonymous"
        if hasattr(request, 'user') and request.user.is_authenticated:
            user = request.user.username

        # Process the request
        response = self.get_response(request)

        # Log the request information
        log_entry = f"{datetime.now()} - User: {user} - Path: {request.path}\n"

        # Write to the log file
        log_file_path = getattr(settings, 'REQUEST_LOG_FILE', 'requests.log')
        try:
            with open(log_file_path, 'a') as log_file:
                log_file.write(log_entry)
        except Exception as e:
            # If logging fails, print to console as fallback
            print(f"Failed to write to log file: {e}")
            print(log_entry)

        return response


class RestrictAccessByTimeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        # Define restricted hours (9 PM to 6 AM)
        self.restricted_start = time(21, 0)  # 9:00 PM
        self.restricted_end = time(6, 0)     # 6:00 AM

        # Define paths that should be restricted (messaging-related URLs)
        self.restricted_paths = [
            r'^/messages/',
            r'^/chat/',
            r'^/messaging/',
            r'^/api/chat/',
            r'^/api/messages/',
        ]

    def __call__(self, request):
        # Check if the current path matches any restricted paths
        if self.is_restricted_path(request.path):
            # Get current server time
            current_time = datetime.now().time()

            # Check if current time is within restricted hours
            if self.is_restricted_time(current_time):
                return HttpResponseForbidden(
                    "<h1>403 Forbidden</h1>"
                    "<p>Access to messaging services is restricted between 9:00 PM and 6:00 AM.</p>"
                    "<p>Please try again during permitted hours.</p>"
                )

        # If not restricted or outside restricted hours, process normally
        response = self.get_response(request)
        return response

    def is_restricted_path(self, path):
        """Check if the requested path matches any restricted patterns"""
        for pattern in self.restricted_paths:
            if re.match(pattern, path):
                return True
        return False

    def is_restricted_time(self, current_time):
        """Check if current time is within restricted hours (9 PM to 6 AM)"""
        if self.restricted_start <= self.restricted_end:
            # Normal case: start < end (e.g., 9 AM to 5 PM)
            return self.restricted_start <= current_time <= self.restricted_end
        else:
            # Overnight case: start > end (e.g., 9 PM to 6 AM)
            return current_time >= self.restricted_start or current_time <= self.restricted_end


class OffensiveLanguageMiddleware:
    """
    Middleware that limits the number of chat messages a user can send 
    within a certain time window based on their IP address.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        # Rate limiting settings
        self.max_requests = getattr(
            settings, 'RATE_LIMIT_MAX_REQUESTS', 5)  # 5 messages
        self.time_window = getattr(
            settings, 'RATE_LIMIT_WINDOW', 60)  # 60 seconds (1 minute)

        # Define chat message paths (POST requests to these paths will be rate limited)
        self.chat_paths = [
            r'^/messages/send/',
            r'^/chat/send/',
            r'^/messaging/send/',
            r'^/api/chat/send/',
            r'^/api/messages/send/',
            r'^/send-message/',
        ]

        # Storage for request counts (in production, use Redis or database)
        self.request_counts = defaultdict(list)

    def __call__(self, request):
        # Check if this is a POST request to a chat message endpoint
        if request.method == 'POST' and self.is_chat_message_path(request.path):
            # Get client IP address
            ip_address = self.get_client_ip(request)

            # Clean old requests outside the time window
            self.clean_old_requests(ip_address)

            # Check if rate limit is exceeded
            if self.is_rate_limited(ip_address):
                return self.rate_limit_exceeded_response(request)

            # Add current request to the count
            self.add_request(ip_address)

        # Process the request normally
        response = self.get_response(request)
        return response

    def get_client_ip(self, request):
        """Extract client IP address from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

    def is_chat_message_path(self, path):
        """Check if the path matches chat message endpoints"""
        for pattern in self.chat_paths:
            if re.match(pattern, path):
                return True
        return False

    def clean_old_requests(self, ip_address):
        """Remove requests older than the time window"""
        now = datetime.now()
        cutoff_time = now - timedelta(seconds=self.time_window)

        # Keep only requests within the time window
        self.request_counts[ip_address] = [
            timestamp for timestamp in self.request_counts[ip_address]
            if timestamp > cutoff_time
        ]

    def is_rate_limited(self, ip_address):
        """Check if IP address has exceeded rate limit"""
        return len(self.request_counts[ip_address]) >= self.max_requests

    def add_request(self, ip_address):
        """Add current request timestamp to the IP's request history"""
        self.request_counts[ip_address].append(datetime.now())

    def rate_limit_exceeded_response(self, request):
        """Return appropriate response when rate limit is exceeded"""
        if request.headers.get('Content-Type') == 'application/json' or request.path.startswith('/api/'):
            return JsonResponse({
                'error': 'Rate limit exceeded',
                'message': f'You can only send {self.max_requests} messages per {self.time_window} seconds.',
                'retry_after': self.get_retry_after(request)
            }, status=429)
        else:
            return HttpResponseForbidden(
                f"<h1>429 Too Many Requests</h1>"
                f"<p>Rate limit exceeded. You can only send {self.max_requests} messages per {self.time_window//60} minute(s).</p>"
                f"<p>Please wait and try again later.</p>"
            )

    def get_retry_after(self, request):
        """Calculate when the user can retry (for API responses)"""
        if not self.request_counts:
            return self.time_window

        ip_address = self.get_client_ip(request)
        if ip_address in self.request_counts and self.request_counts[ip_address]:
            oldest_request = min(self.request_counts[ip_address])
            next_available = oldest_request + \
                timedelta(seconds=self.time_window)
            return int((next_available - datetime.now()).total_seconds())

        return self.time_window


class RolepermissionMiddleware:
    """
    Middleware that checks the user's role before allowing access to specific actions.
    If the user is not admin or moderator, it returns error 403.
    """

    def __init__(self, get_response):
        self.get_response = get_response

        # Paths that require admin/moderator access
        self.admin_paths = [
            r'^/admin/',
            r'^/moderator/',
            r'^/api/admin/',
        ]

    def __call__(self, request):
        # Check if path requires admin permissions
        if self.requires_admin_permission(request.path):
            user = request.user

            # Check if user is authenticated and has admin/moderator role
            if not user.is_authenticated or not self.is_admin_or_moderator(user):
                return HttpResponseForbidden(
                    "<h1>403 Forbidden</h1>"
                    "<p>Admin or moderator role required to access this resource.</p>"
                )

        return self.get_response(request)

    def requires_admin_permission(self, path):
        """Check if the path requires admin permissions"""
        return any(re.match(pattern, path) for pattern in self.admin_paths)

    def is_admin_or_moderator(self, user):
        """Check if user has admin or moderator role"""
        # Check role field
        if hasattr(user, 'role'):
            return user.role.lower() in ['admin', 'moderator', 'superuser']

        # Check Django built-in permissions
        return user.is_superuser or user.is_staff
