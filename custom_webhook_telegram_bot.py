#!/usr/bin/env python
# -*- coding: utf-8 -*-

import toml
import os
import logging
import time
import string
import random
import datetime
import requests

import flask

import telebot
from telebot import logger as telebot_logger
import telebot.types as TelebotTypes
import telebot.custom_filters as TelebotCustomFilters
from telebot.apihelper import ApiTelegramException

import database
from TwitchHelper import TwitchInfo
from PatreonHelper import PatreonInfo

""" Filter to check data content """
class DataMatchFilter(TelebotCustomFilters.AdvancedCustomFilter):

    key = 'data'

    def check(self, message, text):
        """
        :meta private:
        """
        if isinstance(message, TelebotTypes.CallbackQuery):
            return message.data in text

        return False

class EnvVariableNotFound(Exception):
    def __init__(self, message):            
        super().__init__(message)

DEVELOPMENT = True if os.getenv("BOT_MODE", "development") == "development" else False
DEBUG = True

HOSTNAME = 'communikeintest.pythonanywhere.com'
if DEVELOPMENT: HOSTNAME = 'humorous-bison-flowing.ngrok-free.app'
URL_BASE = "https://%s" % (HOSTNAME)
PATH_HOME = "/"
PATH_TELEGRAM = "/telegram"
PATH_TWITCH_OAUTH = "/twitch-oauth-user"
PATH_TWITCH_OAUTH_CHANNEL = "/twitch-oauth-channel"
PATH_TWITCH_REFRESH_TOKEN = "/twitch-refresh-token"
PATH_TWITCH_USER_UNSUBSCRIBED = "/twitch-user-unsubscribed"
PATH_PATREON_OAUTH = "/patreon-oauth-user"
PATH_PATREON_REFRESH_TOKEN = "/patreon-refresh-token"
PATH_PATREON_USER_UNSUBSCRIBED = "/patreon-user-unsubscribed"
WEBHOOK_TELEGRAM = URL_BASE + PATH_TELEGRAM
WEBHOOK_TWITCH_OAUTH = URL_BASE + PATH_TWITCH_OAUTH
WEBHOOK_TWITCH_REFRESH_TOKEN = URL_BASE + PATH_TWITCH_REFRESH_TOKEN
WEBHOOK_TWITCH_USER_UNSUBSCRIBED = URL_BASE + PATH_TWITCH_USER_UNSUBSCRIBED
WEBHOOK_PATREON_OAUTH = URL_BASE + PATH_PATREON_OAUTH
WEBHOOK_PATREON_REFRESH_TOKEN = URL_BASE + PATH_PATREON_REFRESH_TOKEN
WEBHOOK_PATREON_USER_UNSUBSCRIBED = URL_BASE + PATH_PATREON_USER_UNSUBSCRIBED

logging.basicConfig(
    filename='/home/communikeintest/logs/pigliamoschebot.log', 
    encoding='utf-8', 
    filemode='a', 
    style="{", 
    datefmt="%Y-%m-%d %H:%M", 
    format="{asctime}# {levelname} - {name}.{funcName} - {message}",
    level = logging.DEBUG)
logger = logging.getLogger(__name__)

