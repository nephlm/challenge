#! /bin/sh

apt-get update
apt-get install git  -y

#pyenv
apt-get install curl git-core gcc make zlib1g-dev libbz2-dev libreadline-dev libsqlite3-dev libssl-dev -y

apt-get install postgresql postgresql-server-dev-9.3 postgresql -y

git clone https://github.com/nephlm/verodin /opt/verodin
chmod -R 755 /opt/verodin
chown -R ubuntu:ubuntu /opt/verodin

sudo -u ubuntu bash -c '
export HOME="/home/ubuntu"
cd ${HOME}
export PYENV_ROOT="/home/ubuntu/.pyenv"
curl -L https://raw.github.com/yyuu/pyenv-installer/master/bin/pyenv-installer | bash
export PATH="${PYENV_ROOT}/bin:${PATH}"
eval "$(pyenv init -)"
eval "$(pyenv virtualenv-init -)"
pyenv install 2.7.12
pyenv virtualenv 2.7.12 verodin '

# need to get the keys to /opt/verodin/src/keys
# or delete them and have them recreate.

yes | pip install -r /opt/verodin/requirements.txt


python /tmp/verodin/src/worker/worker.py &
