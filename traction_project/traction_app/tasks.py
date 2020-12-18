import requests
import zipfile
import sqlite3
import json
import os
import ssl
import smtplib
from requests.auth import HTTPBasicAuth
from django.contrib.auth.models import User
from celery import shared_task
from .secrets import client_id, client_secret, api_url_base, api_key, email, password
from .models import Item


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
    data = response.json()

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
    url = (f'{api_url_base}/Destiny2/{membership_type}/Profile/{membership_id}'
           f'/Character/{character_id}/Vendors/{vendor_hash}/?components=402')

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


@shared_task
def get_access_token(user_id, code):
    user = User.objects.get(id=user_id)
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

    user.profile.access_token = response_data['access_token']
    user.profile.refresh_token = response_data['refresh_token']

    user.profile.display_name = get_display_name(user.profile.access_token)
    user.profile.membership_type, user.profile.membership_id = get_membership(user.profile.display_name)

    user.profile.save()


def refresh_access_token(user_id):
    user = User.objects.get(id=user_id)
    access_token_url = f'{api_url_base}app/oauth/token/'

    headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }

    data = {
        'grant_type': 'refresh_token',
        'refresh_token': user.profile.refresh_token
    }

    response = requests.post(
        access_token_url,
        data=data,
        headers=headers,
        auth=HTTPBasicAuth(client_id, client_secret)
    )

    response_data = response.json()

    user.profile.access_token = response_data['access_token']

    user.profile.save()


@shared_task
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
        if not Item.objects.filter(hash=item_hash).exists():
            Item.create(item_name, item_hash)

    print('Done!')

    email_users()


@shared_task
def email_users():
    print('Emailing users...')
    port = 465
    smtp_server = "smtp.gmail.com"
    message = """\
    Subject: Traction: {item}

    {item} is currently being sold in Destiny 2!"""

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(smtp_server, port, context=context) as server:
        server.login(email, password)
        for user in User.objects.all():
            refresh_access_token(user.id)
            c = get_character_id(
                user.profile.membership_type, user.profile.membership_id
            )

            vendors = get_vendors(
                user.profile.membership_type,
                user.profile.membership_id,
                c,
                user.profile.access_token
            )

            sold_items = []
            for vendor in vendors:
                sold_items += get_vendor(
                    user.profile.membership_type,
                    user.profile.membership_id,
                    c,
                    vendor,
                    user.profile.access_token
                )

            for item in sold_items:
                for tracked in user.profile.tracked_items.all():
                    if str(item) == tracked.hash:
                        server.sendmail(
                            email,
                            user.email,
                            message.format(item=tracked.name)
                        )
                        print('emailed someone')

    print('Done!')