# TODO: Update bot logger to use system logger
def init_telegram():

    global BOT_MESSAGE_WELCOME, BOT_MESSAGE_PLATFORM_CHECK, BOT_PLATFORM_CHOICE, BOT_JOIN_TELEGRAM_GROUP
    global BOT_SUBSCRIPTION_NOT_ACTIVE, BOT_WELCOME_TO_GROUP, BOT_ALREADY_JOINED_GROUP, BOT_REMOVED_FROM_CHAT
    global BOT_USER_TRIED_CHEATING, BOT_REQUEST_UNKNOWN, BOT_REPLY_READY, BOT_REPLY_NOT_READY
    global BOT_COMMAND_DESCRIPTION_START, BOT_COMMAND_DESCRIPTION_ADD_ME, BOT_COMMAND_DESCRIPTION_ADD_ME_TWITCH
    
    # Import bot text from TOML file
    with open('bot-text.ini', 'r') as f:
        bot_text_dict = toml.load(f)

    BOT_MESSAGE_WELCOME = bot_text_dict['bot']['MESSAGE_WELCOME'.lower()]
    BOT_MESSAGE_PLATFORM_CHECK = bot_text_dict['bot']['MESSAGE_PLATFORM_CHECK'.lower()]
    BOT_PLATFORM_CHOICE = bot_text_dict['bot']['PLATFORM_CHOICE'.lower()]
    BOT_JOIN_TELEGRAM_GROUP = bot_text_dict['bot']['JOIN_TELEGRAM_GROUP'.lower()]
    BOT_SUBSCRIPTION_NOT_ACTIVE = bot_text_dict['bot']['SUBSCRIPTION_NOT_ACTIVE'.lower()]
    BOT_WELCOME_TO_GROUP = bot_text_dict['bot']['WELCOME_TO_GROUP'.lower()]
    BOT_ALREADY_JOINED_GROUP = bot_text_dict['bot']['ALREADY_JOINED_GROUP'.lower()]
    BOT_REMOVED_FROM_CHAT = bot_text_dict['bot']['REMOVED_FROM_CHAT'.lower()]
    BOT_USER_TRIED_CHEATING = bot_text_dict['bot']['USER_TRIED_CHEATING'.lower()]
    BOT_REQUEST_UNKNOWN = bot_text_dict['bot']['REQUEST_UNKNOWN'.lower()]
    BOT_REPLY_READY = bot_text_dict['bot']['REPLY_READY'.lower()]
    BOT_REPLY_NOT_READY = bot_text_dict['bot']['REPLY_NOT_READY'.lower()]
    BOT_COMMAND_DESCRIPTION_START = bot_text_dict['bot']['COMMAND_DESCRIPTION_START'.lower()]
    BOT_COMMAND_DESCRIPTION_ADD_ME = bot_text_dict['bot']['COMMAND_DESCRIPTION_ADD_ME'.lower()]
    BOT_COMMAND_DESCRIPTION_ADD_ME_TWITCH = bot_text_dict['bot']['COMMAND_DESCRIPTION_ADD_ME_TWITCH'.lower()]

    bot_token = os.getenv("BOT_TOKEN", None)
    
    global GROUP_CHAT_ID_DEV, GROUP_CHAT_ID_PROD
    GROUP_CHAT_ID_DEV = os.getenv("GROUP_CHAT_ID_DEV", None)
    GROUP_CHAT_ID_PROD = os.getenv("GROUP_CHAT_ID_PROD", None)

    if not bot_token: raise EnvVariableNotFound('ERROR - init_telegram() - "BOT_TOKEN" environment variable not found')
    if not GROUP_CHAT_ID_DEV: raise EnvVariableNotFound('ERROR - init_telegram() - "GROUP_CHAT_ID_DEV" environment variable not found')
    if not GROUP_CHAT_ID_PROD: raise EnvVariableNotFound('ERROR - init_telegram() - "GROUP_CHAT_ID_PROD" environment variable not found')
    GROUP_CHAT_ID_DEV = int(GROUP_CHAT_ID_DEV)
    GROUP_CHAT_ID_PROD = int(GROUP_CHAT_ID_PROD)
    group_chat_id = GROUP_CHAT_ID_DEV if DEVELOPMENT else GROUP_CHAT_ID_PROD
        
    telebot_logger.setLevel(logging.DEBUG)
    bot = telebot.TeleBot(bot_token, threaded=False) # type: ignore
    bot.add_custom_filter(DataMatchFilter())
    
    # If no webhook, or the wrong one, has been registered, remove the current webhook and register the correct one
    webhook_info = bot.get_webhook_info()
    if not webhook_info or webhook_info.url != WEBHOOK_TELEGRAM:
        # Remove webhook, it fails sometimes the set if there is a previous webhook
        bot.remove_webhook()
        time.sleep(1)
        # Set webhook
        bot.set_webhook(url=WEBHOOK_TELEGRAM)

    return bot, group_chat_id

