#!/usr/bin/env python3
#
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 David Ferraes
#
# Pushover Real Notification Test Script
#
# This script sends a REAL notification to Pushover to test credentials
# and connectivity. It reuses the notification logic from the main script.
#
# Required arguments:
#   - --token: Your Pushover application's API token.
#   - --user: Your Pushover user key.

import argparse
import sys
import os

# Make the import of the sibling script robust by adding its directory to the path
script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

# Import the core function from the main Icinga2 script
try:
    from pushover_notifications import send_pushover_notification
except ImportError:
    print(
        "Error: Make sure 'pushover_notifications.py' is in the same directory.",
        file=sys.stderr,
    )
    sys.exit(1)


def main():
    """
    Parses arguments and sends a real test notification.
    """
    parser = argparse.ArgumentParser(
        description="Send a real test notification using the Icinga 2 Pushover script.",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument("--token", required=True, help="Pushover application token.")
    parser.add_argument("--user", required=True, help="Pushover user key.")
    parser.add_argument(
        "--title",
        default="Test Notification from Icinga 2 Script",
        help="The title of the notification.",
    )
    parser.add_argument(
        "--message",
        default="This is a test message to confirm your Pushover setup is working.",
        help="The body of the notification. Supports HTML.",
    )
    parser.add_argument(
        "--sound",
        help='The sound to use for the notification (e.g., "magic", "siren").',
    )
    parser.add_argument("--url", help="A URL to attach to the notification.")
    parser.add_argument("--url_title", help="The title for the attached URL.")
    parser.add_argument(
        "--priority",
        type=int,
        choices=[-2, -1, 0, 1, 2],
        help="Notification priority (-2 to 2).",
    )
    parser.add_argument(
        "--retry",
        default="30",
        help="Retry interval for emergency priority (priority=2).",
    )
    parser.add_argument(
        "--expire",
        default="3600",
        help="Expiration time for emergency priority (priority=2).",
    )

    args = parser.parse_args()

    # Construct the payload dictionary for the Pushover API
    payload = {
        "token": args.token,
        "user": args.user,
        "title": args.title,
        "message": args.message,
        "html": 1,  # Enable HTML in the test message by default
    }

    if args.sound:
        payload["sound"] = args.sound

    if args.url:
        payload["url"] = args.url
    if args.url_title:
        payload["url_title"] = args.url_title

    if args.priority is not None:
        payload["priority"] = args.priority
        # Add retry/expire only for emergency priority notifications
        if args.priority == 2:
            payload["retry"] = args.retry
            payload["expire"] = args.expire

    print("Attempting to send a real test notification...")

    # The send_pushover_notification function will print success/error messages
    # and exit on failure, so we don't need extensive error handling here.
    send_pushover_notification(payload)


if __name__ == "__main__":
    main()
