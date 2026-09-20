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

import errno
import ipaddress
import os
import re
import socket

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


def parse_auth_whitelist(value):
    """Split a comma separated subnet list into normalised CIDR strings.

    Raises ValueError on anything that is not a network, so the caller can
    turn it into a validation error instead of writing a list qBittorrent
    would silently ignore.
    """
    subnets = []
    for chunk in (value or "").replace(";", ",").split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        # strict=False accepts 192.168.0.1/24 and normalises it to the
        # network address, which is what an administrator usually means.
        subnets.append(str(ipaddress.ip_network(chunk, strict=False)))
    return subnets


def validate_auth_whitelist(value):
    """Return an error identifier, or None when the list is acceptable."""
    try:
        parse_auth_whitelist(value)
    except ValueError:
        return "auth_whitelist_invalid"
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
        "auth_whitelist": environ.get("AUTH_WHITELIST", ""),
    }


def build_bt_publish(bt_port, enabled):
    """Return the `podman pod create` publish arguments for the BitTorrent port.

    The unit expands this with $BT_PUBLISH (unbraced), which systemd splits
    on whitespace, so an empty value means "publish nothing". Publishing
    the port unconditionally and relying on the firewall to block it would
    still bind the host port, which breaks a clone or a migrated instance
    that deliberately keeps the port closed while the original still holds
    it.
    """
    if not enabled:
        return ""
    return f"--publish={bt_port}:{bt_port}/tcp --publish={bt_port}:{bt_port}/udp"


def port_in_use(port):
    """True when the port is already bound on this host.

    Both protocols are tested, because the pod publishes the BitTorrent
    port over TCP and UDP alike and `podman pod create` fails if either one
    is taken. Address families that the kernel does not offer are skipped
    rather than raised: a node with IPv6 disabled must still be able to
    validate a port.
    """
    for family in (socket.AF_INET, socket.AF_INET6):
        for socktype in (socket.SOCK_STREAM, socket.SOCK_DGRAM):
            try:
                with socket.socket(family, socktype) as sock:
                    sock.bind(("", port))
            except OSError as ex:
                if ex.errno == errno.EADDRINUSE:
                    return True
                continue
    return False


def settings_env(settings):
    """Map a settings dict (the configure-module input shape) to the
    environment variables the Systemd units read."""
    bt_port = int(settings.get("bt_port", DEFAULT_BT_PORT))
    bt_port_enabled = bool(settings.get("bt_port_enabled", True))
    return {
        "DOWNLOADS_MOUNT": build_downloads_mount(settings.get("downloads_dir", "")),
        "BT_PORT": str(bt_port),
        "BT_PORT_ENABLED": "1" if bt_port_enabled else "",
        "BT_PUBLISH": build_bt_publish(bt_port, bt_port_enabled),
        "UMASK": settings.get("umask") or DEFAULT_UMASK,
        "TZ": settings.get("timezone") or DEFAULT_TZ,
        # Comma separated CIDR list. Empty means "always ask for a password".
        "AUTH_WHITELIST": ",".join(parse_auth_whitelist(settings.get("auth_whitelist", ""))),
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
