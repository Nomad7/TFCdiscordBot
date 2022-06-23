# bot.py
from __future__ import print_function

import os
import random
# import pickle

from discord.ext import commands
from dotenv import load_dotenv

from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2 import service_account
# from google.auth.transport.requests import Request
# from google.oauth2.credentials import Credentials
# from google.auth.exceptions import RefreshError



# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']

# The ID and range of Neon's gsheet of maps and team sizes.
MAPS_SPREADSHEET_ID = '1sXUDGC9XrRqKNbjq-qZeMNIgQDeRXdimEY1PZmXt6cY'
# This range includes the following fields:
# mapname: [name of map]
# style (not used): ctf|adl|r-ctf|1flag-ctf|cp|fun
# team sizes: 2v2 through 10v10 depending on map
# mirvs (not used): recommended mirv class count
MAPS_RANGE_NAME = 'Full List!A3:D'

# Using a Sheets API service account makes things easier.
# Remember to share the spreadsheet with the service account.
secret_file = os.path.join(os.getcwd(), 'SvcAcctCredentials.json')

# Initializing list of maps here
maps = []

def load_maps():
    creds = None
    # The file SvcAcctCredentials.json stores service account credentials
    # The spreadsheet must be shared with this service account
    if os.path.exists('SvcAcctCredentials.json'):
        creds = service_account.Credentials.from_service_account_file(secret_file, scopes=SCOPES)

    # If service account isn't set up, try prompting the user to log in
    else:
        flow = InstalledAppFlow.from_client_secrets_file(
            'credentials.json', SCOPES)
        creds = flow.run_local_server(port=0)

    # # Save the credentials for the next run - N/A with service account
    # https://developers.google.com/sheets/api/quickstart/python
    #     with open('token.json', 'w') as token:
    #         token.write(creds.to_json())

    # Pull the maps
    try:
        service = build('sheets', 'v4', credentials=creds)

        # Call the Sheets API and get the sheet range contents
        sheet = service.spreadsheets()
        result = sheet.values().get(spreadsheetId=MAPS_SPREADSHEET_ID,
                                    range=MAPS_RANGE_NAME).execute()
        values = result.get('values', [])

        # If it's empty say so
        if not values:
            print('No data found.')
            return
   
    except HttpError as err:
        print(err)
    
    return values

def filter_maps(players='2'):
    maps_filtered = [] # Initialize empty list
    # Check playercount so we can get the right maps
    match players:
        case '3':
            playercount = '3v3'
        case '4':
            playercount = '4v4'
        case '5':
            playercount = '5v5'
        case '6':
            playercount = '6v6'
        case '7':
            playercount = '7v7'
        case '8':
            playercount = '8v8'
        case '9':
            playercount = '9v9'
        case '10':
            playercount = '10v10'
        case _:
            playercount = '2v2'
    
    # Pull map names from column A (0) based on team sizes in column C (2)
    try:
        for row in maps:
            if playercount in row[2]:
                maps_filtered.append(row[0])
   
    except HttpError as err:
        print(err)
    
    return maps_filtered

# DISCORD BOT STUFF
# Bot expects !commands
bot = commands.Bot(command_prefix='!')

    # TODO: track how many players have done !add and give hints about next steps (!maps2 or add more or !maps3 etc)
    # TODO: automatically newmaps
    # TODO: some kind of vote tracking/closure system?

@bot.command(name='test', help='Debugging/helper command because Nomad is kind of dumb.')
async def test_stuff(ctx):
    response = ('testing')
    message = await ctx.send(response)

@bot.command(name='maps', help='Returns 3 random maps from neon\'s spreadsheet, use !maps 3 for 3v3, !maps 4 for 4v4 etc.')
async def choose_maps(ctx, players='2'):
    # Filter the maplist based on player count
    maplistsheets = filter_maps(players)
    
    # Get 3 at random
    # TODO: make this less than fully random? remember previous pick(s)?
    mapstochoose = [random.sample(maplistsheets,3)]
    print(mapstochoose)
    
    # Format response and offer a new maps option
    # TODO: update results with names of voters?
    # TODO: automatically newmaps at (playercount) total votes?
    response = ( '```'
        '1    ' + mapstochoose[0][0] + '\n'
        '2    ' + mapstochoose[0][1] + '\n'
        '3    ' + mapstochoose[0][2] + '\n'
        '4    newmaps```'
    )
    message = await ctx.send(response)

    # Add reactions for vote tracking
    emojis = ['1️⃣', '2️⃣', '3️⃣', '4️⃣']
    for emoji in emojis:
        await message.add_reaction(emoji)


# If something bad happens write it down
@bot.event
async def on_error(event, *args, **kwargs):
    with open('err.log', 'a') as f:
        if event == 'on_message':
            f.write(f'Unhandled message: {args[0]}\n')
        else:
            raise

# Bot's secret, see ID https://discord.com/developers/docs/topics/oauth2
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# Populate maplist on launch
maps = load_maps()

# Announce when ready
@bot.event
async def on_ready():
    print(f'{bot.user.name} has connected to Discord! Now online in these servers...')
    for i in bot.guilds:
        print(i)

# Start the bot when this file is running
bot.run(TOKEN)
