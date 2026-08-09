#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Copyright (C) 2025 David Ferraes
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""
Icinga 2 to Pushover Notification Script

This script sends notifications from Icinga 2 to the Pushover service.
It is designed to be called by Icinga 2's notification system.
"""

import argparse
import http.client
import sys
import urllib.parse

# --- API limits ---

# Pushover rejects an oversized request outright, so a long check output would
# lose the whole notification instead of arriving clipped. Cut it ourselves.
MAX_TITLE_LENGTH = 250
MAX_MESSAGE_LENGTH = 1024

# A notification path that can block forever is worse than one that fails:
# Icinga runs this synchronously, and the network is exactly what tends to be
# broken when an alert fires.
API_TIMEOUT_SECONDS = 10

# --- Customization ---

# Sound mapping for different notification types
SOUND_MAP = {
    "PROBLEM": "siren",
    "RECOVERY": "magic",
    "ACKNOWLEDGEMENT": "pushover",
    "DOWNTIMESTART": "pushover",
    "DOWNTIMEEND": "pushover",
    "DOWNTIMEREMOVED": "pushover",
    "CUSTOM": "pushover",
    "FLAPPINGSTART": "pushover",
    "FLAPPINGEND": "pushover",
}

# Priority mapping for different states.
# '2' is emergency priority, '1' is high priority.
PRIORITY_MAP = {
    "DOWN": 2,
    "CRITICAL": 2,
    "UP": 0,
    "OK": 0,
    "WARNING": 1,
    "UNKNOWN": 1,
}

# --- Internationalization (i18n) ---

TRANSLATIONS = {
    "en": {
        "HOST_NOTIFICATION_TITLE": "Host {hostdisplayname} is {state}",
        "SERVICE_NOTIFICATION_TITLE": (
            "Service {servicedisplayname} on {hostdisplayname} is {state}"
        ),
        "OUTPUT": "Output",
        "AUTHOR": "Author",
        "COMMENT": "Comment",
        "NOTES": "Notes",
        "URL_TITLE": "View in Icinga Web 2",
    },
    "es": {
        "HOST_NOTIFICATION_TITLE": "El Host {hostdisplayname} está {state}",
        "SERVICE_NOTIFICATION_TITLE": (
            "El Servicio {servicedisplayname} en {hostdisplayname} está {state}"
        ),
        "OUTPUT": "Salida",
        "AUTHOR": "Autor",
        "COMMENT": "Comentario",
        "NOTES": "Notas",
        "URL_TITLE": "Ver en Icinga Web 2",
    },
    # Add other languages here
}


def get_translation(lang, key):
    """
    Gets a translation for a given key and language.
    Falls back to English if the translation is not available.
    """
    return TRANSLATIONS.get(lang, TRANSLATIONS["en"]).get(key, TRANSLATIONS["en"].get(key))


def parse_arguments():
    """Parses command-line arguments."""
    parser = argparse.ArgumentParser(description="Send Icinga 2 notifications to Pushover.")
    parser.add_argument("--token", required=True, help="Pushover API Token")
    parser.add_argument("--user", required=True, help="Pushover User Key")
    parser.add_argument(
        "--notificationtype",
        required=True,
        help="Notification type (e.g., PROBLEM, RECOVERY)",
    )
    parser.add_argument("--hostdisplayname", required=True, help="Host display name")
    parser.add_argument(
        "--servicedisplayname", help="Service display name (for service notifications)"
    )
    parser.add_argument("--state", required=True, help="Host or service state")
    parser.add_argument("--output", required=True, help="Check output")
    parser.add_argument("--lang", default="en", help="Language for the notification")
    parser.add_argument("--notification_author", help="Notification author")
    parser.add_argument("--notification_comment", help="Notification comment")
    parser.add_argument("--notification_hostnotes", help="Host notes")
    parser.add_argument("--notification_servicenotes", help="Service notes")
    parser.add_argument("--icingaweb2_base_url", help="Base URL for Icinga Web 2")
    parser.add_argument("--url_title", help="Custom title for the URL")
    parser.add_argument("--retry", default="30", help="Retry interval for emergency notifications")
    parser.add_argument("--expire", default="3600", help="Expiration for emergency notifications")
    return parser.parse_args()


def construct_message_body(args, lang):
    """Constructs the notification message body."""
    body_parts = [f"<b>{get_translation(lang, 'OUTPUT')}:</b> {args.output}"]

    if args.notification_author:
        body_parts.append(f"<b>{get_translation(lang, 'AUTHOR')}:</b> {args.notification_author}")
    if args.notification_comment:
        body_parts.append(f"<b>{get_translation(lang, 'COMMENT')}:</b> {args.notification_comment}")

    notes = (
        args.notification_servicenotes if args.servicedisplayname else args.notification_hostnotes
    )
    if notes:
        body_parts.append(f"<b>{get_translation(lang, 'NOTES')}:</b> {notes}")

    return "\n".join(body_parts)


def construct_icinga_url(args):
    """Constructs the Icinga Web 2 URL for the host or service."""
    if not args.icingaweb2_base_url:
        return None

    base_url = args.icingaweb2_base_url.rstrip("/")
    if args.servicedisplayname:
        # Service URL
        params = urllib.parse.urlencode(
            {"host": args.hostdisplayname, "service": args.servicedisplayname}
        )
        return f"{base_url}/monitoring/service/show?{params}"

    # Host URL
    params = urllib.parse.urlencode({"host": args.hostdisplayname})
    return f"{base_url}/monitoring/host/show?{params}"


def truncate(text, limit):
    """Shortens text to at most limit characters, marking where it was cut."""
    if text is None or len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


def send_pushover_notification(payload):
    """Sends the notification to the Pushover API."""
    conn = http.client.HTTPSConnection("api.pushover.net:443", timeout=API_TIMEOUT_SECONDS)
    try:
        conn.request(
            "POST",
            "/1/messages.json",
            urllib.parse.urlencode(payload),
            {"Content-type": "application/x-www-form-urlencoded"},
        )
        response = conn.getresponse()
        body = response.read()
    except OSError as exc:
        # Covers DNS failures, refused connections and the socket timeout.
        print(f"Could not reach the Pushover API: {exc}", file=sys.stderr)
        sys.exit(1)
    finally:
        conn.close()

    if response.status < 200 or response.status >= 300:
        print(
            f"Pushover API request failed: {response.status} {response.reason}",
            file=sys.stderr,
        )
        print(body.decode(errors="replace"), file=sys.stderr)
        sys.exit(1)
    else:
        print("Pushover notification sent successfully.")


def main():
    """Main function to process arguments and send notification."""
    args = parse_arguments()
    lang = args.lang

    # Determine title
    if args.servicedisplayname:
        title = get_translation(lang, "SERVICE_NOTIFICATION_TITLE").format(
            servicedisplayname=args.servicedisplayname,
            hostdisplayname=args.hostdisplayname,
            state=args.state,
        )
    else:
        title = get_translation(lang, "HOST_NOTIFICATION_TITLE").format(
            hostdisplayname=args.hostdisplayname,
            state=args.state,
        )

    # Construct message body
    message = construct_message_body(args, lang)

    # Determine sound and priority
    sound = SOUND_MAP.get(args.notificationtype, "pushover")
    priority = PRIORITY_MAP.get(args.state, 0)

    # Construct payload for Pushover API
    payload = {
        "token": args.token,
        "user": args.user,
        "title": truncate(title, MAX_TITLE_LENGTH),
        "message": truncate(message, MAX_MESSAGE_LENGTH),
        "sound": sound,
        "priority": priority,
        "html": 1,  # Enable HTML formatting in the message
    }

    # Add URL if Icinga Web 2 base URL is provided
    icinga_url = construct_icinga_url(args)
    if icinga_url:
        payload["url"] = icinga_url
        payload["url_title"] = args.url_title or get_translation(lang, "URL_TITLE")

    # Add retry and expire for emergency notifications
    if priority == 2:
        payload["retry"] = args.retry
        payload["expire"] = args.expire

    # Send notification
    send_pushover_notification(payload)


if __name__ == "__main__":
    main()
