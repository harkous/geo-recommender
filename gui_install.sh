#!/usr/bin/env bash
# install the node requirements
echo 'Downloading and installing nodejs, in case you did not have it'

# see more about n: https://github.com/mklement0/n-install
curl -L https://git.io/n-install | bash -s -- -y

. ~/.bashrc


GUIDIR="$PWD/gui"
cd $GUIDIR

echo "Installing project dependencies:"
#npm install -g bower
#npm install -g gulp-cli
npm install
./node_modules/.bin/bower install

#Install gem 'sass'
#gem install sass

#echo "Serving the current code on port 3000"
#./node_modules/.bin/gulp serve:dist