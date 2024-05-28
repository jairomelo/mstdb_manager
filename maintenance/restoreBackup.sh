#!/bin/bash

set -a
source "${PWD}/.env"
set +a

echo $DATABASE_NAME

DB_NAME=$DATABASE_NAME
BACKUP_DIR="/home/backups/apps/msdb/"
TEMP_DIR="temp"

MYSQL_CNF="~/.my.cnf"

LAST_BACKUP=$(find $BACKUP_DIR -type f -exec ls -t1 {} + | head -1)

mkdir -p $TEMP_DIR

BACKUP=$(basename "$LAST_BACKUP" .gz)

gunzip -c "$LAST_BACKUP" > "$TEMP_DIR/$BACKUP"

mysql --defaults-extra-file=$MYSQL_CNF $DB_NAME < "$TEMP_DIR/$BACKUP"
