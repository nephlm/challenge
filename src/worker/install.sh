#! /bin/sh
echo "yes" > /tmp/installScriptStart.txt

apt-get install python-pip -y
yes | pip install flask requests gunicorn

echo "yes" > /tmp/installScriptFin.txt

python /tmp/verodin/src/worker/worker.py &
