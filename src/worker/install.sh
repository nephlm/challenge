#! /bin/sh
echo "yes" > /tmp/installScriptStart.txt

#pyenv/virtualenv
apt-get install curl git-core gcc make zlib1g-dev libbz2-dev libreadline-dev libsqlite3-dev libssl-dev -y

sudo -u ubuntu bash -c '
export HOME="/home/ubuntu"
cd ${HOME}
export PYENV_ROOT="/home/ubuntu/.pyenv"
curl -L https://raw.github.com/yyuu/pyenv-installer/master/bin/pyenv-installer | bash
export PATH="${PYENV_ROOT}/bin:${PATH}"
eval "$(pyenv init -)"
eval "$(pyenv virtualenv-init -)"
pyenv install 2.7.12
pyenv virtualenv 2.7.12 verodin
. $PYENV_ROOT/versions/verodin/bin/activate
yes | pip install -r /tmp/verodin/requirements.txt
yes | pip install gunicorn
python /tmp/verodin/src/worker/worker.py &

'



