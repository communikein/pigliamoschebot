import requests
import urllib.parse

class PatreonInfo():

    __verify_subscription_link = 'https://patreon.com/oauth2/authorize' \
        '?client_id={client_id}' \
        '&response_type=code' \
        '&scope={scope}' \
        '&redirect_uri={redirect_uri}' \
        '&state={state_csrf}'
    
    __auth_scopes = 'identity identity.memberships campaigns campaigns.members campaigns.webhook'

    def __init__(self, client_id, client_secret, creator_id, creator_token, creator_refresh_token):
        self._client_id = client_id
        self._client_secret = client_secret
        self._creator_id = creator_id
        self._creator_token = creator_token
        self._creator_refresh_token = creator_refresh_token

    """ Get user access token """
    def get_access_token(self, user_code, webhook_refresh_token, debug=False):
        
        # Get the auth (and refresh) token for this user
        url = 'https://www.patreon.com/api/oauth2/token'
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        data = {
            'client_id': self._client_id,
            'client_secret': self._client_secret,
            'code': user_code,
            'grant_type': 'authorization_code',
            'redirect_uri': webhook_refresh_token
        }
        if debug: print('DEBUG - PatreonInfo.get_access_token() - ', data)

        response = requests.post(url, data=data, headers=headers)
        response_code = response.status_code
        response_data = response.json()

        if response_data and all(field in response_data.keys() for field in ['access_token', 'refresh_token']):
            return response_data['access_token'], response_data['refresh_token']
        else:
            print('ERROR - PatreonInfo.get_access_token() - Error fetching user access and refresh tokens.')
            if debug: print(f'DEBUG - PatreonInfo.get_access_token() - Details: {response_code} - {response_data}')
            return None, None
    
    """ Check if user is a currently paying patron """
    def is_user_paid_patron(self, access_token, debug=False):
        is_paid_patron = False

        patron_user_id, pledges = self.get_user_pledges(access_token, debug)
        for pledge_id in pledges:
            amount_cents_total = sum([tier['amount_cents'] for tier in pledges[pledge_id]['tier']])
            if pledges[pledge_id]['creator']['id'] == self._creator_id and amount_cents_total > 0:
                is_paid_patron = True
        
        return patron_user_id, is_paid_patron

    """ Get all pledges for a user """
    def get_user_pledges(self, access_token, debug=False):
        # Get the auth (and refresh) token for this user
        url = 'https://www.patreon.com/api/oauth2/v2/identity'
        headers = {
        "Authorization": f"Bearer {access_token}"
        }
        params_pledge = {
            "include": "memberships.campaign.creator,memberships.currently_entitled_tiers",
            "fields[user]": "full_name,vanity",
            "fields[tier]": "amount_cents",
        }
        response = requests.get(url, headers=headers, params=params_pledge)
        data = response.json()

        # Parse patron user id
        patron_user_id = data.get("data", {}).get("id", None)

        # Parse creators info
        creators_raw = [item for item in data.get("included", []) if item["type"] == "user"]
        creators = {}
        for item in creators_raw:
            creators[item.get('id')] = item.get("attributes", {})
        
        # Parse campaigns info
        campaigns_raw = [item for item in data.get("included", []) if item["type"] == "campaign"]
        campaigns = {}
        for item in campaigns_raw:
            campaign_id = item.get('id')
            creator_id = item.get("relationships", {}).get("creator", {}).get("data", {}).get("id", None)
            campaigns[campaign_id] = {
                'creator_id': creator_id,
                'creator_info': creators[creator_id]
            }

        # Parse memberships info
        memberships_raw = [item for item in data.get("included", []) if item["type"] == "member"]
        memberships = {}
        for membership in memberships_raw:
            member_id = membership.get("id")
            campaign_id = membership.get("relationships", {}).get("campaign", {}).get("data", {}).get("id", None)
            tiers_id_raw = membership.get("relationships", {}).get("currently_entitled_tiers", {}).get("data", [])

            if campaign_id in campaigns:
                memberships[member_id] = {
                    'campaign': {
                        'id': campaign_id,
                    },
                    'creator': {
                        'id': campaigns[campaign_id]['creator_id'],
                        'full_name': campaigns[campaign_id]['creator_info']['full_name'],
                        'vanity': campaigns[campaign_id]['creator_info']['vanity'],
                    },
                    'tier': [{
                        'id': tier.get('id', None),
                        'amount_cents': None
                    } for tier in tiers_id_raw]
                }

        # Parse tiers info
        tiers_raw = [item for item in data.get("included", []) if item["type"] == "tier"]
        tiers = {}
        for tier in tiers_raw:
            tier_id = tier.get("id")
            tier_amount_cents = tier.get("attributes", {}).get("amount_cents", None)

            tiers[tier_id] = {
                'amount_cents': tier_amount_cents
            }
        
        # Combine all info
        for membership_id in memberships:
            for tier in memberships[membership_id]['tier']:
                tier_selected = tiers[tier['id']]
                tier['amount_cents'] = tier_selected['amount_cents']
        
        if debug: print('DEBUG - PatreonInfo.check_subscribed() - memberships:', memberships)
        
        return patron_user_id, memberships

    """ Return the link to verify if a user is subscribed """
    def get_verify_subscription_link(self, callback_webhook, state_csrf):
        if self._client_id:
            scope = urllib.parse.quote(self.__auth_scopes)
            url = urllib.parse.quote(callback_webhook)
            return self.__verify_subscription_link.format(client_id=self._client_id, redirect_uri=url, scope=scope, state_csrf=state_csrf)
        else:
            return None



    """ Get list of events with webhook subscribed """
    def get_events_subscribed(self, token=None, debug=False):

        if not token: token = self._creator_token

        url = 'https://www.patreon.com/api/oauth2/v2/webhooks'
        headers = {
            'Authorization': f'Bearer {token}'
        }
        params = {
            "fields[webhook]": "last_attempted_at,num_consecutive_times_failed,paused,secret,triggers,uri",
        }

        response = requests.get(url, headers=headers, params=params)
        data = response.json()

        if data and 'data' in data:
            if len(data['data']) > 0:
                events_subscribed = data['data']
                print(f'INFO - PatreonHelper.get_events_subscribed() - Found {len(events_subscribed)} events.')
                if debug: print(f'DEBUG - PatreonHelper.get_events_subscribed() - Details: {events_subscribed}')
                return events_subscribed
            else:
                print('INFO - PatreonHelper.get_events_subscribed() - Found 0 events.')
                return []
        else:
            print('ERROR - PatreonHelper.get_events_subscribed() - Error fetching event subscription details.')
            if debug: print(f'DEBUG - PatreonHelper.get_events_subscribed() - Details: {data}')
            return None

    """ Register a webhook for channel subscription end. """
    def register_unsubscribe_webhook(self, callback_webhook, campaign_id, token=None, debug=False):

        # If no token is provided, use the creator token
        if not token: token = self._creator_token

        # If webhook already registered, do not register a new one
        events_subscribed = self.get_events_subscribed(token=token)
        if debug: print("DEBUG - PatreonHelper.register_unsubscribe_webhook() - Already registered webhooks:", events_subscribed)
        if events_subscribed and [e for e in events_subscribed if e['attributes']['uri'] == callback_webhook]:
            return 409, None

        # Otherwise, register the webhook
        url = 'https://www.patreon.com/api/oauth2/v2/webhooks'
        headers = {
            'Authorization': f'Bearer {token}'
        }
        triggers = ['members:pledge:delete', 'members:pledge:update', 'members:delete', 'members:update']
        data = {
            "data": {
                "type": "webhook",
                "attributes": {
                    "triggers": triggers,
                    "uri": callback_webhook,
                },
                "relationships": {
                    "campaign": {
                        "data": {"type": "campaign", "id": str(campaign_id)},
                    },
                },
            },
        }
        response = requests.post(url, json=data, headers=headers)
        response_json = response.json()
        response_code = response.status_code
        print("INFO - PatreonHelper.register_unsubscribe_webhook() - Registering the user unsubscribed event:", response_code, "-", response_json)

        return response_code, response_json
    
    """ Delete a webhook by ID. """
    def delete_webhook(self, webhook_id, token=None, debug=False):
        print(f'INFO - PatreonHelper.delete_webhook() - Deleting webhook id {webhook_id}.')

        if not token: token = self._creator_token

        url = f'https://www.patreon.com/api/oauth2/v2/webhooks/{webhook_id}'
        headers = {'Authorization': f'Bearer {token}'}

        response = requests.delete(url, headers=headers)
        response_code = response.status_code

        if response_code == 204:
            print(f'INFO - PatreonHelper.delete_webhook() - SUCCESS: deleted webhook id {webhook_id}.')
            return True
        else:
            print(f'ERROR - PatreonHelper.delete_webhook() - Error deleting webhook id {webhook_id}.')
            if debug: print(f'DEBUG - PatreonHelper.get_events_subscribed() - Details: {response_code} - {response.json()}')
            return False
    
    """ Delete all webhooks. """
    def delete_all_webhooks(self):
        print(f'INFO - PatreonHelper.delete_webhook() - Deleting all webhooks.')

        webhooks = self.get_events_subscribed()

        for webhook in webhooks or []:
            self.delete_webhook(webhook_id=webhook['id'])
