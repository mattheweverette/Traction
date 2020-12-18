import requests
import zipfile
import sqlite3
import json
import os
from requests.auth import HTTPBasicAuth


api_key = 'ece4108cc5834608b8ef65db3112070b'
api_url_base = 'https://www.bungie.net/Platform/'

client_id = '32592'
client_secret = 'Eu9Z1x47l.hVuBe0YvBAFlCStQ0qbel8OO-UjgyH498'
auth_url_base = 'https://www.bungie.net/en/OAuth/Authorize'


def get_access_token(code):
    access_token_url = f'{api_url_base}app/oauth/token/'

    headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }

    data = {
        'grant_type': 'authorization_code',
        'code': code
    }

    response = requests.post(
        access_token_url,
        data=data,
        headers=headers,
        auth=HTTPBasicAuth(client_id, client_secret)
    )

    response_data = response.json()

    print(response_data)

    return response_data['access_token'], response_data['refresh_token']


def refresh_access_token(refresh_token):
    access_token_url = f'{api_url_base}app/oauth/token/'

    headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }

    data = {
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token
    }

    response = requests.post(
        access_token_url,
        data=data,
        headers=headers,
        auth=HTTPBasicAuth(client_id, client_secret)
    )

    response_data = response.json()

    return response_data['access_token']


def get_display_name(access_token):
    url = f'{api_url_base}/User/GetCurrentBungieNetUser'

    headers = {
        'X-API-KEY': api_key,
        'Authorization': f'Bearer {access_token}'
    }

    response = requests.get(url, headers=headers)

    data = response.json()

    return data['Response']['displayName']


def get_membership(display_name):
    url = f'{api_url_base}Destiny2/SearchDestinyPlayer/All/{display_name}'

    headers = {'X-API-KEY': api_key}

    response = requests.get(url, headers=headers)
    data = json.loads(response.content.decode('utf-8'))

    membership_type = data['Response'][0]['membershipType']
    membership_id = data['Response'][0]['membershipId']

    return membership_type, membership_id


def get_character_id(membership_type, membership_id):
    url = (f'{api_url_base}Destiny2/{membership_type}/Profile/'
           f'{membership_id}/?components=100')

    headers = {'X-API-KEY': api_key}

    response = requests.get(url, headers=headers)
    data = json.loads(response.content.decode('utf-8'))

    character_id = data['Response']['profile']['data']['characterIds'][0]

    return character_id


def get_vendors(membership_type, membership_id, character_id, access_token):
    url = (f'{api_url_base}/Destiny2/{membership_type}/Profile/'
           f'{membership_id}/Character/{character_id}/Vendors/?components=400')

    headers = {
        'X-API-KEY': api_key,
        'Authorization': f'Bearer {access_token}'
    }

    response = requests.get(url, headers=headers)

    data = response.json()['Response']['vendors']['data']

    vendors = []
    for vendor in data:
        vendors.append(vendor)

    return vendors


def get_vendor(membership_type, membership_id, character_id, vendor_hash, access_token):
    url = (f'{api_url_base}/Destiny2/{membership_type}/Profile/'
           f'{membership_id}/Character/{character_id}/Vendors/{vendor_hash}/?components=402')

    headers = {
        'X-API-KEY': api_key,
        'Authorization': f'Bearer {access_token}'
    }

    response = requests.get(url, headers=headers)

    data = response.json()['Response']['sales']['data']

    sold_items = []
    for item in data:
        sold_items.append(data[item]['itemHash'])

    return sold_items


# code = input('code: ')
# print(get_access_token(code))

# name = 'xXGearZ HDXx'
# a = 'CKfaAhKGAgAgxQ4UBmtKqUaRKZIr1Aj++oWZp/p5MXcupAcj+pDX8YPgAAAA6MGP8PAQFm+EkAOJOXmiR47N7WDeECq4vj3RQR8WXQxdT/1Gxv0tlaJmT0GN+DKXZvhCbLEh1+QY7VEFNrqWGhgbLRFXeflslqh0G0E4d2pRJSxhNQBt03xeWyOR6HnqRAzm6wtTqNMaikG/2zNs8gPnH6AvyDkLAs8sgLYI/Xc9y1l/4eWHtP2A+hh69JPCNt4rzJJqoDFEHMCDuYUKtNqHGUjzcNYr+Eit62EJwYW26Tvyh4tVCEDYYJxampLI2O92N7O63luVjueVHRp4LUeq4aGBPk2eXADe7JKal38='
# t, i = get_membership(name)
#
# c = get_character_id(t, i)
# h = '4230408743'
#
# vs = get_vendors(t, i, c, a)
#
# sold_items = []
# for v in vs:
#     sold_items += get_vendor(t, i, c, v, a)


def update_manifest():
    print('Updating manifest...')
    headers = {'X-API-KEY': api_key}

    manifest_url = f'{api_url_base}Destiny2/Manifest'
    response = requests.get(manifest_url, headers=headers)

    content_path = response.json()['Response']['mobileWorldContentPaths']['en']
    content_url = f'https://www.bungie.net{content_path}'
    response = requests.get(content_url, headers=headers)

    with open('manifest.content.zip', 'wb') as zip:
        zip.write(response.content)

    print('Extracting manifest...')
    with zipfile.ZipFile('manifest.content.zip') as zip:
        zip.extractall()
        os.rename(zip.namelist()[0], 'manifest.content')

    conn = sqlite3.connect('manifest.content')
    c = conn.cursor()

    c.execute('SELECT json FROM DestinyInventoryItemDefinition')
    items = c.fetchall()

    item_jsons = [json.loads(item[0]) for item in items]

    print('Saving data...')
    for item in item_jsons:
        item_name = item['displayProperties']['name']
        item_hash = item['hash']
        print(item)
        print('break\n\n\n')


update_manifest()