def init_twitch():
    twitch_client_id = os.getenv("TWITCH_CLIENT_ID", None)
    if not twitch_client_id: raise EnvVariableNotFound('ERROR - init_twitch() - "TWITCH_CLIENT_ID" environment variable not found')
    twitch_client_secret = os.getenv("TWITCH_CLIENT_SECRET", None)
    if not twitch_client_secret: raise EnvVariableNotFound('ERROR - init_twitch() - "TWITCH_CLIENT_SECRET" environment variable not found')
    twitch_secret = os.getenv("TWITCH_SECRET", None)
    if not twitch_secret: raise EnvVariableNotFound('ERROR - init_twitch() - "TWITCH_SECRET" environment variable not found')
    twitch_channel_username = os.getenv("TWITCH_CHANNEL_USERNAME", None)
    if not twitch_channel_username: raise EnvVariableNotFound('ERROR - init_twitch() - "TWITCH_CHANNEL_USERNAME" environment variable not found')
    twitch_channel_id = os.getenv("TWITCH_CHANNEL_ID", None)
    if not twitch_channel_id: raise EnvVariableNotFound('ERROR - init_twitch() - "TWITCH_CHANNEL_ID" environment variable not found')

    twitch_info = TwitchInfo( \
        client_id=twitch_client_id, \
        client_secret=twitch_client_secret, \
        twitch_secret=twitch_secret, \
        channel_username=twitch_channel_username, \
        channel_id=int(twitch_channel_id) \
    )
    webhook_registration_result_code, webhook_registration_result_data = twitch_info.register_unsubscribe_webhook(WEBHOOK_TWITCH_USER_UNSUBSCRIBED)
    if webhook_registration_result_code == 202:
        logger.info('Subscribed to Twitch event \'user unsubscribed\'')
    elif webhook_registration_result_code == 409:
        logger.info('Already subscribed to Twitch event \'user unsubscribed\'')
    else:
        logger.error(f'Unknown error: {webhook_registration_result_data}')

    return twitch_info

def init_patreon():
    patreon_client_id = os.getenv("PATREON_CLIENT_ID", None)
    if not patreon_client_id: raise EnvVariableNotFound('ERROR - init_patreon() - "PATREON_CLIENT_ID" environment variable not found')
    patreon_client_secret = os.getenv("PATREON_CLIENT_SECRET", None)
    if not patreon_client_secret: raise EnvVariableNotFound('ERROR - init_patreon() - "PATREON_CLIENT_SECRET" environment variable not found')
    
    patreon_creator_id = os.getenv("PATREON_CREATOR_ID", None)
    if not patreon_creator_id: raise EnvVariableNotFound('ERROR - init_patreon() - "PATREON_CREATOR_ID" environment variable not found')
    patreon_creator_token = os.getenv("PATREON_CREATOR_TOKEN", None)
    if not patreon_creator_token: raise EnvVariableNotFound('ERROR - init_patreon() - "PATREON_CREATOR_TOKEN" environment variable not found')
    patreon_creator_refresh_token = os.getenv("PATREON_CREATOR_REFRESH_TOKEN", None)
    if not patreon_creator_refresh_token: raise EnvVariableNotFound('ERROR - init_patreon() - "PATREON_CREATOR_REFRESH_TOKEN" environment variable not found')
    patreon_creator_campaign_id = os.getenv("PATREON_CREATOR_CAMPAIGN_ID", None)
    if not patreon_creator_campaign_id: raise EnvVariableNotFound('ERROR - init_patreon() - "PATREON_CREATOR_CAMPAIGN_ID" environment variable not found')

    patreon_info = PatreonInfo( \
        client_id=patreon_client_id, \
        client_secret=patreon_client_secret, \
        creator_id=patreon_creator_id, \
        creator_token=patreon_creator_token, \
        creator_refresh_token=patreon_creator_refresh_token
    )
    webhook_registration_result_code, webhook_registration_result_data = patreon_info.register_unsubscribe_webhook(
        callback_webhook=WEBHOOK_PATREON_USER_UNSUBSCRIBED, 
        campaign_id=patreon_creator_campaign_id, 
        debug=DEBUG
    )
    if webhook_registration_result_code == 201:
        logger.info('Subscribed to Patreon event \'user unsubscribed\'')
    elif webhook_registration_result_code == 409:
        logger.info('Already subscribed to Patreon event \'user unsubscribed\'')
    else:
        logger.error(f'Unknown error: {webhook_registration_result_data}')

    return patreon_info

