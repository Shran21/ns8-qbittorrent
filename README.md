# ns8-qbittorrent

A [qBittorrent](https://www.qbittorrent.org/) module for [NethServer 8](https://github.com/NethServer/ns8-core).

It runs [linuxserver/qbittorrent](https://docs.linuxserver.io/images/docker-qbittorrent/)
as a rootless Podman pod and publishes the WebUI through Traefik.

## Install

    add-module ghcr.io/shran21/ns8-qbittorrent:latest 1

The command prints the instance name, for example `ns8-qbittorrent1`. Then
open the app in the cluster UI and fill in the Settings page, or configure
it from the command line:

```
api-cli run configure-module --agent module/ns8-qbittorrent1 --data - <<EOF
{
  "host": "qbittorrent.domain.com",
  "http2https": true,
  "lets_encrypt": false
}
EOF
```

## Update

    update-module ghcr.io/shran21/ns8-qbittorrent:latest ns8-qbittorrent1 --force

`--force` is needed because the `:latest` tag moves: without it NS8 reuses
the image already in the node's local storage and nothing changes.

Your settings are kept. Every update reads the current configuration back
and writes it out again, so an option added by a newer version arrives
with its default while everything you configured stays as it is. The
qBittorrent configuration itself -- limits, categories, credentials and
the torrent list -- lives in the `qbittorrent-config` volume and is never
touched by an update.

## Settings

**Hostname (FQDN)** — the virtual host Traefik publishes the WebUI on,
together with the Let's Encrypt and force-HTTPS switches.

**Trusted networks** — subnets in CIDR notation, comma separated, whose
clients reach the WebUI without a password. Empty means always ask. Set it
here rather than in the qBittorrent WebUI: Traefik forwards every request
from `127.0.0.1`, so the module also enables qBittorrent's reverse proxy
support to make the list match the real client address.

**BitTorrent listen port** — TCP and UDP port for incoming peer
connections, opened in the node firewall when the switch next to it is on.
Forward the same port on your router. Off means outgoing connections only,
which works but finds fewer peers.

**Downloads directory** (Advanced) — an absolute host path to bind-mount,
or empty to use the `qbittorrent-downloads` volume, which the cluster UI
can place on an additional disk. A custom path must already exist and be
writable by the module user; the container runs as that user.

**Time zone** and **file creation mask** (Advanced) — passed to the
container as `TZ` and `UMASK`.

**Restart service** — on the Status page, restarts the pod and reports
whether it came back up.

## Backup

The `qbittorrent-config` volume is included: settings, credentials and the
torrent session state. **Downloaded data is not** — it can reach hundreds
of gigabytes, and the NS8 backup engine only reaches named volumes and the
module state directory. Back that up separately if it matters.

## First login

qBittorrent prints a temporary admin password to its log on the very first
start. Find it in the NS8 **System logs** page, or with:

    journalctl --user -u qbittorrent-app -t ns8-qbittorrent1 | grep -i password

Set a permanent one under **Options → Web UI**, otherwise a new temporary
password is generated on every restart.

## Support

Bug reports and feature requests: [issue tracker](https://github.com/Shran21/ns8-qbittorrent/issues).
Anything else: [shranit.dev@gmail.com](mailto:shranit.dev@gmail.com)
