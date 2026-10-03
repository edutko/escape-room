#!/usr/bin/env bash

SERVER_IP=192.168.80.1
PHONE_EXT=8567
PHONE_IP=$(/usr/sbin/asterisk -rx "pjsip show contacts" | grep $PHONE_EXT | cut -d ':' -f 3 | sed -E -e 's/^.*@//')
CREDENTIALS="admin:password"

if [[ -z "$PHONE_IP" ]]; then
  exit 1
fi

function lock_phone() {
  /usr/sbin/asterisk -rx "database put LOCKED $PHONE_EXT yes"
  curl -u "$CREDENTIALS" --data-urlencode 'XML=<CiscoIPPhoneExecute><ExecuteItem Priority="2" URL="http://'$SERVER_IP':8888/locked.xml"/></CiscoIPPhoneExecute>' "http://$PHONE_IP/CGI/Execute"
  sleep 5
}

function unlock_phone() {
  /usr/sbin/asterisk -rx "database del LOCKED $PHONE_EXT"
  curl -u "$CREDENTIALS" --data-urlencode 'XML=<CiscoIPPhoneExecute><ExecuteItem Priority="2" URL="Key:Soft3"/></CiscoIPPhoneExecute>' "http://$PHONE_IP/CGI/Execute"
  sleep 5
}


# main
php_file=$(mktemp)
cat > "$php_file" <<"EOF"
<?php
$path = parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH);

if ($path === '/auth') {
    header('Content-Type: text/plain');
    echo 'AUTHORIZED';
    exit;
}

if ($path === '/locked.xml') {
    header('Content-Type: text/xml');
    echo '<CiscoIPPhoneText>
<Title>OUT OF SERVICE</Title>
<Text>Please repair the switchboard</Text>
</CiscoIPPhoneText>';
    exit;
}

http_response_code(404);
echo 'Not Found';
EOF

php -S ${SERVER_IP}:8888 "$php_file" &
php_pid=$!
sleep 1

if [[ "$1" = "unlock" ]]; then
  unlock_phone
else
    lock_phone
fi

kill $php_pid
rm -f "$php_file" 2>/dev/null
