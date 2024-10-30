#!/bin/bash

set -a
source /home/mexico_slave_trade_db/.env
set +a

echo $DATABASE_NAME

# Set the date format, the database name, and the directory where you want to store your backups
DATE=$(date +%Y%m%d)
DB_NAME=$DATABASE_NAME
BACKUP_DIR="/home/backups/apps/msdb/"

# use a secure options file
MYSQL_CNF="~/.my.cnf"

# Create a backup
if ! mysqldump --defaults-file=$MYSQL_CNF $DB_NAME | gzip > "$BACKUP_DIR/$DB_NAME-$DATE.sql.gz"; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') - Backup failed for $DB_NAME" >> /home/mexico_slave_trade_db/appslogs/backup.log
    exit 1
else
    echo "$(date '+%Y-%m-%d %H:%M:%S') - Backup successful for $DB_NAME" >> /home/mexico_slave_trade_db/appslogs/backup.log
fi

# Delete backups older than 30 days
find $BACKUP_DIR -name "$DB_NAME-*.sql" -type f -mtime +30 -exec rm {} \;
