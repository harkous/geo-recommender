#!/usr/bin/env bash

#server='icsil1-ds-26.epfl.ch'
server='lsirpc32.epfl.ch'
dir='/home/harkous/Development'
rsync -ave ssh /Users/harkous/Development/DMRec_public harkous@${server}:${dir}/ --exclude data_generation/generated_data --exclude .git --exclude .idea --exclude bower_components --exclude node_modules --exclude .sass-cache --exclude .tmp --exclude venv --exclude build --exclude __pycache__