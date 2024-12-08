import logging
import requests
import urllib.parse

class PatreonInfo():

    __verify_subscription_link = ''

    def __init__(self):

        self.__logger = logging.getLogger(__name__)
        self.__logger.basicConfig(
            filename=f'./logs/pigliamoschebot.log', 
            encoding='utf-8', 
            filemode='a', 
            style="{", 
            datefmt="%Y-%m-%d %H:%M", 
            format="{asctime}# {levelname} - {name}.{funcName} - {message}",
            level = logging.DEBUG)

    """ Get user access token """
    def get_access_token(self):
        pass