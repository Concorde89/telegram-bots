import locale
import sys
import os


BASE_PATH = os.environ.get('BASE_PATH')
sys.path.insert(1, BASE_PATH + '/telegram-bots/src')

from twython import Twython
from graphqlclient import GraphQLClient
import time
from datetime import datetime
import pprint
import os.path
import re

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackContext, CallbackQueryHandler, MessageHandler, Filters
import telegram.error
import libraries.graphs_util as graphs_util
import libraries.general_end_functions as general_end_functions
import libraries.commands_util as commands_util
import libraries.scrap_websites_util as scrap_websites_util
import libraries.git_util as git_util
import libraries.requests_util as requests_util
import libraries.util as util
from bots.boo_bank.bot_boo_values import links, test_error_token, how_to_swap
from libraries.timer_util import RepeatedTimer

button_list_price = [[InlineKeyboardButton('refresh', callback_data='refresh_price')]]
reply_markup_price = InlineKeyboardMarkup(button_list_price)

APP_KEY = os.environ.get('TWITTER_API_KEY')
APP_SECRET = os.environ.get('TWITTER_API_KEY_SECRET')
ACCESS_TOKEN = os.environ.get('TWITTER_ACCESS_TOKEN')
ACCESS_SECRET_TOKEN = os.environ.get('TWITTER_ACCESS_TOKEN_SECRET')

twitter = Twython(APP_KEY, APP_SECRET, ACCESS_TOKEN, ACCESS_SECRET_TOKEN)

# time
last_time_checked_4chan = 0
last_time_checked_twitter = 0

# log_file
charts_path = BASE_PATH + 'log_files/chart_bot/'

locale.setlocale(locale.LC_ALL, 'en_US')

graphql_client_uni = GraphQLClient('https://api.thegraph.com/subgraphs/name/uniswap/uniswap-v2')
graphql_client_eth = GraphQLClient('https://api.thegraph.com/subgraphs/name/blocklytics/ethereum-blocks')

re_4chan = re.compile(r'\$BOOB|BOOB')
TELEGRAM_KEY = os.environ.get('BOO_TELEGRAM_KEY')
MEME_GIT_REPO = os.environ.get('BOO_MEME_GIT_REPO')
MEME_PWD = os.environ.get('BOO_MEME_GIT_REPO_DELETE_PWD')
TMP_FOLDER = BASE_PATH + 'tmp/'
boob_contract = "0xa9c44135b3a87e0688c41cf8c27939a22dd437c9"
name = "Boo Bank"
ticker = 'BOOB'
ecto_contract = "0x921c87490ccbef90a3b0fc1951bd9064f7220af6"
ecto_name = "Ectoplasma"
ecto_ticker = 'ECTO'
pair_contract = "0x6e31ef0b62a8abe30d80d35476ca78897dffa769"
decimals = 1000000000000000000  # that's 18
git_url = "https://api.github.com/repos/boobank/boo-memes/contents/memesFolder"

# add meme
git_handler = git_util.MemeHandler(MEME_GIT_REPO, git_url)

supply_file_path = BASE_PATH + 'log_files/boo_bot/supply_log.txt'
supply_chart_path = BASE_PATH + 'log_files/boo_bot/supply_chart.png'

lambo_price_usd = 220000


