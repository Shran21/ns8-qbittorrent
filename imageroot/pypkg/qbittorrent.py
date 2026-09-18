#
# Copyright (C) 2025 Nethesis S.r.l.
# SPDX-License-Identifier: GPL-3.0-or-later
#

"""Shared settings helpers for the ns8-qbittorrent module.

Every setting handled here ends up in the agent ``state/environment``
file, which is read by the Systemd units and is always included in the
module backup. Because that file is expanded by Systemd and its values are
stored raw -- they are not quoted nor escaped -- user supplied values are
validated strictly before being stored.
"""

import os
import re

import agent

# The named volume used when the administrator does not provide a custom
# downloads path.
DOWNLOADS_VOLUME = "qbittorrent-downloads"
CONFIG_VOLUME = "qbittorrent-config"

DEFAULT_BT_PORT = 6881
DEFAULT_UMASK = "002"
DEFAULT_TZ = "UTC"

# An absolute path made of "ordinary" characters. Anything outside this set
# (spaces, colons, commas, quotes, dollar signs, backslashes...) is refused:
# such characters would either break the Systemd environment file syntax or
# let the value inject extra arguments into `podman run --volume`.
DOWNLOADS_DIR_RE = re.compile(r"^/[A-Za-z0-9._@+-]+(?:/[A-Za-z0-9._@+-]+)*$")


def build_downloads_mount(downloads_dir):
    """Return the `podman run --volume` argument for /downloads.

    An empty or missing ``downloads_dir`` selects the named volume, which
    needs no SELinux relabelling. A custom host path is bind-mounted with
    the shared ``z`` label, so that a directory shared with other services
    (a media server, for instance) keeps working.
    """
    if not downloads_dir:
        return f"{DOWNLOADS_VOLUME}:/downloads"
    return f"{downloads_dir}:/downloads:z"


def parse_downloads_mount(downloads_mount):
    """Inverse of :func:`build_downloads_mount`: return the custom path, or
    an empty string when the named volume is in use."""
    if not downloads_mount or downloads_mount.startswith(DOWNLOADS_VOLUME + ":"):
        return ""
    return downloads_mount.split(":", 1)[0]


def validate_downloads_dir(downloads_dir):
    """Return an error identifier, or None when the path is acceptable.

    The identifier matches a key of the UI translation catalog.
    """
    if not downloads_dir:
        return None  # the named volume will be used

    if not DOWNLOADS_DIR_RE.match(downloads_dir) or "/.." in downloads_dir + "/":
        return "downloads_dir_invalid"

    if not os.path.isdir(downloads_dir):
        return "downloads_dir_not_found"

    # The container runs as PUID=0, which is mapped to the module user on
    # the host, so this process and the application share one identity:
    # testing access here tells us exactly what the container will get.
    if not os.access(downloads_dir, os.W_OK | os.X_OK):
        return "downloads_dir_not_writable"

    return None


def validate_bt_port(bt_port):
    """Return an error identifier, or None when the port is acceptable."""
    if not isinstance(bt_port, int) or isinstance(bt_port, bool):
        return "bt_port_invalid"
    if not 1024 <= bt_port <= 65535:
        return "bt_port_invalid"
    return None


def read_settings(environ=None):
    """Return the current settings as the get-configuration output."""
    if environ is None:
        environ = os.environ
    return {
        "host": environ.get("TRAEFIK_HOST", ""),
        "http2https": environ.get("TRAEFIK_HTTP2HTTPS", "") == "True",
        "lets_encrypt": environ.get("TRAEFIK_LETS_ENCRYPT", "") == "True",
        "downloads_dir": parse_downloads_mount(environ.get("DOWNLOADS_MOUNT", "")),
        "bt_port": int(environ.get("BT_PORT", DEFAULT_BT_PORT)),
        "bt_port_enabled": environ.get("BT_PORT_ENABLED", "1") == "1",
        "umask": environ.get("UMASK", DEFAULT_UMASK),
        "timezone": environ.get("TZ", DEFAULT_TZ),
    }


def set_many(envmap):
    """Store several environment variables at once.

    agent.mset_env() is the efficient call, but it is not available on
    older cores: fall back to repeated set_env() calls there.
    """
    mset_env = getattr(agent, "mset_env", None)
    if mset_env is not None:
        mset_env(envmap)
        return
    for name, value in envmap.items():
        agent.set_env(name, value)


def unset_many(names):
    """Remove several environment variables, with the same fallback."""
    munset_env = getattr(agent, "munset_env", None)
    if munset_env is not None:
        munset_env(names)
        return
    for name in names:
        agent.unset_env(name)