twitch_info = init_twitch()
patreon_info = init_patreon()
flask_app = flask.Flask(__name__)
database.check_or_create_db()
csrf_user_link_mapping = dict()
bot, GROUP_CHAT_ID = init_telegram()

# Empty webserver index, return nothing, just http 200
@flask_app.route(PATH_HOME, methods=['GET', 'HEAD'])
def index():
    return 'The bot is running fine :)'

# Handle incoming webhook updates by also putting them into the `update_queue` if
# the required parameters were passed correctly.
@flask_app.route(PATH_TELEGRAM, methods=['POST'])
def http_request_home():
    if flask.request.headers.get('content-type') == 'application/json':
        json_string = flask.request.get_data().decode('utf-8')
        if DEBUG: logger.debug('Bot received message - ', json_string)
        update = telebot.types.Update.de_json(json_string)
        if update: bot.process_new_updates([update])

        return ''
    else:
        flask.abort(403)

""" 
### Twitch SECTION 
"""
# 
@flask_app.route(PATH_TWITCH_OAUTH, methods=["GET", "POST"])
def webhook_twitch_user_oauth():
    if DEBUG: logger.debug('endpoint called')

    # Get query parameters from the URL
    params = flask.request.args
    user_code = params['code']
    scope = params['scope']
    csrf_token = params['state']

    # Get context information from CSRF token
    user_info = database.find_user_info_from_session(csrf_token)
    telegram_user_id = user_info[0]
    telegram_chat_id = user_info[1]

    # Log the incoming query parameters for demonstration
    if DEBUG: logger.debug(f"Received query parameters: {params}")

    # Get the auth (and refresh) token for this user
    access_token, _ = twitch_info.get_user_access_token(user_code, WEBHOOK_TWITCH_REFRESH_TOKEN, debug=True)

    # Get the Twitch username and ID for both the channel and the user
    _, twitch_user_id = twitch_info.get_user_data(access_token, debug=True)
    _, twitch_channel_id = twitch_info.get_channel_data(access_token, debug=True)

    # Check if the user is subscribed to the channel
    subscription_info = twitch_info.check_subscribed(access_token, twitch_user_id, twitch_channel_id)
    subscribed = True if subscription_info and len(subscription_info['data']) == 1 else False

    # If user is subscribed, add to Telegram group
    if subscribed:

        # If user has already created invite links, revoke them before creating a new one
        user_invite_links = database.find_links_by_telegram_id(telegram_user_id)
        for link in user_invite_links or []:
            result = bot.revoke_chat_invite_link(GROUP_CHAT_ID, link)
            if result.is_revoked:
                logger.info('Invite link revoked succesfully')
                logger.info('Removing invite link from database')
                if database.remove_link(link):
                    logger.info('Invite link removed successfully from database')
                else:
                    logger.error('Could not remove invite link from database')
            else:
                logger.error(f'Could not revoke invite link: {link}')

        # Create a single-use invite link
        invite = bot.create_chat_invite_link(
            chat_id = GROUP_CHAT_ID,
            #name = telegram_user_id,      #
            #expire_date = None,            # No expiry time, can be set if needed
            #member_limit = 1,              # Valid for one user only (if set, creates_join_request must be False)
            creates_join_request = True     # Requires approval by admin before being added (if True, member_limit must not be set)
        )
        # Store the newly created invite link in the DB
        database.store_link(
            telegram_user_id=telegram_user_id, 
            twitch_user_id=twitch_user_id, 
            patreon_user_id=None,
            invite_link=invite.invite_link)

        bot.send_message(telegram_chat_id, BOT_JOIN_TELEGRAM_GROUP.format(invite.invite_link))

    else:
        bot.send_message(telegram_chat_id, BOT_SUBSCRIPTION_NOT_ACTIVE, parse_mode='HTML')

    return ''

