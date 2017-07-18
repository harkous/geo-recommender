#!/usr/bin/env bash
#create and load the virtual environment
echo "Creating virtual environment"
python3 -m venv venv
source venv/bin/activate


#install requirements
echo "Installing python dependencies, which might take time..."
pip install -r requirements.txt

# install the packages
echo "Setting up the package"
python setup.py install
