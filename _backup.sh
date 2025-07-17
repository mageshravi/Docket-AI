#!/bin/bash

SITE_NAME=mysite.com
APP_DIR=/opt/$SITE_NAME
BACKUP_DIR=/opt/$SITE_NAME/data/dumps/$(date +'%Y')/$(date +'%m')/$(date +'%d')

printf "\nCreating new backup folder... \n"

mkdir -p $BACKUP_DIR

printf "\nCopying database...\n"
cp db.sqlite3 $BACKUP_DIR

printf "\nCopying media files...\n"
tar -czvf $BACKUP_DIR/media_$(date +'%Y_%m_%d').tar.gz /var/www/media-$SITE_NAME

printf "\nDone.\n"

# Send notification to Telegram
BOT_TOKEN="<botToken>"
CHAT_ID="<chatId>"
curl "https://api.telegram.org/bot$BOT_TOKEN/sendMessage?chat_id=$CHAT_ID&message_thread_id=0&text=Backup+successful."
