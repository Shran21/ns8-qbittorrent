# ns8-qbittorrent

This is a module for [NethServer 8](https://github.com/NethServer/ns8-core).

## Install

Instantiate the module with:

    add-module ghcr.io/shran21/ns8-qbittorrent:latest 1

The output of the command will return the instance name.
Output example:

    {"module_id": "ns8-qbittorrent1", "image_name": "ns8-qbittorrent", "image_url": "ghcr.io/shran21/ns8-qbittorrent:latest"}

## Configure

Let's assume that the mattermost instance is named `ns8-qbittorrent1`.

Launch `configure-module`, by setting the following parameters:
- `host`: a fully qualified domain name for the application
- `http2https`: enable or disable HTTP to HTTPS redirection (true/false)
- `lets_encrypt`: enable or disable Let's Encrypt certificate (true/false)
- `Downloads Directory`: the absolute path to the download directory used by the application.


Example:

```
api-cli run configure-module --agent module/ns8-qbittorrent1 --data - <<EOF
{
  "host": "ns8-qbittorrent.domain.com",
  "http2https": true,
  "lets_encrypt": false
  "downloads_dir": "/data/qbittorrent/downloads"
}
EOF
```

The above command will:
- start and configure the ns8-qbittorrent instance
- configure a virtual host for trafik to access the instance

### Setting Up the Downloads Directory

The `downloads_dir` specifies the directory where the application stores downloaded files. By default, the directory must exist, and the rootless container's user must have the necessary permissions to access it.

---

### Steps to Set Up the Downloads Directory

1. **Create the Default Directory:**
   If the directory does not already exist, create it using the `mkdir` command. For example:
   ```bash
   mkdir -p /data/qbittorrent/downloads
   ```

2. **Set the Correct Permissions:**
   Assign ownership of the directory to the rootless container user. Replace `<username>` with the user running the container (e.g., `ns8-qbittorrent`):
   ```bash
   chown -R <username>:<username> /data/qbittorrent/downloads
   ```

3. **Verify Permissions:**
   Ensure that the directory has the correct permissions:
   ```bash
   ls -ld /data/qbittorrent/downloads
   ```

   Example output:
   ```
   drwxr-xr-x 2 ns8-qbittorrent ns8-qbittorrent 4096 Jan 23 20:00 /data/qbittorrent/downloads
   ```

4. **Specify the Directory in the Configuration:**
   Pass the `downloads_dir` path when configuring the module:
   ```bash
   api-cli run configure-module --agent module/ns8-qbittorrent1 --data - <<EOF
   {
     "host": "ns8-qbittorrent.domain.com",
     "http2https": true,
     "lets_encrypt": false,
     "downloads_dir": "/data/qbittorrent/downloads"
   }
   EOF
   ```

---

### Example: Granting Permissions to Rootless Container User

If the rootless container user is `ns8-qbittorrent14`, you can grant the necessary permissions as follows:

```bash
mkdir -p /data/qbittorrent/downloads
chown -R ns8-qbittorrent14:ns8-qbittorrent14 /data/qbittorrent/downloads
```

Verify the permissions:
```bash
ls -ld /data/qbittorrent/downloads
```

Example output:
```
drwxr-xr-x 2 ns8-qbittorrent14 ns8-qbittorrent14 4096 Jan 23 20:00 /data/qbittorrent/downloads
```

---

## Get the configuration
You can retrieve the configuration with

```
api-cli run get-configuration --agent module/ns8-qbittorrent1
```

## Uninstall

To uninstall the instance:

    remove-module --no-preserve ns8-qbittorrent1

## Smarthost setting discovery

Some configuration settings, like the smarthost setup, are not part of the
`configure-module` action input: they are discovered by looking at some
Redis keys.  To ensure the module is always up-to-date with the
centralized [smarthost
setup](https://nethserver.github.io/ns8-core/core/smarthost/) every time
ns8-qbittorrent starts, the command `bin/discover-smarthost` runs and refreshes
the `state/smarthost.env` file with fresh values from Redis.

Furthermore if smarthost setup is changed when ns8-qbittorrent is already
running, the event handler `events/smarthost-changed/10reload_services`
restarts the main module service.

See also the `systemd/user/ns8-qbittorrent.service` file.

This setting discovery is just an example to understand how the module is
expected to work: it can be rewritten or discarded completely.

## Debug

some CLI are needed to debug

- The module runs under an agent that initiate a lot of environment variables (in /home/ns8-qbittorrent1/.config/state), it could be nice to verify them
on the root terminal

    `runagent -m ns8-qbittorrent1 env`

- you can become runagent for testing scripts and initiate all environment variables
  
    `runagent -m ns8-qbittorrent1`

 the path become : 
```
    echo $PATH
    /home/ns8-qbittorrent1/.config/bin:/usr/local/agent/pyenv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/usr/
```

- if you want to debug a container or see environment inside
 `runagent -m ns8-qbittorrent1`
 ```
podman ps
CONTAINER ID  IMAGE                                      COMMAND               CREATED        STATUS        PORTS                    NAMES
d292c6ff28e9  localhost/podman-pause:4.6.1-1702418000                          9 minutes ago  Up 9 minutes  127.0.0.1:20015->80/tcp  80b8de25945f-infra
d8df02bf6f4a  docker.io/library/mariadb:10.11.5          --character-set-s...  9 minutes ago  Up 9 minutes  127.0.0.1:20015->80/tcp  mariadb-app
9e58e5bd676f  docker.io/library/nginx:stable-alpine3.17  nginx -g daemon o...  9 minutes ago  Up 9 minutes  127.0.0.1:20015->80/tcp  ns8-qbittorrent-app
```

you can see what environment variable is inside the container
```
podman exec  ns8-qbittorrent-app env
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
TERM=xterm
PKG_RELEASE=1
MARIADB_DB_HOST=127.0.0.1
MARIADB_DB_NAME=ns8-qbittorrent
MARIADB_IMAGE=docker.io/mariadb:10.11.5
MARIADB_DB_TYPE=mysql
container=podman
NGINX_VERSION=1.24.0
NJS_VERSION=0.7.12
MARIADB_DB_USER=ns8-qbittorrent
MARIADB_DB_PASSWORD=ns8-qbittorrent
MARIADB_DB_PORT=3306
HOME=/root
```

you can run a shell inside the container

```
podman exec -ti   ns8-qbittorrent-app sh
/ # 
```
## Testing

Test the module using the `test-module.sh` script:


    ./test-module.sh <NODE_ADDR> ghcr.io/nethserver/ns8-qbittorrent:latest

The tests are made using [Robot Framework](https://robotframework.org/)
