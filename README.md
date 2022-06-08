"# TFC" 

# Nomad's discord bot for TFC stuff

Currently this just pulls data from a Google Sheets document based on some criteria and spits it back to the server with some reactions attached.
It's very dumb. There are no clever features at all. It takes 1 argument which is just for querying hardcoded values in the spreadsheet.

## Usage

If you want to put this bot in your server send me a message (Nomad#6589) and I'll get you the link.

If you want to make a copy of this code and run it yourself you're welcome to do that, you'll need a .env file with DISCORD_TOKEN=your_token, and a credentials.json file with your Google Sheets API OAuth info (see [here](https://developers.google.com/sheets/api/quickstart/python) for more information).

If you just want to use the bot the only command current supported is `!maps #` where # is the teamsize for the sheets lookup (`!maps 2` for 2v2, `!maps 4` for 4v4, etc). The bot will randomly select 3 maps from the list and post them for voting.

## TODO / wishlist

- Automatically newmaps (based on vote count being a certain ratio of player size?)
- Maybe expand it into a super basic pickup bot?