# 
@flask_app.route(PATH_TWITCH_OAUTH_CHANNEL, methods=['GET'])
def webhook_twitch_channel_oauth():
    if DEBUG: logger.debug('endpoint called')

    # Get query parameters from the URL
    params = flask.request.args
    user_code = params['code']
    scope = params['scope']

    # Log the incoming parameters
    if DEBUG: logger.debug(f"Received parameters: {params}")

    # Get the auth (and refresh) token for this user
    access_token, refresh_token = twitch_info.get_user_access_token(user_code, WEBHOOK_TWITCH_REFRESH_TOKEN)
    # Get the app access token
    app_access_token = twitch_info.get_app_access_token()

    # Get the username and ID for both the channel and the user
    user_username, user_id = twitch_info.get_user_data(access_token)
    channel_username, channel_id = twitch_info.get_channel_data(access_token)

    # Return result
    return '', 200

# 
@flask_app.route(PATH_TWITCH_REFRESH_TOKEN, methods=['GET'])
def webhook_twitch_refresh_token():
    if DEBUG: logger.debug('endpoint called')

    # Get query parameters from the URL
    params = flask.request.args

    return '', 200

# Handle user unsubscribed from channel (subscription expired or manually removed) 
# More info on this webhook at https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types/#channelsubscriptionend
@flask_app.route(PATH_TWITCH_USER_UNSUBSCRIBED, methods=["POST"])
def webhook_twitch_user_unsubscribed():
    if DEBUG: logger.debug('endpoint called')

    data = flask.request.json

    # If this is Twitch verifying the webhook, verify it and return
    if data and data['subscription']['status'] == 'webhook_callback_verification_pending':
        logger.info('Received a request to verify the webhook for "channel.subscription.end" event from Twitch.')
        return data['challenge'], 200

    # If this is a "user unsubscribed" event, process it
    if data and data["subscription"]["type"] == "channel.subscription.end":

        unsubscribed_user_id = data['event']['user_id']
        unsubscribed_user_username = data['event']['user_login']

        try:
            # Remove the user (ban) from the group.
            # until_date must be more than 30s, or it will be considered banned forever.
            # remoke_messages set to False, we don't want to remove the messages sent by this user
            until_date = datetime.datetime.now() + datetime.timedelta(0,60)
            bot.ban_chat_member(GROUP_CHAT_ID, unsubscribed_user_id, until_date, revoke_messages=False)

            # Unban the user right away, otherwise it will not be able to user invite links to join again.
            # By default, this method guarantees that after the call the user is not a member of the chat,
            # but will be able to join it. So if the user is a member of the chat they will also be removed
            # from the chat. If you don't want this, use the parameter only_if_banned.
            time.sleep(0.5)
            bot.unban_chat_member(GROUP_CHAT_ID, unsubscribed_user_id, only_if_banned=True)

        except ApiTelegramException as e:
            # Since this webhook gets triggered whether or not a user is part of the Telegram group, 
            # we need to handle the case where the user is not part of the group
            if e.description.conatins('PARTICIPANT_ID_INVALID'):
                logger.info(f"{unsubscribed_user_username} unsubscribed from Twitch, " \
                    "but was not part of the Telegram group. More data available here:", data)
            else:
                raise e

        return 'removed', 200

    elif not data:
        return 'got no reply', 400

    else:
        return 'ignored', 200


