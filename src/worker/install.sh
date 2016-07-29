#! /bin/sh
echo "yes" > /tmp/installScriptStart.txt

apt-get install python-pip -y
yes | pip install flask requests

echo "yes" > /tmp/installScriptFin.txt
