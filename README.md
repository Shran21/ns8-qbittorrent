# ns8-qbittorrent

A [qBittorrent](https://www.qbittorrent.org/) module for [NethServer 8](https://github.com/NethServer/ns8-core).

It runs the [linuxserver/qbittorrent](https://docs.linuxserver.io/images/docker-qbittorrent/)
container as a rootless Podman pod, publishes the WebUI through Traefik on a
virtual host of your choice, and can open the BitTorrent listen port in the
node firewall.

## Install

Instantiate the module with:

    add-module ghcr.io/shran21/ns8-qbittorrent:latest 1

The output of the command will return the instance name.
Output example:

    {"module_id": "ns8-qbittorrent1", "image_name": "ns8-qbittorrent", "image_url": "ghcr.io/shran21/ns8-qbittorrent:latest"}

## Configure

Let's assume the instance is named `ns8-qbittorrent1`.

Launch `configure-module`, setting the following parameters:

| Parameter | Required | Default | Description |
|---|---|---|---|
| `host` | yes | – | Fully qualified domain name of the WebUI |
| `http2https` | yes | – | Redirect HTTP requests to HTTPS |
| `lets_encrypt` | yes | – | Request a Let's Encrypt certificate |
| `downloads_dir` | no | `""` | Absolute host path for downloads. Empty means the `qbittorrent-downloads` volume |
| `bt_port` | no | `6881` | TCP/UDP port for incoming peer connections |
| `bt_port_enabled` | no | `true` | Open `bt_port` in the public firewall zone |
| `umask` | no | `002` | Umask applied to downloaded files |
| `timezone` | no | `UTC` | IANA time zone used inside the container |

Example:

```
api-cli run configure-module --agent module/ns8-qbittorrent1 --data - <<EOF
{
  "host": "qbittorrent.domain.com",
  "http2https": true,
  "lets_encrypt": false,
  "bt_port": 6881,
  "bt_port_enabled": true,
  "timezone": "Europe/Budapest"
}
EOF
```

The above command will:

- store the settings in the module environment
- open (or close) the BitTorrent port in the node firewall
- configure a Traefik virtual host for the WebUI
- start the `ns8-qbittorrent` pod

## Storage layout

| Container path | Backed by | Included in backup |
|---|---|---|
| `/config` | `qbittorrent-config` named volume | **yes** |
| `/downloads` | `qbittorrent-downloads` named volume, or a host path | **no** |

The configuration volume holds the application settings, the WebUI
credentials and the torrent session state (`.torrent` files, resume data,
categories), so restoring a backup brings the queue back.

Downloaded data is deliberately excluded: it can reach hundreds of gigabytes,
it is re-downloadable by design, and the NS8 backup engine only reaches named
volumes and the module state directory. Back up that data separately if it
matters to you.

### Downloads on an additional disk

The `qbittorrent-downloads` volume carries the `org.nethserver.volumes` label,
so when the installation node has an additional disk the cluster UI offers to
store it there during installation. See
[volumes](https://nethserver.github.io/ns8-core/modules/volumes/).

### Downloads on a host directory

Set `downloads_dir` to an absolute path to bind-mount an existing directory
instead. The directory must already exist and be writable by the module user:
the container runs as `PUID=0`, which rootless Podman maps to that user on the
host.

```bash
# the module user is the instance name, e.g. ns8-qbittorrent1
mkdir -p /data/qbittorrent/downloads
chown -R ns8-qbittorrent1:ns8-qbittorrent1 /data/qbittorrent/downloads
```

`configure-module` refuses a path that does not exist or is not writable,
instead of starting a container that cannot save anything.

## BitTorrent port

Incoming peer connections cannot be proxied by Traefik: they need a port
reachable from the outside. With `bt_port_enabled` the module opens
`bt_port` (TCP and UDP) in the *public* firewall zone of the node. You still
have to forward the same port on the upstream router or gateway.

Turn it off if the port is published some other way, or if you accept
outgoing-only connectivity (torrents still work, but with fewer peers). When
it is off the pod does not bind the host port at all, so a second instance
(a clone, or a restore next to the original) can start on the same node.

Instances updated from an earlier version start with the port **closed**: an
update never widens the firewall on its own.

## Reverse proxy support

On first start, `bin/bootstrap-qbittorrent-config` seeds `qBittorrent.conf`
so the WebUI works behind Traefik:

- `WebUI\ReverseProxySupportEnabled=true` and
  `WebUI\TrustedReverseProxiesList=127.0.0.1` — the supported way to run
  qBittorrent behind a proxy
- `WebUI\ServerDomains=*` — accept the `Host` header forwarded by Traefik
- `WebUI\LocalHostAuth=true` and `WebUI\CSRFProtection=true` — authentication
  and CSRF protection stay on. Traefik connects from `127.0.0.1`, so bypassing
  authentication for localhost would leave the WebUI open to anyone who can
  reach the virtual host.

Afterwards the file belongs to you and is left alone, with one exception: the
BitTorrent listen port is kept in sync on every start, because it is the
platform that publishes it and opens the firewall.

## qBittorrent admin password

On the very first launch qBittorrent generates a temporary admin password and
prints it to the container log. Find it in the NS8 **System logs** page, or
with:

    journalctl --user -u qbittorrent-app -t ns8-qbittorrent1 | grep -i password

Log in, then set a permanent password under **Options → Web UI**. Until you do,
a new temporary password is generated on every restart.

## Restart the service

From the UI, use the **Restart service** button on the Status page. From the
command line:

    api-cli run module/ns8-qbittorrent1/restart-services --data '{}'

## Get the configuration

    api-cli run get-configuration --agent module/ns8-qbittorrent1

## Update

Update an installed instance to a newer image:

    update-module ghcr.io/shran21/ns8-qbittorrent:1.0.0 ns8-qbittorrent1

or through the API:

    api-cli run update-module --data '{"module_url":"ghcr.io/shran21/ns8-qbittorrent:1.0.0","instances":["ns8-qbittorrent1"],"force":true}'

Instances created before the volume rework are migrated automatically by
`update-module.d/10migrate_volumes`: the configuration is copied from the old
bind-mounted directory into the `qbittorrent-config` volume, the obsolete
`database.env` and `volume-qbittorrent.env` files are removed, and the new
settings get their defaults. The old configuration directory is left on disk —
removing it is your call.

## Uninstall

To uninstall the instance:

    remove-module --no-preserve ns8-qbittorrent1

This also removes the Traefik route and closes the firewall port.

## Debug

The module runs under an agent that sets a number of environment variables.
Inspect them from a root terminal:

    runagent -m ns8-qbittorrent1 env

Become the module user to run scripts with the same environment:

    runagent -m ns8-qbittorrent1

Then inspect the containers:

```
podman ps
CONTAINER ID  IMAGE                                                        COMMAND     CREATED        STATUS        PORTS                     NAMES
d292c6ff28e9  localhost/podman-pause:4.6.1-1702418000                                  9 minutes ago  Up 9 minutes  127.0.0.1:20015->8080/tcp  a1b2c3d4e5f6-infra
9e58e5bd676f  docker.io/linuxserver/qbittorrent:5.2.3_v2.0.14-ls476        /init       9 minutes ago  Up 9 minutes  127.0.0.1:20015->8080/tcp  qbittorrent-app
```

Check the environment inside the container:

    podman exec qbittorrent-app env

Open a shell inside the container:

    podman exec -ti qbittorrent-app bash

Find the configuration volume on disk:

    podman volume inspect --format '{{.Mountpoint}}' qbittorrent-config

## Testing

Test the module using the `test-module.sh` script:

    ./test-module.sh <NODE_ADDR> ghcr.io/shran21/ns8-qbittorrent:latest

The tests are written with [Robot Framework](https://robotframework.org/).

## UI translation

Translated with [Weblate](https://hosted.weblate.org/projects/ns8/).

To set up the translation process:

- add the [GitHub Weblate app](https://docs.weblate.org/en/latest/admin/continuous.html#github-setup) to the repository
- add the repository to [hosted.weblate.org](https://hosted.weblate.org) or ask a NethServer developer to add it to the ns8 Weblate project
