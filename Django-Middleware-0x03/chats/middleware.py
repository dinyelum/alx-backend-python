from datetime import datetime, time
from django.http import HttpResponseForbidden


class RestrictAccessByTimeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Get current server time
        current_time = datetime.now().time()

        # Define restricted hours (9 PM to 6 AM)
        restricted_start = time(21, 0)  # 9:00 PM
        restricted_end = time(6, 0)     # 6:00 AM

        # Check if current time is within restricted hours
        if self.is_restricted_time(current_time, restricted_start, restricted_end):
            return HttpResponseForbidden(
                "<h1>403 Forbidden</h1>"
                "<p>Access to messaging services is restricted between 9:00 PM and 6:00 AM.</p>"
                "<p>Please try again during permitted hours.</p>"
            )

        # If outside restricted hours, process normally
        response = self.get_response(request)
        return response

    def is_restricted_time(self, current_time, start_time, end_time):
        """Check if current time is within restricted hours (9 PM to 6 AM)"""
        if start_time <= end_time:
            # Normal case: start < end
            return start_time <= current_time <= end_time
        else:
            # Overnight case: start > end (9 PM to 6 AM)
            return current_time >= start_time or current_time <= end_time
