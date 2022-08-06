# bot.py
from __future__ import print_function

import os
import random

from discord.ext import commands
from discord.utils import get
from dotenv import load_dotenv
# for google sheets stuff
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2 import service_account
# for FTP stuff
from datetime import datetime
from ftplib import FTP
import json

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

# Add/vote tracking
players_added = 0
vote_message_id = 0

# PROGRAMATIC / LOGIC STUFF

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
    
    # Overwrite added players with specified players
    global players_added
    players_added = players #(int("STR"))

    return maps_filtered

def hampalyze_logs():
    # Connect to FTP using info from .env file
    ftp = FTP()
    ftp.connect(os.getenv('BOP_IP'), 21)
    ftp.login(os.getenv('BOP_UN'), os.getenv('BOP_PW'))
    ftp.cwd('/tfc/logs') # Navigate to the logs subfolder
    
    # Get the list of files in the logs folder
    logFiles = list(reversed(ftp.nlst())) # Reverse the list of logs so it's in descending order
    firstLog = None
    secondLog = None
    round1log = None # Redundant, workaround for my own inadequacies
    round2log = None # Redundant, workaround for my own inadequacies

    for logFile in logFiles[:300]: # Just check the last few logs
        if ".log" not in logFile:
            continue

        # not using json stuff currently
        # if 'logFiles' in prevlog and logFile in prevlog['logFiles']:
        #     print("already parsed the latest log")
        #     return

        # Log files from 4v4 games are generally over 100k bytes
        if int(ftp.size(logFile)) > 50000: # Log files from 2v2 games may be more like 70k
            # Hamp's inhouse bot does this and I don't fully understand it but it works like magic - thanks hamp!
            logModified = datetime.strptime(ftp.voidcmd("MDTM %s" % logFile).split()[-1], '%Y%m%d%H%M%S')
            if firstLog is None:
                print(logFile + ' is set to round2log')
                round2log = logFile
                firstLog = (logFile, logModified)
                continue

            # otherwise, verify that there was another round played at least <60 minutes within the last found log
            if (firstLog[1] - logModified).total_seconds() < 3600:
                round1log = logFile
                print(logFile + ' is set to round1log')
                secondLog = (logFile, logModified)

            # if secondLog is not populated, this is probably the first pickup of the day; abort
            break

    # Abort if we didn't find two logs
    if firstLog is None or secondLog is None:
        print('Could not find a log')
        return

    # Retrieve first log file (most recent; round 2)
    # ftp.retrbinary("RETR %s" % round2log, open('logs/%s' % round2log, 'wb').write) # Not sure why this doesn't work
    with open(round2log, 'wb') as fp: # Workaround
        print('Downloading ' + round2log)
        ftp.retrbinary('RETR {0}'.format(round2log), fp.write) 

    # Retrieve second log file (round 1)
    # ftp.retrbinary("RETR %s" % secondLog[0], open('logs/%s' % secondLog[0], 'wb').write) # Not sure why this doesn't work
    with open(round1log, 'wb') as fp: # Workaround
        print('Downloading ' + round1log)
        ftp.retrbinary('RETR {0}'.format(round1log), fp.write) 
    
    # Send the retrieved log files to hampalyzer
    hampalyze = 'curl -X POST -F logs[]=@%s -F logs[]=@%s http://app.hampalyzer.com/api/parseGame' % (round1log, round2log)
    # Capture the result
    output = os.popen(hampalyze).read()
    print(output)

    # Check if it worked or not
    status = json.loads(output)
    if 'success' in status:
        site = "http://app.hampalyzer.com" + status['success']['path']
        print("Parsed logs available: %s" % site)
        # not using json stuff currently
        # with open('prevlog.json', 'w') as f:
        #     prevlog = { 'site': site, 'logFiles': [ firstLog[0], secondLog[0] ] }
        #     json.dump(prevlog, f)
    else:
        print('error parsing logs: %s' % output)
    
    return site # Give the hampalyzer link

# DISCORD BOT STUFF
# Bot expects !commands
bot = commands.Bot(command_prefix='!')

    # TODO: track how many players have done !add and give hints about next steps (!maps2 or add more or !maps3 etc)
    # TODO: automatically newmaps
    # TODO: some kind of vote tracking/closure system?

# Command for testing / debugging things.
@bot.command(name='test', help='Debugging/helper command because Nomad is kind of dumb.')
async def test_stuff(ctx):
    test_output = ('testing')
    #test_output = (vote_message_id)
    test_message = await ctx.send(test_output)
    await ctx.send(test_message.id)

