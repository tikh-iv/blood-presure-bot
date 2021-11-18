#!/usr/bin/env python

"""
This bot can help you monitor your blood presure avery day
"""

import logging
from typing import Dict
import datetime
import pandas as pd
import os
from credentials import token

from telegram import ReplyKeyboardMarkup, Update, ReplyKeyboardRemove
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    ConversationHandler,
    CallbackContext,
)

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# Callback markers
CHOOSING, MESUREMENT, SPECIFIC_DATE, CHOOSING_TIME = range(4)

# Main menu
reply_keyboard = [
    ['Morning', 'Evening'],
    ['yesterday', 'Other day'],
    ['Download CSV']
]
markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)

# Choose time menu
reply_keyboard_time = [['Morning', 'Evening'],]
choose_time_markup = ReplyKeyboardMarkup(reply_keyboard_time, one_time_keyboard=True)

def start(update: Update, context: CallbackContext) -> int:
    """Start chating."""
    update.message.reply_text(
        "Hi! I'm bot. I can help you save you blood presure", # Show message 
        reply_markup=markup) # and start main menu
    return CHOOSING

def restart(update: Update, context: CallbackContext) -> int:
    """Restart chating when something wrong."""
    update.message.reply_text(
        "Hm, something went wrong. Try Again.", # Show message 
        reply_markup=markup) # and start main menu
    return CHOOSING

def today_date(update: Update, context: CallbackContext) -> int:
    """Define today date."""
    context.user_data['datetime'] = datetime.datetime.now() 
    evening_or_morning(update, context) # Call evening_or_morning wich define specific time
    return MESUREMENT

def yesterday_date(update: Update, context: CallbackContext) -> int:
    """Ask the user for specific time of mesurement anf define yesterday."""
    update.message.reply_text(
        'Time of mesurement',  # Show message 
        reply_markup=choose_time_markup) # and start time menu
    context.user_data['datetime'] = datetime.datetime.now() - datetime.timedelta(days=1) # define yesterday
    return CHOOSING_TIME  
    
def specific_date(update: Update, context: CallbackContext) -> int:
    """Ask the user for specific date of mesurement."""
    update.message.reply_text('Enter data in this format: dd.mm.yyyy')
    return SPECIFIC_DATE
    
def entering_date(update: Update, context: CallbackContext) -> int:
    """Define specific date."""
    text = update.message.text
    datetime_object = datetime.datetime.strptime(text, '%d.%m.%Y')
    context.user_data['datetime'] = datetime_object
    update.message.reply_text(
        'Time of mesurement', reply_markup=choose_time_markup)
    return CHOOSING_TIME
    
def evening_or_morning(update: Update, context: CallbackContext) -> int:
    """Define specific time and ask user for his presure."""
    text = update.message.text # There are "Morning" or "Evening"
    current_date = context.user_data['datetime'] # Define date frome context
    current_date = current_date.replace(minute=0,second=0,microsecond=0) # Replace minutes and seconds
    if text == 'Morning':
        current_date = current_date.replace(hour=8)
    else:
        current_date = current_date.replace(hour=20)
    context.user_data['datetime'] = current_date # Update datetime in context
    update.message.reply_text(f'Your {text.lower()} presure?') # Ask users presure
    return MESUREMENT

def mesurement_data(update: Update, context: CallbackContext) -> int:
    """Store info provided by user."""
    user_data = context.user_data
    text = update.message.text
    user_id = update.message.from_user['id'] # It'll ganerate CSV based on user's ID
    user_date_and_time = user_data['datetime'].strftime("%Y-%m-%d %H:%M:%S")
    del user_data['datetime'] # Delite datetime from context
    save_data_to_csv(user_date_and_time, text, user_id)
    update.message.reply_text(
        "Done",  # Show message 
        reply_markup=markup)# and start time menu
    return CHOOSING

def send_csv(update: Update, context: CallbackContext) -> int:
    """Send to user the csv based his id"""
    user_id = update.message.from_user['id'] # CSV name based on user's ID
    chat_id = update.message.chat_id # CSV was sended to this chat
    user_csv = str(user_id)+'.csv'
    if (os.path.exists(user_csv)): # if this fille is exist send the file
        with open(user_csv, "rb") as f:
            context.bot.send_document(chat_id=chat_id, document=f,  
                filename=user_csv)
    return CHOOSING

def save_data_to_csv(saving_date, saving_presure, user_id):
    """Save data to csv"""
    #file name based on user id
    user_csv = str(user_id)+'.csv'
    #if file doesn't exit make new one
    if not(os.path.exists(user_csv)):
        with open(user_csv, 'tw') as f:
            f.write(',')
    blood_csv = pd.read_csv(user_csv, header=None)    
    existed_rows =  blood_csv.index[blood_csv[0] == saving_date].tolist()
    #save data to csv
    if existed_rows != []:
        blood_csv[1][existed_rows[0]] = saving_presure
    else:
        df = pd.DataFrame([[saving_date,saving_presure]])
        blood_csv = blood_csv.append(df)
    blood_csv[0] = pd.to_datetime(blood_csv[0], format='%Y-%m-%d %H:%M:%S')
    #sort scv file
    blood_csv = blood_csv.sort_values(by=0)
    blood_csv.to_csv(user_csv, header = False, index = False)


def main() -> None:
    """Run the bot."""
    # Create the Updater and pass it your bot's token.
    updater = Updater(token)

    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher

    # Add conversation handler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            CHOOSING: [ # Main menu state
                MessageHandler(Filters.regex('^(Morning|Evening)$'), today_date),
                MessageHandler(Filters.regex('^(yesterday)$'), yesterday_date),
                MessageHandler(Filters.regex('^(Other day)$'), specific_date),
                MessageHandler(Filters.regex('^(Download CSV)$'), send_csv),
                MessageHandler(Filters.text & ~(Filters.command), restart)
                ],
            SPECIFIC_DATE : { # Entering specific day state
                MessageHandler(Filters.regex('^\d\d.\d\d.\d\d\d\d$'), evening_or_morning),
                MessageHandler(Filters.text & ~(Filters.command), restart,)
            },
            MESUREMENT: [ # Entering data state
                MessageHandler(Filters.text & ~(Filters.command), mesurement_data,)
            ],
            CHOOSING_TIME : { # Choosing time state
                MessageHandler(Filters.regex('^(Morning|Evening)$'), evening_or_morning),
                MessageHandler(Filters.text & ~(Filters.command), restart)
            },
        },
        fallbacks=[MessageHandler(Filters.regex('^\/?(((R|r)e)?(S|s)tart)$'), start)],
    )

    dispatcher.add_handler(conv_handler)

    # Start the Bot
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
