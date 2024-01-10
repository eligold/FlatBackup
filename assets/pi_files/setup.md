become root
apt update && apt upgrade -y
apt install screen vim python3-pip python3-opencv fim git
ssh-keygen -t ed25119
raspi-config
-locale
-keyboard

as lando:
mkdir workspace
cd workspace
git clone

as root:
python -m venv --system-site-packages env
source env/bin/activate
pip install obd