# Command for linking rolodex.
@bot.command(name='rolodex', help='Link to TFC rolodex sheet.')
async def rolodex(ctx):
    rolodex_link = ('https://docs.google.com/spreadsheets/d/1oCbcf-TwQOoW9u9Zu5rHeWZt7uZAkoV9ctfmidDFcYo/')
    await ctx.send(rolodex_link)

# Command for tracking player adds.
# TODO: track by username to avoid duplicate adds
@bot.command(name='add', help='Enqueue yourself.')
async def adding(ctx):
    global players_added
    players_added += 1
    team_size = str(int(players_added/2)) + 'v' + str(int(players_added/2))
    print(str(players_added) + ' in the queue, using ' + team_size + ' maps')

# Command for tracking player adds.
# TODO: track by username to avoid duplicate adds
@bot.command(name='remove', help='Abandon your friends.')
async def removing(ctx):
    global players_added
    players_added -= 1
    team_size = str(int(players_added/2)) + 'v' + str(int(players_added/2))
    print(str(players_added) + ' in the queue, using ' + team_size + ' maps')

# Command for pulling maps.
# TODO: separate some of this logic into its own function (pre-filter all maps by playercount?)
@bot.command(name='maps', help='Returns 3 random maps from neon\'s spreadsheet, use !maps 3 for 3v3, !maps 4 for 4v4 etc.')
async def choose_maps(ctx, players='2'):
    # Filter the maplist based on player count
    maplistsheets = filter_maps(players)

    # # Announce and then reset the player count
    # global players_added
    # team_size = str(int(players_added/2)) + 'v' + str(int(players_added/2))
    # print(str(players_added) + ' in the queue, using ' + team_size + ' maps')
    # players_added = 0
    
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
    
    # Keep track of the most recent vote message
    global vote_message_id
    vote_message_id = message.id

    # Add reactions for vote tracking
    emojis = ['1️⃣', '2️⃣', '3️⃣', '4️⃣']
    for emoji in emojis:
        await message.add_reaction(emoji)

# # Automatically get new maps if newmaps won the vote
# @bot.event
# async def on_raw_reaction_add(payload):
#     if payload.channel_id: #== 614467771866021944:
#         print(payload.channel_id)
#         if payload.emoji.name == "4️⃣":
#             channel = bot.get_channel(payload.channel_id)
#             print(channel)
#             message = await channel.fetch_message(payload.message_id)
#             print(message)
#             reaction = get(message.reactions, emoji=payload.emoji.name)
#             print(reaction)
#             if reaction and reaction.count > 1:
#                 # await message.delete()
#                 #await ctx.send('VOTE TRACKING TEST')
#                 await message.add_reaction('😄')

# Automatically get new maps if newmaps won the vote
@bot.event
async def on_reaction_add(reaction, user):
    # Only care about reactions to the most recent vote
    if reaction.message.id == vote_message_id:
        if reaction.emoji == "4️⃣":
        #     channel = bot.get_channel(payload.channel_id)
        #     message = await channel.fetch_message(payload.message_id)
        #     reaction = get(message.reactions, emoji=payload.emoji.name)
            if reaction and reaction.count > 1:
        #         # await message.delete()
        #         #await ctx.send('VOTE TRACKING TEST')
                await reaction.message.add_reaction('😄')
                cmd = bot.get_command("maps")
                await cmd(ctx, "positional argument", kwarg='etc')
                #await ctx.invoke(self.bot.get_command('') choose_maps(ctx, players_added)

# retrieve logs from FTP and get hampalyzer link
@bot.command(name='stats', help='Hamaplyze most recent pair of large log files from FTP.')
async def get_logs(ctx):
    logs_link = hampalyze_logs()
    await ctx.send(logs_link)
  
#   # for posting the actual log files to discord
#   firstfile, secondfile = hampalyze_logs() 
#   await message.channel.send(file=discord.File(firstfile))
#   await message.channel.send(file=discord.File(secondfile))
#   # delete the downloaded files
#   os.unlink(firstfile) 
#   os.unlink(secondfile)

# @bot.event
# async def on_message(message):
#   if message.author == bot.user:
#     return
#   if message.content.startswith('$gimme'):
#     firstfile, secondfile = download_random_file()
#     # file_downloaded = getLastGameLogs()
#     await message.channel.send(file=discord.File(firstfile))
#     os.unlink(firstfile) #Delete the downloaded file
#     await message.channel.send(file=discord.File(secondfile))
#     os.unlink(secondfile) #Delete the downloaded file

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
    # print('We have logged in as {0.user}'.format(bot))

# Start the bot when this file is running
bot.run(TOKEN)
