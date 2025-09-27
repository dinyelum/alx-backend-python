import os
from datetime import datetime, time
from django.conf import settings
from django.http import HttpResponseForbidden
import re


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
