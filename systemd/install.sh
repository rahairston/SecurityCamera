#!/bin/sh
USER_ID=$USER

sed "s/%i/$USER/" security-camera.template > security-camera.service

sudo mv security-camera.service /etc/systemd/system/

sudo systemctl daemon-reload
sudo systemctl --now enable security-camera.service