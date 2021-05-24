import discord
import os
import requests
import json
from replit import db
from keep_alive import keep_alive
from replit import db

client = discord.Client()

from riotwatcher import LolWatcher, ApiError

lolWatcher = LolWatcher(os.environ['RTOKEN'])
defaultServer = 'euw1'
# Docs:
### https://developer.riotgames.com/apis
### https://discord.com/developers/docs/intro
### https://discordpy.readthedocs.io/en/stable/api.html
#
# The 429 status code indicates that the user has sent too many requests
# in a given amount of time ("rate limiting").

print(db.keys())


def linear_search(arr, key, val):
    """Perform a search over arr for a given key, value pair"""
    # Small server so linear search is fine
    for i in range(len(arr)):
        if arr[i][key] == val:
            return i
    return -1

def appendToDB(key, val):
    temp = db[key]
    temp.append(val)
    db[key] = temp
    
def owner_authorized(discordTag):
    """Return true if a given discordTag is in botOwners I.E. has owner permissions"""
    #if discordTag in db["botOwners"]:
    #    return True
    #return False
    return True

def add_owner(discordTag):
    """Add given discordTag to bot Owners"""
    if "botOwners" in db.keys():
        if discordTag not in db["botOwners"]:
            appendToDB("botOwners", discordTag)
        else:  
            return "Already an owner."
    else:
        db["botOwners"] = [discordTag]
    return "Successfully added " + discordTag[:-5] +  "'s owner status."
    
def admin_authorized(discordTag):
    """Return true if a given discordTag is in botAdmins I.E. has admin permissions"""
    #if discordTag in db["botAdmins"]:
    #    return True
    #return False
    return True

def add_admin(discordTag):
    if "botAdmins" in db.keys():
        if discordTag not in db["botAdmins"]:
            appendToDB("botAdmins", discordTag)
        else:
            return "Already an admin."
    else:
        db["botAdmins"] = [discordTag]
    
    return "Successfully added " + discordTag[:-5] +  " as an admin."

def remove_admin(discordTag):
    """Remove the given discordTag from the admins list"""
    if "botAdmins" in db.keys():
        if discordTag in db["botAdmins"]:
            temp = db["botAdmins"]
            temp.remove(discordTag)
            db["botAdmins"] = temp
            return "Successfully removed " + discordTag[:-5] +  "'s admin status."
        return "Can't find an admin by that name"
    else:
        return "No admins, add some first"

def player_toString(index):
    """Return a string representation of some key player facts"""
    p = db["players"][index]
    outString = p['discordTag'] + " goes by " + p['summonerName']
    winRate = 0
    # Avoiding division by 0 
    if p['clashGames'] == 0:
        winRate = -1
        #outString = players[index]['discordTag'] + " goes by " + players[index]['summonerName'] + " and has not played any games yet."
    else:
        winRate = round(100 * p['clashWins']/p['clashGames'], 2)
        #outString = p['discordTag'] + " goes by " + p['summonerName'] + " and has a " + winRate + "% win rate accross " + p['clashGames'] " games.".
    return outString

def register_player(summonerName, discordTag):
    print(discordTag)
    """Register a new player with given summoner name and discord tag"""
    player = {
            'discordTag': discordTag,
            'summonerName': summonerName,
            'server': defaultServer,
            'clashHistory': [], # List of indexes in pastClashes
            'clashWins': 0, # Total games won in clash  (will be used for team balancing feature)
            'clashGames': 0
            }
    print(db.keys())
    if "players" in db.keys():
        newID = len(db["players"]) + 1
        player[id] = newID
        if linear_search(db["players"], 'discordTag', discordTag) == -1: 
            appendToDB("players", player)
        else:
            return "Player already exists."
    else:
        player['id'] = 0
        db["players"] = [player]
    return "Successfully registered " + discordTag[:-5] +  " as a player."
        
def remove_player(summonerName):
    """Remove a player from the players list"""
    if "players" in db.keys():
        loc = linear_search(db["players"], 'summonerName', summonerName)
        if loc == -1:
            return "Cant find a player with that summoner name"
        temp = db["players"]
        temp.pop(loc)
        db["players"] = temp
        return "Successfully removed " + summonerName +  " from the players list"
    else:
        return "No players, try adding some first."

def print_player(name):
    """Search for a player by name and return a string describing their profile or -1 if not found"""
    locDiscord = linear_search(db["players"], 'discordTag', name)
    if locDiscord != -1:
        return player_toString(locDiscord)
    locSummoner = linear_search(db["players"], 'summonerName', name)
    if locSummoner != -1:
        return player_toString(locSummoner)  
    return "Player not found"

