# bot.py
from __future__ import print_function

import os
import random
# import pickle

from discord.ext import commands
from dotenv import load_dotenv

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.exceptions import RefreshError
from google.oauth2 import service_account


# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']

# The ID and range of Neon's sheet of maps + team sizes.
SAMPLE_SPREADSHEET_ID = '1sXUDGC9XrRqKNbjq-qZeMNIgQDeRXdimEY1PZmXt6cY'
SAMPLE_RANGE_NAME = 'Full List!A3:D'
secret_file = os.path.join(os.getcwd(), 'SvcAcctCredentials.json')

def pullmaps(players='2'):
    pulledmaps = [] # i don't think this is necessary
    creds = None
    # the file SvcAcctCredentials.json stores service account credentials
    # the spreadsheet must be shared with this service account
    if os.path.exists('SvcAcctCredentials.json'):
        creds = service_account.Credentials.from_service_account_file(secret_file, scopes=SCOPES)

    # if service account isn't set up, try prompting the user
    else:
        flow = InstalledAppFlow.from_client_secrets_file(
            'credentials.json', SCOPES)
        creds = flow.run_local_server(port=0)
    # # Save the credentials for the next run - N/A with service account
    #     with open('token.json', 'w') as token:
    #         token.write(creds.to_json())

    #check playercount so we can get the right maps
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
    
    #pull the maps
    try:
        service = build('sheets', 'v4', credentials=creds)

        # Call the Sheets API
        sheet = service.spreadsheets()
        result = sheet.values().get(spreadsheetId=SAMPLE_SPREADSHEET_ID,
                                    range=SAMPLE_RANGE_NAME).execute()
        values = result.get('values', [])

        #if it's empty say so
        if not values:
            print('No data found.')
            return

        #pull map names from column A (0) based on team sizes in column C (2)
        for row in values:
            if playercount in row[2]:
                pulledmaps.append(row[0])
   
    except HttpError as err:
        print(err)
    
    return pulledmaps

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

bot = commands.Bot(command_prefix='!')

    #TODO: track how many players have done !add and give hints about next steps (!maps2 or add more or !maps3 etc)
    #TODO: automatically newmaps
    #TODO: some kind of vote tracking/closure system?

@bot.command(name='maps', help='Returns 3 random maps from neon\'s spreadsheet, use !maps 3 for 3v3, !maps 4 for 4v4 etc')
async def choose_maps(ctx, players):
    #populate the maplist from google sheets
    maplistsheets = pullmaps(players)
    
    #get 3 at random
    #TODO: make this less than fully random? remember previous pick(s)?
    mapstochoose = [random.sample(maplistsheets,3)]
    print(mapstochoose)
    
    #format response
    #TODO: update results with names of voters?
    #TODO: automatically newmaps at (playercount) total votes?
    response = ( '```'
        '1    ' + mapstochoose[0][0] + '\n'
        '2    ' + mapstochoose[0][1] + '\n'
        '3    ' + mapstochoose[0][2] + '\n'
        '4    newmaps```'
    )
    message = await ctx.send(response)

    #add reactions for vote tracking
    emojis = ['1️⃣', '2️⃣', '3️⃣', '4️⃣']
    for emoji in emojis:
        await message.add_reaction(emoji)


#if something bad happens write it down
@bot.event
async def on_error(event, *args, **kwargs):
    with open('err.log', 'a') as f:
        if event == 'on_message':
            f.write(f'Unhandled message: {args[0]}\n')
        else:
            raise

#lemme know when it's ready
@bot.event
async def on_ready():
    print(f'{bot.user.name} has connected to Discord!')

bot.run(TOKEN)
