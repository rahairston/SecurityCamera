#!/bin/sh
USER_ID=$USER

sed "s/%i/$USER/" security-camera.template > security-camera.service

mkdir -p ~/.config/systemd/user/
mv security-camera.service ~/.config/systemd/

systemctl --user daemon-reload
systemctl --user --now enable security-camera.service