def get_tournaments():
    """Retrieve a list of tournaments from Riot's API"""
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
    """Compare Riot's list of current clashes to ours and update accordingly"""
    # Check if our currentClashes is up to date with Riot's
    for apiEvent in apiClashes:
        if apiEvent['id'] not in db["currentClashes"]:
            db["currentClashes"].append(
            {
                'id': apiEvent['id'],
                'themeId': apiEvent['themeId'],
                'nameKey': apiEvent['nameKey'],
                'nameKeySecondary': apiEvent['nameKeySecondary'],
                'cancelled': apiEvent['schedule']['cancelled']
            }
        )

def update_past_clashes(apiClashes):
    """Moves all old tournaments from currentClashes to pastClashes"""
    for c in db["currentClashes"]:
    # If a clash id is in currentClashes but not Riot's apiClashses, move it to pastClashes

    # Horrible coding, but should work
    # For some reason, using range() gives an out of bounds exception
        if not any(d['id'] == c['id'] for d in apiClashes):
            db["pastClashes"].append(db["currentClashes"].pop(db["currentClashes"].index(c)))

def update_clash_lists():
    """Checks the Riot API for new tournaments, adds them accordingly and moves old ones"""
    apiClashes = get_tournaments()
    update_current_clashes(apiClashes)
    update_past_clashes(apiClashes)

def send_incorrect_format(format):
    # Based on format param, return a string of correct format
    # Using a map of some kind to map format param to format actual
    pass

def not_authorized(authority):
    return "You are not authorized to do that. Please contact an {} if you think you should be.".format(authority)
    
@client.event
async def on_ready():
    print('We have logged in as {0.user}'.format(client))

@client.event
async def on_message(message):

    #print(db["players"])
    if message.author == client.user:
        # If the bot sends a message don't analyze it
        return

    msg = message.content
    msgDetails = msg.split()

    if msg.startswith("$available"):
        # Indicate you are available for a clash
        print("help")

    if msg.startswith("$tournaments") or msg.startswith("$t"):
        # Prints a parsed list of tournaments returned from Riots API
        print(message.author)
        # TODO: Parse JSON info into readable format and send to server
        # WTF is the riot time format
        print(get_tournaments())

    if msg.startswith("$register"):
        # Register a new player with a summonerName 
        # TODO: Link with discords league intergration, loop through server and autoadd
        # $register summonerName
        summonerName = msgDetails[1]
        discordTag = message.author
        if len(msgDetails) == 2:
            # Adds a new player
            await message.channel.send(register_player(summonerName, discordTag))
        else:
            await message.channel.send("Please use the following format: '$register summonerName'")

    if msg.startswith("$remove"):
        # Remove a player from the players list. Requires admin permissions to remove a player other than yourself
        # $remove summonerName
        # $remove me
        if len(msgDetails) == 2:
            nameToRemove = msgDetails[1]
            if nameToRemove == 'me':
                nameToRemove = message.author
            if admin_authorized(message.author) or nameToRemove == message.author:
                await message.channel.send(remove_player(nameToRemove))
            else:
                await message.channel.send(not_authorized('admin'))
        else:
            await message.channel.send("Please use the following format: '$remove summonerName'")

    if msg.startswith("$admin"):
        # Grants a specified user admin
        # $admin discordTag
        if len(msgDetails) == 2:
            if len(message.mentions != 0):
                discordTag = message.mentions[0].name
            else:
                discordTag = msgDetails[1]
            if admin_authorized(message.author):
                
                await message.channel.send(add_admin(discordTag))
            else:
                await message.channel.send(not_authorized('admin'))
        else:
            await message.channel.send("Please use the following format: '$admin discordTag'")
            
    if msg.startswith("$de-admin"):
        # Removes admin from a specified discord user
        # de-admin discordTag
        # de-admin me
        if len(msgDetails) == 2:
            if len(message.mentions != 0):
                discordTag = message.mentions[0].name
            else:
                discordTag = msgDetails[1]
            if discordTag == 'me':
                discordTag = message.author
            if owner_authorized(message.author):
                
                await message.channel.send(remove_admin(discordTag.name))
            else:
                await message.channel.send(not_authorized('owner'))  
        else:
            await message.channel.send("Please use the following format: '$de-admin discordTag'")
            
    if msg.startswith("$player"):
        # Prints info about a player on the discord server
        # $player me
        # $player discordTag
        # $player summonerName
        nameToSearchFor = msgDetails[1]
        if nameToSearchFor == "me":
            nameToSearchFor = message.author.name
        await message.channel.send(print_player(nameToSearchFor))
    
    if msg.startswith("$summoner"):
        # $summoner summonerName
        pass
    
    if msg.startswith("$owner"):
        if len(msgDetails) == 2:
            if len(message.mentions) != 0:
                discordTag = message.mentions[0].name + str(message.mentions[0].id)
            else:   
                discordTag = msgDetails[1]
            if owner_authorized(message.author):
                await message.channel.send(add_owner(discordTag))
                
            else:
                await message.channel.send(not_authorized('owner')) 
        else:
            await message.channel.send("Please use the following format: '$owner discordTag'")
                           
keep_alive()
client.run(os.environ['DTOKEN'])