""" 
## Patreon SECTION
"""
# 
@flask_app.route(PATH_PATREON_OAUTH, methods=["GET", "POST"])
def webhook_patreon_user_oauth():
    if DEBUG: logger.debug('endpoint called')

    # Get query parameters from the URL
    params = flask.request.args
    user_code = params['code']
    csrf_token = params['state']
    if DEBUG: logger.debug(f"Received query parameters: {params}")

    # Get context information from CSRF token
    user_info = database.find_user_info_from_session(csrf_token)
    telegram_user_id = user_info[0]
    telegram_chat_id = user_info[1]

    # Get the auth token for this user
    access_token, _ = patreon_info.get_access_token(
        user_code=user_code, 
        webhook_refresh_token=WEBHOOK_PATREON_OAUTH,    # Must be the same as the one used by helper_platform_choice()
        debug=DEBUG
    )

    # Check if the user is a paying patron
    patron_user_id, paying_patron = patreon_info.is_user_paid_patron(access_token, debug=DEBUG)

    # If user is a paying patron, add to Telegram group
    if paying_patron:

        # If user has already created invite links, revoke them before creating a new one
        user_invite_links = database.find_links_by_telegram_id(telegram_user_id)
        for link in user_invite_links or []:
            result = bot.revoke_chat_invite_link(GROUP_CHAT_ID, link)
            if result.is_revoked:
                logger.info('Invite link revoked succesfully')
                logger.info('Removing invite link from database')
                if database.remove_link(link):
                    logger.info('Invite link removed successfully from database')
                else:
                    logger.error('Could not remove invite link from database')
            else:
                logger.error(f'Could not revoke invite link: {link}')

        # Create a single-use invite link
        invite = bot.create_chat_invite_link(
            chat_id = GROUP_CHAT_ID,
            #name = telegram_user_id,      #
            #expire_date = None,            # No expiry time, can be set if needed
            #member_limit = 1,              # Valid for one user only (if set, creates_join_request must be False)
            creates_join_request = True     # Requires approval by admin before being added (if True, member_limit must not be set)
        )
        # Store the newly created invite link in the DB
        database.store_link(
            telegram_user_id=telegram_user_id, 
            twitch_user_id=None, 
            patreon_user_id=patron_user_id,
            invite_link=invite.invite_link)

        bot.send_message(telegram_chat_id, BOT_JOIN_TELEGRAM_GROUP.format(invite.invite_link))

    else:
        bot.send_message(telegram_chat_id, BOT_SUBSCRIPTION_NOT_ACTIVE, parse_mode='HTML')

    return '', 200

# 
@flask_app.route(PATH_PATREON_REFRESH_TOKEN, methods=['GET'])
def webhook_patreon_refresh_token():
    if DEBUG: logger.debug('endpoint called')

    # Get query parameters from the URL
    params = flask.request.args

    return '', 200

# Handle user unsubscribed from creator (subscription expired or manually removed) 
# More info on this webhook at https://docs.patreon.com/#apiv2-webhook-endpoints
@flask_app.route(PATH_PATREON_USER_UNSUBSCRIBED, methods=["POST"])
def webhook_patreon_user_unsubscribed():
    if DEBUG: logger.debug('endpoint called')

    data = flask.request.json
    headers = flask.request.headers

    logger.info('Received a Patreon webhook:', headers, "-", data)

    # If this is Twitch verifying the webhook, verify it and return
    if data and data['subscription']['status'] == 'webhook_callback_verification_pending':
        
        return data['challenge'], 200

    return 'ignored', 200



""" 
### Telegram bot SECTION 
"""
# Handle '/start' 
@bot.message_handler(commands=['start'])
def command_start(message):
    if DEBUG: logger.debug('DEBUG - bot - /start command received')

    # Define inline buttons for reply options
    keyboard = [
        [TelebotTypes.InlineKeyboardButton(BOT_REPLY_READY, callback_data='add_me')],
        [TelebotTypes.InlineKeyboardButton(BOT_REPLY_NOT_READY, callback_data='finish')],
    ]
    reply_markup = TelebotTypes.InlineKeyboardMarkup(keyboard)

    bot.send_message(message.chat.id, BOT_MESSAGE_WELCOME, reply_markup=reply_markup)

# Handle all chat join requests, verify user has the right to join
@bot.chat_join_request_handler()
def handle_join_chat_request(message: telebot.types.ChatJoinRequest):

    user_id = message.from_user.id
    if user_id != bot.bot_id:
        used_invite_link = message.invite_link.invite_link if message.invite_link else None

        if used_invite_link and database.user_owns_link(user_id, used_invite_link):
            bot.approve_chat_join_request(GROUP_CHAT_ID, user_id)
            bot.send_message(GROUP_CHAT_ID, BOT_WELCOME_TO_GROUP.format(message.from_user.username))

            result = bot.revoke_chat_invite_link(GROUP_CHAT_ID, used_invite_link)
            if result.is_revoked:
                logger.info('Invite link revoked succesfully')
                logger.info('Removing invite link from database')
                if database.remove_link(used_invite_link):
                    logger.info('Invite link removed from database')
                else:
                    logger.error('Could not remove invite link from database')
                
                if database.remove_user_session(user_id):
                    logger.info('User session removed from database')
                else:
                    logger.error('Could not remove user session')
            else:
                logger.error(f'Could not revoke invite link: {used_invite_link}')

        else:
            bot.decline_chat_join_request(GROUP_CHAT_ID, user_id)

            try:
                bot.send_message(user_id, BOT_USER_TRIED_CHEATING)
            except ApiTelegramException as e:
                logger.error(f"Sending message to user trying to sneak in failed with error: {e}")
            return


