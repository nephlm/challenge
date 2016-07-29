#! /bin/sh

apt-get install python-pip -y
yes | pip install flask requests

echo "yes" > /tmp/installScript.txt