# button refresh: h:int-d:int-t:token
def get_candlestick(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id

    query_received = update.message.text.split(' ')

    time_type, k_hours, k_days, tokens = commands_util.check_query(query_received, ticker)
    t_to = int(time.time())
    t_from = t_to - (k_days * 3600 * 24) - (k_hours * 3600)

    if isinstance(tokens, list):
        for token in tokens:
            (message, path, reply_markup_chart) = general_end_functions.send_candlestick_pyplot(token, charts_path, k_days, k_hours, t_from, t_to)
            context.bot.send_photo(chat_id=chat_id, photo=open(path, 'rb'), caption=message, parse_mode="html", reply_markup=reply_markup_chart)
    else:
        (message, path, reply_markup_chart) = general_end_functions.send_candlestick_pyplot(tokens, charts_path, k_days, k_hours, t_from, t_to)
        context.bot.send_photo(chat_id=chat_id, photo=open(path, 'rb'), caption=message, parse_mode="html", reply_markup=reply_markup_chart)


def get_price_token(update: Update, context: CallbackContext):
    message = general_end_functions.get_price(boob_contract, pair_contract, graphql_client_eth, graphql_client_uni, name, decimals)
    chat_id = update.message.chat_id
    context.bot.send_message(chat_id=chat_id, text=message, parse_mode='html', reply_markup=reply_markup_price, disable_web_page_preview=True)


def get_price_ecto(update: Update, context: CallbackContext):
    message = general_end_functions.get_price(ecto_contract, pair_contract, graphql_client_eth, graphql_client_uni, ecto_name, decimals)
    chat_id = update.message.chat_id
    context.bot.send_message(chat_id=chat_id, text=message, parse_mode='html', reply_markup=reply_markup_price, disable_web_page_preview=True)


def refresh_chart(update: Update, context: CallbackContext):

    print("refreshing chart")
    query = update.callback_query.data

    k_hours = int(re.search(r'\d+', query.split('h:')[1]).group())
    k_days = int(re.search(r'\d+', query.split('d:')[1]).group())
    token = query.split('t:')[1]

    t_to = int(time.time())
    t_from = t_to - (k_days * 3600 * 24) - (k_hours * 3600)

    chat_id = update.callback_query.message.chat_id
    message_id = update.callback_query.message.message_id

    (message, path, reply_markup_chart) = general_end_functions.send_candlestick_pyplot(token, charts_path, k_days, k_hours, t_from, t_to)
    try:
        context.bot.delete_message(chat_id=chat_id, message_id=message_id)
        context.bot.send_photo(chat_id=chat_id, photo=open(path, 'rb'), caption=message, parse_mode="html", reply_markup=reply_markup_chart)
    except telegram.error.BadRequest:
        print("couldn't find message to deleted but catched the error")
        pass


def refresh_price(update: Update, context: CallbackContext):
    print("refreshing price")
    message = general_end_functions.get_price(boob_contract, pair_contract, graphql_client_eth, graphql_client_uni,
                                              name, decimals)
    update.callback_query.edit_message_text(text=message, parse_mode='html', reply_markup=reply_markup_price, disable_web_page_preview=True)


def get_help(update: Update, context: CallbackContext):
    general_end_functions.get_help(update, context)


def get_twitter(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    res = scrap_websites_util.get_last_tweets(twitter, ticker)
    context.bot.send_message(chat_id=chat_id, text=res, parse_mode='html', disable_web_page_preview=True)


def delete_chart_message(update: Update, context: CallbackContext):
    print("deleting chart")
    chat_id = update.callback_query.message.chat_id
    message_id = update.callback_query.message.message_id
    context.bot.delete_message(chat_id=chat_id, message_id=message_id)


def handle_new_image(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    try:
        caption = update['message']['caption']
        if caption == "/add_meme" and chat_id == -1001187740219:
            if git_handler.add_meme(update, context):
                context.bot.send_message(chat_id=chat_id, text="Got it boss!")
            else:
                error_msg = "Adding image failed: no image provided or incorrect format."
                context.bot.send_message(chat_id=chat_id, text=error_msg)
        else:
            __send_message_if_ocr(update, context)
    except KeyError:
        __send_message_if_ocr(update, context)


def __send_message_if_ocr(update, context):
    message_id = update.message.message_id
    chat_id = update.message.chat_id
    try:
        text_in_ocr = general_end_functions.ocr_image(update, context, TMP_FOLDER)
        if ('transaction cannot succeed' and 'one of the tokens' in text_in_ocr) or (
                'transaction will not succeed' and 'price movement or' in text_in_ocr):
            context.bot.send_message(chat_id=chat_id, text=test_error_token, reply_to_message_id=message_id)
    except IndexError:
        pass


def send_meme_to_chat(update: Update, context: CallbackContext):
    url = git_handler.get_url_meme()
    chat_id = update.message.chat_id
    context.bot.send_photo(chat_id=chat_id, photo=url)


# sends the current biz threads
def get_biz(update: Update, context: CallbackContext):
    global last_time_checked_4chan
    chat_id = update.message.chat_id
    new_time = round(time.time())
    if new_time - last_time_checked_4chan > 60:
        last_time_checked_4chan = new_time
        threads_ids = scrap_websites_util.get_biz_threads(re_4chan)

        base_url = "boards.4channel.org/biz/thread/"
        message = """Plz go bump the /biz/ threads:
"""
        for thread_id in threads_ids:
            excerpt = thread_id[2] + " | " + thread_id[1]
            message += base_url + str(thread_id[0]) + " -- " + excerpt[0: 100] + "[...] \n"
        if not threads_ids:
            meme_url = git_handler.get_url_meme()
            meme_caption = "There hasn't been a BoobBank /biz/ thread for a while. Here's a meme, go make one https://boards.4channel.org/biz/."
            context.bot.send_photo(chat_id=chat_id, photo=meme_url, caption=meme_caption)
        else:
            context.bot.send_message(chat_id=chat_id, text=message, disable_web_page_preview=True)
    else:
        context.bot.send_message(chat_id=chat_id,
                                 text='Only checking 4chan/twitter/charts once per minute. Don\'t spam.')


# sends the main links
def get_links(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    context.bot.send_message(chat_id=chat_id, text=links, disable_web_page_preview=True, parse_mode='html')


def send_anthem(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    caption = "🎸🤘🎼 <i>I want my stacked boobiiiiieeesssss</i>🎼🤘🎸"
    context.bot.send_audio(chat_id=chat_id,
                           audio=open(BASE_PATH + 'audio/boo/boo_anthem.mp3', 'rb'),
                           caption=caption,
                           parse_mode='html')


def send_flyer(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    path = BASE_PATH + 'images/boo/flyer.jpg'
    context.bot.send_photo(chat_id=chat_id, photo=open(path, 'rb'))


def log_current_supply():
    number_boob = requests_util.get_supply_cap_raw(boob_contract, decimals)
    number_ecto = requests_util.get_supply_cap_raw(ecto_contract, decimals)
    with open(supply_file_path, "a") as supply_file:
        time_now = datetime.now()
        date_time_str = time_now.strftime("%m/%d/%Y,%H:%M:%S")
        message_to_write = date_time_str + " " + str(number_boob) + " " + str(number_ecto) + "\n"
        supply_file.write(message_to_write)


def get_chart_supply(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id

    query_received = update.message.text.split(' ')

    time_type, k_hours, k_days, tokens = commands_util.check_query(query_received, ticker)

    current_boob_nbr, current_ecto_nbr = general_end_functions.send_supply_two_pyplot(supply_file_path,
                                                                                      k_days,
                                                                                      k_hours,
                                                                                      "BOOB",
                                                                                      "ECTO",
                                                                                      supply_chart_path)

    current_boob_str = util.number_to_beautiful(current_boob_nbr)
    current_ecto_str = util.number_to_beautiful(current_ecto_nbr)

    msg_time = " " + str(k_days) + " day(s) " if k_days > 0 else " last " + str(k_hours) + " hour(s) "

    caption = "Supply of the last " + msg_time + ".\nCurrent supply: \n<b>BOOB:</b> <pre>" + current_boob_str + \
              "</pre> \n<b>ECTO:</b> <pre>" + current_ecto_str + "</pre>"

    context.bot.send_photo(chat_id=chat_id,
                           photo=open(supply_chart_path, 'rb'),
                           caption=caption,
                           parse_mode="html")


def send_how_to_swap(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    context.bot.send_message(chat_id=chat_id, text=how_to_swap, disable_web_page_preview=True, parse_mode='html')


def do_convert(update: Update, context: CallbackContext):
    query_received = update.message.text.split(' ')
    chat_id = update.message.chat_id
    if len(query_received) == 3:
        ticker_req = query_received[2]
        amount = float(query_received[1])
        res = general_end_functions.convert_to_usd(amount, ticker_req, graphql_client_uni, graphql_client_eth)
        message = str(amount) + " " + ticker_req + " = " + res + " USD"
        context.bot.send_message(chat_id=chat_id, text=message, disable_web_page_preview=True, parse_mode='html')
    elif len(query_received) == 4:
        ticker_req = query_received[2]
        amount = float(query_received[1])
        ticker_to = query_received[3]
        res_req = general_end_functions.convert_to_usd_raw(1, ticker_req, graphql_client_uni, graphql_client_eth)
        if ticker_to == 'lambo':
            res = amount * (res_req / float(lambo_price_usd))
            res_req_usd_str = util.number_to_beautiful(round(res_req * amount)) if round(res_req * amount) > 10 else util.float_to_str(res_req * amount)
            res_str = util.number_to_beautiful(round(res)) if round(res) > 10 else util.float_to_str(res)[0:10]
            message = str(amount) + " " + ticker_req + " = " + res_req_usd_str + " USD or roughly " + res_str + " lamborghini huracan"
        else:
            res_ticker_to = general_end_functions.convert_to_usd_raw(1, ticker_to, graphql_client_uni, graphql_client_eth)
            res = amount * (res_req / res_ticker_to)
            res_req_usd_str = util.number_to_beautiful(round(res_req * amount)) if round(res_req * amount) > 10 else util.float_to_str(res_req * amount)
            res_str = util.number_to_beautiful(round(res)) if round(res) > 10 else util.float_to_str(res)[0:10]
            message = str(amount) + " " + ticker_req + " = " + res_req_usd_str + " USD or " + res_str + " " + ticker_to
        context.bot.send_message(chat_id=chat_id, text=message, disable_web_page_preview=True, parse_mode='html')
    else:
        context.bot.send_message(chat_id=chat_id, text="Wrong format. Please use /convert AMOUNT CURRENCY", disable_web_page_preview=True, parse_mode='html')


def delete_meme(update: Update, context: CallbackContext):
    git_handler.delete_meme(update, context, MEME_PWD)


def main():
    updater = Updater(TELEGRAM_KEY, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler('chart', get_candlestick))
    dp.add_handler(CommandHandler('price', get_price_token))
    dp.add_handler(CommandHandler('boob', get_price_token))
    dp.add_handler(CommandHandler('ecto', get_price_ecto))
    dp.add_handler(CallbackQueryHandler(refresh_chart, pattern='refresh_chart(.*)'))
    dp.add_handler(CallbackQueryHandler(refresh_price, pattern='refresh_price'))
    dp.add_handler(CallbackQueryHandler(delete_chart_message, pattern='delete_message'))
    dp.add_handler(CommandHandler('help', get_help))
    dp.add_handler(CommandHandler('twitter', get_twitter))
    dp.add_handler(MessageHandler(Filters.photo, handle_new_image))
    dp.add_handler(CommandHandler('give_meme', send_meme_to_chat))
    dp.add_handler(CommandHandler('meme', send_meme_to_chat))
    dp.add_handler(CommandHandler('biz', get_biz))
    dp.add_handler(CommandHandler('links', get_links))
    dp.add_handler(CommandHandler('anthem', send_anthem))
    dp.add_handler(CommandHandler('flyer', send_flyer))
    dp.add_handler(CommandHandler('chart_supply', get_chart_supply))
    dp.add_handler(CommandHandler('how_to_swap', send_how_to_swap))
    dp.add_handler(CommandHandler('convert', do_convert))
    dp.add_handler(CommandHandler('delete_meme_secret', delete_meme))
    RepeatedTimer(120, log_current_supply)
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()

commands = """
help - How to use the bot.
chart - Display a chart of the price.
boob - Get the current price of $BOOB.
ecto - Get the current price of $ECTO.
chart_supply - Display a chart of the supply (BOOB and ECTO).
twitter - Get the last tweets concerning $BOOB.
add_meme - Add a meme to the meme folder.
give_meme - Returns a random meme from the meme folder.
anthem - Send the Boo Bank Org. national anthem.
flyer - Show the flyer.
biz - Display current 4chan threads.
how_to_swap - Guide on how to swap ecto
convert - convert AMOUNT MONEY
"""
