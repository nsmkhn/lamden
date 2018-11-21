#!/bin/bash
set -ex

# DEV only
if [ $CIRCLECI != 'true' ]
  then
    pip3 install seneca --upgrade
    pip3 install vmnet --upgrade
    sudo service mongodb stop
fi

echo "Waiting for mongo on localhost"
mkdir -p ./data/$HOST_NAME/db/logs
touch ./data/$HOST_NAME/db/logs/log_mongo.log
echo 'Dir created'

mongod --dbpath ./data/db --logpath ./data/db/logs/mongo.log --bind_ip_all &
sleep 1
echo 'started mongod'

python3 ./scripts/create_user.py
