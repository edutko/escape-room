#!/usr/bin/env bash

MAC=00254592EF0C
EXTENSION=5432
DISPLAY_NAME=Classroom
SECRET=18e340f34c8bc5cf
ORGANIZATION=Lab
SERVER_IP=192.168.80.1

sed -e "s/##EXTENSION##/$EXTENSION/g" \
	-e "s/##DISPLAY_NAME##/$DISPLAY_NAME/g" \
	-e "s/##SECRET##/$SECRET/g" \
	-e "s/##ORGANIZATION##/$ORGANIZATION/g" \
	-e "s/##SERVER_IP##/$SERVER_IP/g" \
	SEP-MAC-.cnf.xml | sudo tee /var/ftpd/SEP${MAC}.cnf.xml
