import discord
import os
import requests
import json
from replit import db
from keep_alive import keep_alive

client = discord.Client()

from riotwatcher import LolWatcher, ApiError

lolWatcher = LolWatcher(os.environ['RTOKEN'])
defaultServer = 'euw1'

# For Riot's API, the 404 status code indicates that the requested data wasn't found and
# should be expected to occur in normal operation, as in the case of a an
# invalid summoner name, match ID, etc.
#
# The 429 status code indicates that the user has sent too many requests
# in a given amount of time ("rate limiting").
pastClashes = [] # Past clashes, with Riot info. id matches serverClashes id
currentClashes = [] # Currently active/upcoming clashes
players = [
  {
    'id': 0,
    'discordTag': 'Kore#8756',
    'summonerName': 'Tithe',
    'server': defaultServer,
    'clashHistory': [], # List of indexes in pastClashes
    'clashWins': 2 # Total games won in clash  (will be used for team balancing feature)
  }
  ]

serverClashes = [
  {
    'id': 9999999,
    'date': '13/04/2021',
    'teamName': 'For the Shirts',
    'teamPlayers': [],
    'wins': 2,
    'losses': 1
  }
]

def get_tournaments():
  try:
    response = lolWatcher.clash.tournaments(defaultServer)
    return response
  except ApiError as err:
    if err.response.status_code == 429:
      return "Retry in {} seconds".format(err.headers['Retry-After'])
    elif err.response.status_code == 404:
      print('No Tournaments Found')
    else:
        raise

def update_current_clashes(apiClashes):
  # Check if our currentClashes is up to date with Riot's
  for apiEvent in apiClashes:
    if apiEvent['id'] not in currentClashes:
      currentClashes.append(
        {
          'id': apiEvent['id'],
          'themeId': apiEvent['themeId'],
          'nameKey': apiEvent['nameKey'],
          'nameKeySecondary': apiEvent['nameKeySecondary'],
          'cancelled': apiEvent['schedule']['cancelled']
        }
      )

def update_past_clashes(apiClashes):
  for c in currentClashes:
    # If a clash id is in currentClashes but not Riot's apiClashses, move it to pastClashses

    # Horrible coding, but should work
    # For some reason, using range() gives an out of bounds exception
    if not any(d['id'] == c['id'] for d in apiClashes):
      pastClashes.append(currentClashes.pop(currentClashes.index(c)))

def update_clash_lists():
  apiClashes = get_tournaments()
 
  update_current_clashes(apiClashes)
  update_past_clashes(apiClashes)
  

@client.event
async def on_ready():
  print('We have logged in as {0.user}'.format(client))

@client.event
async def on_message(message):
  # If the bot sends a message don't analyze it
  if message.author == client.user:
    return

  msg = message.content

  if msg.startswith("$available") or msg.startswith("$a"):
    pass

  if msg.startswith("$tournaments") or msg.startswith("$t"):
    """Messages a parsed list of tournaments returned from Riots API"""

    # TODO: Parse JSON info into readable format and send to server
    # WTF is the riot time format
    print(get_tournaments())
    #await message.channel.send("Check Server.")


keep_alive()
client.run(os.environ['DTOKEN'])