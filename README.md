# Icinga 2 to Pushover Notifications

A small Python script that sends Icinga 2 host and service alerts to
[Pushover](https://pushover.net/). It uses only the standard library, so there
is nothing to install beyond Python itself.

![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)

## Features

- **Host and service notifications**, with titles built from the alert.
- **No external dependencies** — standard library only, verified in CI.
- **Internationalization** — English and Spanish included; unknown languages
  fall back to English.
- **Custom sounds** — `siren` for problems, `magic` for recoveries, and a
  mapping you can edit.
- **Emergency priority** — `DOWN` and `CRITICAL` are sent at priority 2, which
  bypasses quiet hours and repeats until acknowledged.
- **Rich context** — check output plus the author, comment and notes.
- **Deep links** — an optional button that opens the object in Icinga Web 2.

## Requirements

- Python 3.9+ (CI covers 3.9, 3.11 and 3.13).
- A running Icinga 2 instance with outbound HTTPS to `api.pushover.net`.
- A Pushover account with an application API token and a user key.

## Installation

The script has no dependencies, so a virtual environment buys nothing here —
copy it in and make it executable:

```bash
sudo cp pushover_notifications.py /etc/icinga2/scripts/
sudo chmod +x /etc/icinga2/scripts/pushover_notifications.py
```

## Icinga 2 configuration

Icinga 2 has no generic "current object" macro, and `||` inside an argument
string is not evaluated — it would be sent to the script as literal text. Host
and service notifications therefore need one `NotificationCommand` each.

```icinga2
object NotificationCommand "pushover-host-notification" {
  command = [ "/etc/icinga2/scripts/pushover_notifications.py" ]

  arguments = {
    "--token"            = PushoverToken
    "--user"             = PushoverUserKey
    "--notificationtype" = "$notification.type$"
    "--hostdisplayname"  = "$host.display_name$"
    "--state"            = "$host.state$"
    "--output"           = "$host.output$"
    "--lang"             = "$user.vars.lang$"

    "--notification_author"    = "$notification.author$"
    "--notification_comment"   = "$notification.comment$"
    "--notification_hostnotes" = "$host.notes$"
    "--icingaweb2_base_url"    = "https://icinga.example.com/icingaweb2"

    // Optional, only used for emergency (priority 2) notifications:
    // "--retry"  = "60"    // default 30 seconds
    // "--expire" = "7200"  // default 3600 seconds
  }
}

object NotificationCommand "pushover-service-notification" {
  command = [ "/etc/icinga2/scripts/pushover_notifications.py" ]

  arguments = {
    "--token"              = PushoverToken
    "--user"               = PushoverUserKey
    "--notificationtype"   = "$notification.type$"
    "--hostdisplayname"    = "$host.display_name$"
    "--servicedisplayname" = "$service.display_name$"
    "--state"              = "$service.state$"
    "--output"             = "$service.output$"
    "--lang"               = "$user.vars.lang$"

    "--notification_author"       = "$notification.author$"
    "--notification_comment"      = "$notification.comment$"
    "--notification_servicenotes" = "$service.notes$"
    "--icingaweb2_base_url"       = "https://icinga.example.com/icingaweb2"
  }
}
```

The script picks the service layout when `--servicedisplayname` arrives with a
value, and the host layout otherwise.

**Credentials.** Keep the token and user key in `constants.conf` and restrict
that file (`chmod 600`) rather than writing them into a command definition:

```icinga2
// In /etc/icinga2/constants.conf
const PushoverToken = "your-application-api-token"
const PushoverUserKey = "your-user-key"
```

**Per-user language (optional).** `--lang` defaults to English when the value is
missing or unknown:

```icinga2
object User "juan" {
  email = "juan@example.com"
  vars.lang = "es"
}
```

**Apply rules:**

```icinga2
apply Notification "pushover-host-notification" to Host {
  import "generic-host-notification"
  command = "pushover-host-notification"
  users = [ "icingaadmin" ]
  assign where host.address
}

apply Notification "pushover-service-notification" to Service {
  import "generic-service-notification"
  command = "pushover-service-notification"
  users = [ "icingaadmin" ]
  assign where service.check_command
}
```

**Validate and reload:**

```bash
sudo icinga2 daemon -C
sudo systemctl reload icinga2
```

## Customization

- **Sounds** — edit `SOUND_MAP` at the top of the script. The available names
  are listed in the Pushover API documentation.
- **Priorities** — edit `PRIORITY_MAP`. Valid values are `-2` (silent) through
  `2` (emergency); `2` also sends `retry` and `expire`.
- **Languages** — add a key to `TRANSLATIONS` with the same entries as `en`.

## Limitations

- **The token and user key are passed as command-line arguments**, which makes
  them visible in the process list to other users on the Icinga host. This is
  how Icinga 2 passes arguments to notification commands; if that matters in
  your environment, restrict shell access on that machine.
- **Titles are cut at 250 characters and messages at 1024**, which is what the
  Pushover API accepts. A longer check output arrives clipped rather than
  being rejected outright.
- **Check output is sent with `html=1` and is not escaped**, so output
  containing `<` or `>` may render oddly on the device.
- **Links target the legacy `monitoring` module** (`/monitoring/host/show`).
  Installations that use Icinga DB Web need a different path.

## Testing

Unit tests mock the HTTP layer, so no notification is sent and no network is
touched:

```bash
python3 -m unittest discover
```

To send one real notification and confirm your credentials and connectivity:

```bash
python3 send_test_notification.py --token YOUR_TOKEN --user YOUR_USER
```

## Contributing

Issues and pull requests are welcome.

## License

Copyright (C) 2025 David Ferraes.

This program is free software: you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation, either version 3 of the License, or (at your option) any later
version. See [LICENSE](LICENSE) for the full text.