def helper_add_me(bot, requesting_user_id, chat_id):
    # Check if user requesting the invite link is already a member of the group
    group_chat_member = bot.get_chat_member(GROUP_CHAT_ID, requesting_user_id) if requesting_user_id else None
    if group_chat_member and group_chat_member.status in ['member', 'restricted', 'administrator', 'creator']:
        bot.send_message(chat_id, BOT_ALREADY_JOINED_GROUP)

    else:
        # Define inline buttons for reply options
        keyboard = [
            [TelebotTypes.InlineKeyboardButton('Twitch', callback_data='platform_twitch')],
            [TelebotTypes.InlineKeyboardButton('Patreon', callback_data='platform_patreon')],
            #[TelebotTypes.InlineKeyboardButton('Youtube', callback_data='platform_youtube')],
        ]
        reply_markup = TelebotTypes.InlineKeyboardMarkup(keyboard)

        bot.send_message(chat_id, BOT_MESSAGE_PLATFORM_CHECK, parse_mode='HTML', reply_markup=reply_markup)

@bot.callback_query_handler(func=lambda call: True, data=['add_me'])
def callback_query_add_me(call: telebot.types.CallbackQuery):
    if DEBUG: logger.debug(f'"Lo sono" button pressed: {call.data}')
    
    helper_add_me(bot, requesting_user_id=call.from_user.id, chat_id=call.message.chat.id)

@bot.message_handler(commands=['add_me'])
def command_add_me(message: telebot.types.Message):
    if DEBUG: logger.debug(f'Command "add-me" received: {message}')

    requesting_user_id = message.from_user.id if message.from_user else None
    helper_add_me(bot, requesting_user_id=requesting_user_id, chat_id=message.chat.id)


def helper_platform_choice(bot, platform, user_id, chat_id):
    csrf_token = ''.join(random.choices(string.ascii_letters, k=32))
        
    database.store_session(telegram_user_id=user_id, telegram_chat_from_id=chat_id, session_id=csrf_token)
    user_info = database.find_user_info_from_session(csrf_token)
    print(user_info)

    
    platform_link = None
    if platform == 'Twitch':
        platform_link = twitch_info.get_verify_subscription_link(
            callback_webhook = WEBHOOK_TWITCH_OAUTH,
            state_csrf = str(csrf_token)
        )
    elif platform == 'Patreon':
        platform_link = patreon_info.get_verify_subscription_link(
            callback_webhook = WEBHOOK_PATREON_OAUTH,
            state_csrf = str(csrf_token)
        )

    message_html = BOT_PLATFORM_CHOICE.format(platform=platform, link=platform_link)
    bot.send_message(chat_id, message_html, parse_mode='HTML')

# User requested to verify via TWITCH
@bot.callback_query_handler(func=lambda call: True, data=['platform_twitch'])
def callback_query_platform_twitch(call: telebot.types.CallbackQuery):
    if DEBUG: logger.debug(f'"Twitch" button pressed: {call.data}')

    helper_platform_choice(bot, "Twitch", call.from_user.id, call.message.chat.id)

# User requested to verify via TWITCH
@bot.message_handler(commands=['add_me_twitch'])
def command_platform_twitch(message: telebot.types.Message):
    if DEBUG: logger.debug(f'Command "add_me_twitch" received: {message}')

    requesting_user_id = message.from_user.id if message.from_user else None
    # Check if user requesting the invite link is already a member of the group
    group_chat_member = bot.get_chat_member(GROUP_CHAT_ID, requesting_user_id) if requesting_user_id else None
    if group_chat_member and group_chat_member.status in ['member', 'restricted', 'administrator', 'creator']:
        bot.send_message(message.chat.id, BOT_ALREADY_JOINED_GROUP)

    else:
        helper_platform_choice(bot, "Twitch", requesting_user_id, message.chat.id)

