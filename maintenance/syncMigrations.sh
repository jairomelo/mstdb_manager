#!/bin/bash

declare -a apps=("esclavizados" "prosopographic")
remotepath="/home/django/toolbox/"
remote_host="root@138.197.58.4"

for app in "${apps[@]}"
do
    rsync -avh --progress --delete --exclude="__*" $remote_host:$remotepath/$app/migrations/ $app/migrations

done
