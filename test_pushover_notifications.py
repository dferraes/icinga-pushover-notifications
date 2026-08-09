#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 David Ferraes

"""
Unit tests for pushover_notifications.py.

The HTTP layer is mocked throughout, so these never reach the network.

Run with:  python3 -m unittest discover
"""

import unittest
from unittest.mock import patch, MagicMock, call
import sys
import urllib.parse

# Import the script to be tested
# Assuming the script is in the same directory or in python path
import pushover_notifications


class TestPushoverNotificationScript(unittest.TestCase):

    # Tests for send_pushover_notification function

    # === Tests for send_pushover_notification function ===

    @patch("pushover_notifications.http.client.HTTPSConnection")
    @patch("pushover_notifications.sys.exit")
    @patch("builtins.print")
    def test_send_notification_success(self, mock_print, mock_exit, mock_https_connection):
        """Test successful notification sending."""
        # Arrange
        mock_conn_instance = mock_https_connection.return_value
        mock_response = MagicMock()
        mock_response.status = 200
        mock_conn_instance.getresponse.return_value = mock_response
        payload = {
            "token": "fake_token",
            "user": "fake_user",
            "message": "test_message",
        }

        # Act
        pushover_notifications.send_pushover_notification(payload)

        # Assert
        mock_https_connection.assert_called_once_with(
            "api.pushover.net:443",
            timeout=pushover_notifications.API_TIMEOUT_SECONDS,
        )
        expected_payload = urllib.parse.urlencode(payload)
        mock_conn_instance.request.assert_called_once_with(
            "POST",
            "/1/messages.json",
            expected_payload,
            {"Content-type": "application/x-www-form-urlencoded"},
        )
        mock_conn_instance.close.assert_called_once()
        mock_exit.assert_not_called()
        mock_print.assert_called_with("Pushover notification sent successfully.")

    @patch("pushover_notifications.http.client.HTTPSConnection")
    @patch("pushover_notifications.sys.exit")
    @patch("builtins.print")
    def test_send_notification_api_error(self, mock_print, mock_exit, mock_https_connection):
        """Test handling of an API error during notification sending."""
        # Arrange
        mock_conn_instance = mock_https_connection.return_value
        mock_response = MagicMock()
        mock_response.status = 400
        mock_response.reason = "Bad Request"
        mock_response.read.return_value = b'{"errors": ["token is invalid"]}'
        mock_conn_instance.getresponse.return_value = mock_response
        payload = {"token": "invalid_token", "user": "fake_user", "message": "msg"}

        # Act & Assert
        pushover_notifications.send_pushover_notification(payload)
        mock_exit.assert_called_once_with(1)
        self.assertIn(
            call("Pushover API request failed: 400 Bad Request", file=sys.stderr),
            mock_print.call_args_list,
        )
        self.assertIn(
            call('{"errors": ["token is invalid"]}', file=sys.stderr),
            mock_print.call_args_list,
        )

    # === Tests for main function ===

    @patch("pushover_notifications.send_pushover_notification")
    def test_main_host_notification(self, mock_send_notification):
        """Test main function for a host notification."""
        # Arrange
        sys.argv = [
            "pushover_notifications.py",
            "--token",
            "fake_token",
            "--user",
            "fake_user",
            "--notificationtype",
            "PROBLEM",
            "--hostdisplayname",
            "my-host",
            "--state",
            "DOWN",
            "--output",
            "Host is down",
        ]

        # Act
        pushover_notifications.main()

        # Assert
        expected_payload = {
            "token": "fake_token",
            "user": "fake_user",
            "title": "Host my-host is DOWN",
            "message": "<b>Output:</b> Host is down",
            "sound": "siren",
            "priority": 2,
            "html": 1,
            "retry": "30",
            "expire": "3600",
        }
        mock_send_notification.assert_called_once_with(expected_payload)

    @patch("pushover_notifications.send_pushover_notification")
    def test_main_service_notification(self, mock_send_notification):
        """Test main function for a service notification."""
        # Arrange
        sys.argv = [
            "pushover_notifications.py",
            "--token",
            "fake_token",
            "--user",
            "fake_user",
            "--notificationtype",
            "RECOVERY",
            "--hostdisplayname",
            "my-host",
            "--servicedisplayname",
            "check-http",
            "--state",
            "OK",
            "--output",
            "HTTP OK",
        ]

        # Act
        pushover_notifications.main()

        # Assert
        expected_payload = {
            "token": "fake_token",
            "user": "fake_user",
            "title": "Service check-http on my-host is OK",
            "message": "<b>Output:</b> HTTP OK",
            "sound": "magic",
            "priority": 0,
            "html": 1,
        }
        mock_send_notification.assert_called_once_with(expected_payload)

    @patch("pushover_notifications.send_pushover_notification")
    def test_main_service_notification_spanish(self, mock_send_notification):
        """Test main function for a service notification in Spanish."""
        # Arrange
        sys.argv = [
            "pushover_notifications.py",
            "--token",
            "fake_token",
            "--user",
            "fake_user",
            "--notificationtype",
            "PROBLEM",
            "--hostdisplayname",
            "mi-servidor",
            "--servicedisplayname",
            "chequeo-http",
            "--state",
            "CRITICAL",
            "--output",
            "HTTP CRITICO",
            "--lang",
            "es",
        ]

        # Act
        pushover_notifications.main()

        # Assert
        expected_payload = {
            "token": "fake_token",
            "user": "fake_user",
            "title": "El Servicio chequeo-http en mi-servidor está CRITICAL",
            "message": "<b>Salida:</b> HTTP CRITICO",
            "sound": "siren",
            "priority": 2,
            "html": 1,
            "retry": "30",
            "expire": "3600",
        }
        mock_send_notification.assert_called_once_with(expected_payload)

    @patch("pushover_notifications.send_pushover_notification")
    def test_main_notification_with_full_context(self, mock_send_notification):
        """Test main function with all optional context fields."""
        # Arrange
        sys.argv = [
            "pushover_notifications.py",
            "--token",
            "fake_token",
            "--user",
            "fake_user",
            "--notificationtype",
            "PROBLEM",
            "--hostdisplayname",
            "my-host",
            "--servicedisplayname",
            "check-disk",
            "--state",
            "CRITICAL",
            "--output",
            "DISK CRITICAL - /var is 95% full",
            "--notification_author",
            "icingaadmin",
            "--notification_comment",
            "Acknowledged. Investigating.",
            "--notification_hostnotes",
            "This is a host note.",
            "--notification_servicenotes",
            "This is a service note.",
            "--icingaweb2_base_url",
            "https://icinga.example.com/icingaweb2",
        ]

        # Act
        pushover_notifications.main()

        # Assert
        expected_message = (
            "<b>Output:</b> DISK CRITICAL - /var is 95% full\n"
            "<b>Author:</b> icingaadmin\n"
            "<b>Comment:</b> Acknowledged. Investigating.\n"
            "<b>Notes:</b> This is a service note."
        )
        expected_url = (
            "https://icinga.example.com/icingaweb2/monitoring/service/show"
            "?host=my-host&service=check-disk"
        )
        expected_payload = {
            "token": "fake_token",
            "user": "fake_user",
            "title": "Service check-disk on my-host is CRITICAL",
            "message": expected_message,
            "sound": "siren",
            "priority": 2,
            "html": 1,
            "url": expected_url,
            "url_title": "View in Icinga Web 2",
            "retry": "30",
            "expire": "3600",
        }
        mock_send_notification.assert_called_once_with(expected_payload)

    def test_main_missing_args(self):
        """Test that main exits if required arguments are missing."""
        # Arrange
        sys.argv = ["pushover_notifications.py"]  # No arguments
        with self.assertRaises(SystemExit):
            pushover_notifications.main()

    # === Network failure handling ===

    @patch("pushover_notifications.http.client.HTTPSConnection")
    @patch("builtins.print")
    def test_unreachable_api_exits_nonzero(self, mock_print, mock_https_connection):
        """A DNS failure or a timeout must fail loudly, not raise a traceback."""
        mock_conn_instance = mock_https_connection.return_value
        mock_conn_instance.request.side_effect = OSError("Name or service not known")

        with self.assertRaises(SystemExit) as ctx:
            pushover_notifications.send_pushover_notification({"message": "msg"})

        self.assertEqual(ctx.exception.code, 1)
        mock_conn_instance.close.assert_called_once()
        self.assertTrue(
            any("Could not reach the Pushover API" in str(c) for c in mock_print.call_args_list)
        )

    @patch("pushover_notifications.http.client.HTTPSConnection")
    def test_connection_carries_a_timeout(self, mock_https_connection):
        """Without a timeout the notification could hang Icinga indefinitely."""
        mock_conn_instance = mock_https_connection.return_value
        mock_conn_instance.getresponse.return_value = MagicMock(status=200)

        pushover_notifications.send_pushover_notification({"message": "msg"})

        _, kwargs = mock_https_connection.call_args
        self.assertEqual(kwargs["timeout"], pushover_notifications.API_TIMEOUT_SECONDS)
        self.assertGreater(kwargs["timeout"], 0)

    # === Payload size limits ===

    @patch("pushover_notifications.send_pushover_notification")
    def test_long_output_is_truncated(self, mock_send_notification):
        """Pushover rejects a message over 1024 chars, losing the whole alert."""
        sys.argv = [
            "pushover_notifications.py",
            "--token",
            "fake_token",
            "--user",
            "fake_user",
            "--notificationtype",
            "PROBLEM",
            "--hostdisplayname",
            "my-host",
            "--state",
            "CRITICAL",
            "--output",
            "x" * 5000,
        ]

        pushover_notifications.main()

        payload = mock_send_notification.call_args.args[0]
        self.assertEqual(len(payload["message"]), pushover_notifications.MAX_MESSAGE_LENGTH)
        self.assertTrue(payload["message"].endswith("…"))

    @patch("pushover_notifications.send_pushover_notification")
    def test_long_title_is_truncated(self, mock_send_notification):
        sys.argv = [
            "pushover_notifications.py",
            "--token",
            "fake_token",
            "--user",
            "fake_user",
            "--notificationtype",
            "PROBLEM",
            "--hostdisplayname",
            "h" * 400,
            "--state",
            "DOWN",
            "--output",
            "down",
        ]

        pushover_notifications.main()

        payload = mock_send_notification.call_args.args[0]
        self.assertEqual(len(payload["title"]), pushover_notifications.MAX_TITLE_LENGTH)

    def test_short_text_is_left_alone(self):
        self.assertEqual(pushover_notifications.truncate("short", 100), "short")


if __name__ == "__main__":
    unittest.main()