# User requested to verify via PATREON
@bot.callback_query_handler(func=lambda call: True, data=['platform_patreon'])
def callback_query_platform_patreon(call: telebot.types.CallbackQuery):
    if DEBUG: logger.debug(f'"Patreon" button pressed: {call.data}')

    helper_platform_choice(bot, "Patreon", call.from_user.id, call.message.chat.id)

# User requested to verify via PATREON
@bot.message_handler(commands=['add_me_patreon'])
def command_platform_patreon(message: telebot.types.Message):
    if DEBUG: logger.debug(f'Command "add_me_patreon" received: {message}')

    requesting_user_id = message.from_user.id if message.from_user else None
    # Check if user requesting the invite link is already a member of the group
    group_chat_member = bot.get_chat_member(GROUP_CHAT_ID, requesting_user_id) if requesting_user_id else None
    if group_chat_member and group_chat_member.status in ['member', 'restricted', 'administrator', 'creator']:
        bot.send_message(message.chat.id, BOT_ALREADY_JOINED_GROUP)

    else:
        helper_platform_choice(bot, "Patreon", requesting_user_id, message.chat.id)

# User requested to verify via YOUTUBE
@bot.callback_query_handler(func=lambda call: True, data=['platform_youtube'])
def callback_query_platform_youtube(call: telebot.types.CallbackQuery):
    if DEBUG: logger.debug(f'"Youtube" button pressed: {call.data}')

    #message_html = BOT_PLATFORM_CHOICE.format(platform='Youtube', link=VERIFY_SUBSCRIPTION_LINK)
    message_html = "Il reame di <b>Youtube</b>non è ancora pronto per essere utilizzato."
    bot.send_message(call.message.chat.id, message_html, parse_mode='HTML')


@bot.callback_query_handler(func=lambda call: True, data=['finish'])
def callback_query_finish(call: telebot.types.CallbackQuery):
    if DEBUG: logger.debug(f'"Non lo sono" button pressed: {call.data}')

    bot.answer_callback_query(call.id, "Answer is No")

# A user leaves the group
@bot.message_handler(func=lambda m: True, content_types=['left_chat_member'])
def on_user_removed(message: telebot.types.Message):

    # Process updates only from the main chat
    if message.chat.id == GROUP_CHAT_ID and message.left_chat_member:

        # Try sending a goodbye message to the user that left the chat
        try:
            bot.send_message(message.left_chat_member.id, BOT_REMOVED_FROM_CHAT)
        except ApiTelegramException as e:
            logger.error(f"Sending message to user kicked off of chat failed with error: {e}")
        return

    else:
        logger.info(f"Ignoring request coming from chat {message.chat.id}")

# This handler removes all service messages
@bot.message_handler(content_types=telebot.util.content_type_service)
def delall(message: telebot.types.Message):
    bot.delete_message(message.chat.id,message.message_id)


# Handles all other messages
@bot.message_handler(func=lambda message: True, content_types=['text'])
def echo_message(message):
    if message.chat.id not in [GROUP_CHAT_ID_DEV, GROUP_CHAT_ID_PROD]:
        reply_text = BOT_REQUEST_UNKNOWN + \
            "/start - " + BOT_COMMAND_DESCRIPTION_START + "\n\n" + \
            "/add_me - " + BOT_COMMAND_DESCRIPTION_ADD_ME + "\n\n" + \
            "/add_me_twitch - " + BOT_COMMAND_DESCRIPTION_ADD_ME_TWITCH
        bot.reply_to(message, reply_text)


# pythonanywhere uses a WSGI interface, meaning this script must not run flask_app.run()
# unless it gets executed explicitely run via command line.
if __name__ == '__main__':
    WEBHOOK_PORT = 5050 # 443, 80, 88 or 8443 (port need to be 'open')
    WEBHOOK_LISTEN = '127.0.0.1'  # In some VPS you may need to put here the IP addr

    # Start flask server
    flask_app.run(host=WEBHOOK_LISTEN, port=WEBHOOK_PORT, debug=True)