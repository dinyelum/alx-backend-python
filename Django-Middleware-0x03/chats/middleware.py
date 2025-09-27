import os
from datetime import datetime, time, timedelta
from django.conf import settings
from django.http import HttpResponseForbidden
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
        # Rate limit: 5 messages per minute
        self.max_messages = 5
        self.time_window = 60  # seconds

        # Track messages by IP
        self.message_counts = defaultdict(list)

    def __call__(self, request):
        # Only check POST requests to chat endpoints
        if request.method == 'POST' and self.is_chat_endpoint(request.path):
            ip = self.get_client_ip(request)

            # Clean old messages
            self.clean_old_messages(ip)

            # Check if limit exceeded
            if len(self.message_counts[ip]) >= self.max_messages:
                return HttpResponseForbidden(
                    "<h1>429 Too Many Requests</h1>"
                    "<p>You have exceeded the limit of 5 messages per minute.</p>"
                    "<p>Please wait before sending more messages.</p>"
                )

            # Record this message
            self.message_counts[ip].append(datetime.now())

        return self.get_response(request)

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        return x_forwarded_for.split(',')[0] if x_forwarded_for else request.META.get('REMOTE_ADDR')

    def is_chat_endpoint(self, path):
        chat_patterns = [r'^/chat/', r'^/messages/', r'^/api/chat/']
        return any(re.match(pattern, path) for pattern in chat_patterns)

    def clean_old_messages(self, ip):
        cutoff = datetime.now() - timedelta(seconds=self.time_window)
        self.message_counts[ip] = [
            t for t in self.message_counts[ip] if t > cutoff]
