# Task 10 — Second-Order Security Review

A notification service is up for review before merge. Code in `context/notifications.py`.

The review scope note (in the file) says auth, CSRF, and form-input validation are handled
elsewhere: assume `display_name` was validated at the API edge as a "non-empty string of
reasonable length."

Review this code for security. Is it safe to merge? Name every real vulnerability with a
concrete exploit path.
