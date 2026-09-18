#!/bin/bash

#
# Copyright (C) 2023 Nethesis S.r.l.
# SPDX-License-Identifier: GPL-3.0-or-later
#

# Terminate on error
set -e

# Prepare variables for later use
images=()
# The image will be pushed to GitHub container registry
repobase="${REPOBASE:-ghcr.io/shran21}"
# Configure the image name
reponame="ns8-qbittorrent"

# The qBittorrent image is pinned to an exact upstream build: ":latest"
# makes the module unreproducible and lets an upstream change break a
# running installation without any action from the administrator.
# Renovate keeps this line up to date.
qbittorrent_image="docker.io/linuxserver/qbittorrent:5.2.3_v2.0.14-ls476"

# Create a new empty container image
container=$(buildah from scratch)

# Reuse existing nodebuilder-ns8-qbittorrent container, to speed up builds
if ! buildah containers --format "{{.ContainerName}}" | grep -q nodebuilder-ns8-qbittorrent; then
    echo "Pulling NodeJS runtime..."
    buildah from --name nodebuilder-ns8-qbittorrent -v "${PWD}:/usr/src:Z" docker.io/library/node:24.21.0-slim
fi

echo "Build static UI files with node..."
buildah run \
    --workingdir=/usr/src/ui \
    --env="NODE_OPTIONS=--openssl-legacy-provider" \
    nodebuilder-ns8-qbittorrent \
    sh -c "corepack enable && yarn install --immutable && yarn build"

# Add imageroot directory to the container image
buildah add "${container}" imageroot /imageroot
buildah add "${container}" ui/dist /ui
# Setup the entrypoint, ask to reserve one TCP port with the label and set a rootless container
#
# Labels:
# - authorizations: routeadm publishes the WebUI through Traefik, fwadm
#   opens the BitTorrent listen port in the public firewall zone.
# - tcp-ports-demand=1: the WebUI backend port, bound to the loopback
#   address. The BitTorrent port is chosen by the administrator (it has to
#   be forwarded on the upstream router), so it is not allocated here.
# - volumes: qbittorrent-downloads is offered for assignment to an
#   additional disk, because downloaded data is the part that grows.
buildah config --entrypoint=/ \
    --label="org.nethserver.authorizations=traefik@node:routeadm node:fwadm" \
    --label="org.nethserver.tcp-ports-demand=1" \
    --label="org.nethserver.rootfull=0" \
    --label="org.nethserver.volumes=qbittorrent-downloads" \
    --label="org.nethserver.images=${qbittorrent_image}" \
    "${container}"
# Commit the image
buildah commit "${container}" "${repobase}/${reponame}"

# Append the image URL to the images array
images+=("${repobase}/${reponame}")

#
# NOTICE:
#
# It is possible to build and publish multiple images.
#
# 1. create another buildah container
# 2. add things to it and commit it
# 3. append the image url to the images array
#

#
# Setup CI when pushing to Github.
# Warning! docker::// protocol expects lowercase letters (,,)
if [[ -n "${CI}" ]]; then
    # Set output value for Github Actions
    printf "images=%s\n" "${images[*],,}" >> "${GITHUB_OUTPUT}"
else
    # Just print info for manual push
    printf "Publish the images with:\n\n"
    for image in "${images[@],,}"; do printf "  buildah push %s docker://%s:%s\n" "${image}" "${image}" "${IMAGETAG:-latest}" ; done
    printf "\n"
fi
