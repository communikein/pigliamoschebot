import requests
import urllib.parse

class TwitchInfo():

    #TODO: Fix 400 Error "Missing Response Type": https://discuss.dev.twitch.com/t/how-to-resolve-missing-response-type/37674

    __verify_subscription_link = 'https://id.twitch.tv/oauth2/authorize' \
        '?client_id={client_id}' \
        '&force_verify=true' \
        '&response_type=code' \
        '&scope=user:read:subscriptions' \
        '&redirect_uri={redirect_uri}' \
        '&state={state_csrf}'

    def __init__(self, client_id, client_secret, twitch_secret, channel_id, channel_username):
        self._client_id = client_id
        self._client_secret = client_secret
        self._twitch_secret = twitch_secret
        self._channel_id = channel_id
        self._channel_username = channel_username


    """ Get user token """
    def get_user_access_token(self, code, callback_webhook, debug=False):
        url = 'https://id.twitch.tv/oauth2/token'
        params = {
            'client_id': self._client_id,
            'client_secret': self._client_secret,
            'code': code,
            'grant_type': 'authorization_code',
            'redirect_uri': callback_webhook
        }
        print('TEST - TwitchInfo - ', params)

        response = requests.post(url, params=params)
        data = response.json()
        if debug: print('DEBUG - TwitchHelper.get_user_access_token() - ', data)

        if data and all(field in data.keys() for field in ['access_token', 'refresh_token']):
            return data['access_token'], data['refresh_token']
        else:
            print('ERROR - TwitchHelper.get_user_access_token() - Error fetching user access and refresh tokens.')
            if debug: print(f'DEBUG - TwitchHelper.get_user_access_token() - Details: {data}')
            return None, None

    """ Get app token """
    def get_app_access_token(self, debug=False):
        url = 'https://id.twitch.tv/oauth2/token'
        data = {
            'client_id': self._client_id,
            'client_secret': self._client_secret,
            'grant_type': 'client_credentials'
        }

        response = requests.post(url, data=data)
        data = response.json()
        if debug: print('DEBUG - TwitchHelper.get_app_access_token() - ', data)

        if data and 'access_token' in data:
            return data['access_token']
        else:
            print('ERROR - TwitchHelper.get_app_access_token() - Error fetching app access token.')
            if debug: print(f'Details: {data}')
            return None

    """ Get channel ID and username """
    def get_channel_data(self, access_token, debug=False):
        headers = {
            'Client-ID': self._client_id,
            'Authorization': f'Bearer {access_token}'
        }

        url = 'https://api.twitch.tv/helix/users'
        params = {'login': self._channel_username}
        response = requests.get(url, headers=headers, params=params)
        data = response.json()
        if debug: print('DEBUG - TwitchHelper.get_channel_data() - ', data)

        if 'data' in data and 'id' in data['data'][0]:
            id = data['data'][0]['id']
            return self._channel_username, id
        else:
            print('ERROR - TwitchHelper.get_channel_data() - Error fetching channel ID.')
            if debug: print(f'DEBUG - TwitchHelper.get_channel_data() - Details: {data}')
            return None, None

    """ Get user ID and username """
    def get_user_data(self, access_token, debug=False):
        headers = {
            'Client-ID': self._client_id,
            'Authorization': f'Bearer {access_token}'
        }

        url = 'https://id.twitch.tv/oauth2/validate'
        params = {}

        response = requests.get(url, headers=headers, params=params)
        data = response.json()
        if debug: print('DEBUG - TwitchHelper.get_user_data() - ', data)

        if 'user_id' in data:
            id = data['user_id']
            username = data['login']
            return username, id
        else:
            print('ERROR - TwitchHelper.get_user_data() - Error fetching user ID.')
            if debug: print(f'DEBUG - TwitchHelper.get_user_data() - Details: {data}')
            return None, None

    """ Check if user is subscribed to channel """
    def check_subscribed(self, access_token, user_id, broadcaster_id, debug=False):
        url = 'https://api.twitch.tv/helix/subscriptions/user'
        params = {
            'broadcaster_id': broadcaster_id,
            'user_id': user_id
        }
        headers = {
            'Client-ID': self._client_id,
            'Authorization': f'Bearer {access_token}'
        }

        response = requests.get(url, headers=headers, params=params)
        data = response.json()

        if 'data' in data:
            subscription_details = data
            return subscription_details
        else:
            print('ERROR - TwitchHelper.check_subscribed() - Error fetching subscription details.')
            if debug: print(f'DEBUG - TwitchHelper.check_subscribed() - Details: {data}')
            return None

    """ Get list of events with webhook subscribed """
    def get_events_subscribed(self, token=None, any_status=False, debug=False):

        if not token: token = self.get_app_access_token()

        url = 'https://api.twitch.tv/helix/eventsub/subscriptions'
        headers = {
            'Client-ID': self._client_id,
            'Authorization': f'Bearer {token}'
        }

        response = requests.get(url, headers=headers)
        data = response.json()
        if debug: print(data)

        if 'data' in data:
            if len(data['data']) > 0:
                events_subscribed = data['data']
                if not any_status:
                    events_subscribed = [event for event in data['data'] if event['status'] == 'enabled']
                print(f'INFO - TwitchHelper.get_events_subscribed() - Found {len(events_subscribed)} events.')
                if debug: print(f'Details: {events_subscribed}')
                return events_subscribed
            else:
                print('INFO - TwitchHelper.get_events_subscribed() - Found 0 events.')
                return []
        else:
            print('ERROR - TwitchHelper.get_events_subscribed() - Error fetching event subscription details.')
            if debug: print(f'DEBUG - TwitchHelper.get_events_subscribed() - Details: {data}')
            return None

    """ Register a webhook for channel subscription end. """
    def register_unsubscribe_webhook(self, callback_webhook):

        event_type = "channel.subscription.end"

        # Get the app access token
        app_access_token = self.get_app_access_token()

        # If webhook already subscribed, return
        events_subscribed = self.get_events_subscribed(token=app_access_token)
        if events_subscribed and [e for e in events_subscribed if e['type'] == event_type and e['transport']['callback'] == callback_webhook]:
            return 202, None

        # If webhook not already subscribed, subscribe to webhook
        url = "https://api.twitch.tv/helix/eventsub/subscriptions"
        headers = {
            "Client-ID": self._client_id,
            "Authorization": f"Bearer {app_access_token}",
            "Content-Type": "application/json",
        }
        data = {
            "type": event_type,
            "version": "1",
            "condition": {"broadcaster_user_id": f"{self._channel_id}"},
            "transport": {
                "method": "webhook",
                "callback": callback_webhook,
                "secret": "your_webhook_secret",
            },
        }
        response = requests.post(url, json=data, headers=headers)
        print("INFO - TwitchHelper.register_unsubscribe_webhook() - Trying to register the user unsubscribed event -", response.json())

        return response.status_code, response.json()

    """ Return the link to verify if a user is subscribed """
    def get_verify_subscription_link(self, callback_webhook, state_csrf):
        if self._client_id:
            url = urllib.parse.quote(callback_webhook)
            return self.__verify_subscription_link.format(client_id=self._client_id, redirect_uri=url, state_csrf=state_csrf)
        else:
            return None