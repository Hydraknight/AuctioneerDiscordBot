import discord
import os
import random
import copy
import asyncio
import random
import pytz
from datetime import datetime
import json
MAX_PURSE = 100
MAX_PLAYERS = 11
intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)

# Create dictionaries to store player names by type (lowercase)

teams = {}
full_team_names = {}
# Create a dictionary to store purse for each team
purse = {}

team_colors = {}
with open("auction_sets.json", "r") as players_file:
    auction_sets = json.load(players_file)
copy_auction_sets = copy.deepcopy(auction_sets)
# Load base prices from base_prices.json
with open("base_prices.json", "r") as base_prices_file:
    base_prices = json.load(base_prices_file)

# Load set colors from set_colors.json
with open("set_colors.json", "r") as set_colors_file:
    embed_colors = json.load(set_colors_file)


# Function to check if a user has the 'Auctioneer' role
def is_auctioneer(user):
  for role in user.roles:
    if role.name == 'Auctioneer':
      return True
  return False

# Initialize a dictionary to store sale history
sale_history = []
# Define a function to add a sale to the history
ist = pytz.timezone('Asia/Kolkata')

# Function to get the current IST time as a string
def get_current_ist_time():
    current_time = datetime.now(pytz.utc).astimezone(ist)
    return current_time.strftime("%Y-%m-%d %H:%M:%S IST")
def get_event_timestamp():
    return datetime.now(ist).strftime("%Y-%m-%d %H:%M:%S")
def add_sale(team_name, player_name, price):
    sale_history.append({'type':'sale','timestamp':get_event_timestamp(),'team_name': team_name, 'player_name': player_name, 'price': price})

def add_trade(team1_name, team2_name, player1_name, player2_name):
  sale_history.append({'type':'trade','timestamp':get_event_timestamp(),'team_1': team1_name, 'team_2': team2_name, 'player_1': player1_name, 'player_2': player2_name})
#############################################################
#Events:
#############################################################
@client.event
async def on_ready():
  print('We have logged in as {0.user}'.format(client))
#############################################################
#Message:
#############################################################
@client.event
async def on_message(message):
  if message.author == client.user:
    return

  content = message.content
  user = message.author

  if content.startswith('$'):
    cmd = content[1:]
    #Reset auction
    if cmd == 'reset' and is_auctioneer(user):
      await reset_sets_teams(message.channel)
    #Shows all sets
    elif cmd == 'sets':
      await show_sets(message.channel)
    #Pops a player
    elif cmd in auction_sets and is_auctioneer(user):
      await pop_and_send(cmd, message.channel)
    #Starts a timer
    elif cmd.startswith('timer '):
      cmd_args = cmd.split(' ')   
      await timer(cmd_args[1], message.channel)
    elif cmd == 'timer':
      await timer('10', message.channel)
    #Adds a new team
    elif cmd.startswith('add ') and is_auctioneer(user):
      cmd_args = cmd.split(' ')
      team_name = cmd_args[1]
      color_arg = cmd_args[2] if len(cmd_args) > 2 else None
      full_name = ' '.join(cmd_args[3:])
      await add_team(team_name,full_name, color_arg, message.channel)
    #Shows details of all teams
    elif cmd == 'teams':
      await show_teams(message.channel)
    #Sells the player to a team
    elif cmd.startswith('sell') and is_auctioneer(user):
      cmd_args = cmd.split(' ')
      team_name = cmd_args[1]
      price = cmd_args[2]
      name = ' '.join(cmd_args[3:])
      await sell_team(team_name, price, name, message.channel)
    #Shows specified team details
    elif cmd.lower() in str(teams.keys()).lower():
      await show_team(cmd, message.channel)
    #Shows Help embed
    elif cmd == 'help':
      await show_help(message.channel)
    #Shows specific set
    elif cmd.startswith('set '):
      cmd_args = cmd.split(' ')
      set_name = cmd_args[1]
      await show_set(set_name, message.channel)
    #Shows sales and trades that occurred
    elif cmd == 'sales':
      await show_sales(message.channel)
    #Sets Maximum purse for all teams
    elif cmd.startswith('setmaxpurse ') and is_auctioneer(user):
      cmd_args = cmd.split(' ')
      if len(cmd_args) == 2:
          await set_max_purse(cmd_args[1], message.channel)
      else:
          await message.channel.send("Invalid usage. Please use: $setmaxpurse <value>")
    #Trade
    elif cmd.startswith('trade ') and is_auctioneer(user):
      cmd_args = cmd.split(' ')  
      if len(cmd_args) < 5:
          # Invalid trade command, show an error message
          embed = discord.Embed(title="Invalid Trade Command", color=discord.Color.red())
          embed.add_field(name="Usage", value="$trade <team1> <team2> <player1> <player2>")
          await message.channel.send(embed=embed)
      else:
          team1_name = cmd_args[1]
          team2_name = cmd_args[2]
          players = ' '.join(cmd_args[3:])
          await trade(team1_name, team2_name, players, message.channel)
    elif cmd.startswith('setmaxplayers ') and is_auctioneer(user):
      cmd_args = cmd.split(' ')
      if len(cmd_args) == 2:  
          await set_max_players(cmd_args[1], message.channel)
      else:
          await message.channel.send("Invalid usage. Please use: $setmaxplayers <value>")
    # Remove player command
    elif cmd.startswith('removeplayer ') and is_auctioneer(user):
        cmd_args = cmd.split(' ')
        if len(cmd_args) == 3:
            team_name = cmd_args[1]
            player_name = cmd_args[2]
            await remove_player(team_name, player_name, message.channel)
        else:
            # Invalid usage of the removeplayer command
            embed = discord.Embed(
                title="Invalid Remove Player Command",
                description="Usage: $removeplayer <team_name> <player_name>",
                color=discord.Color.red()
            )
            await message.channel.send(embed=embed)

#############################################################
#Reset Sets:
#############################################################

async def reset_sets_teams(channel):
    global auction_sets
    global teams
    global purse
    global sale_history

    # Create an embed for the confirmation message
    confirmation_embed = discord.Embed(
        title="Reset Confirmation",
        description="WARNING: This action will reset all sets and teams.",
        color=discord.Color.orange()
    )
    confirmation_embed.add_field(name="Confirmation:", value="React with ✅ to confirm or ❌ to cancel..", inline=False)

    
    # Send the confirmation embed
    confirmation_message = await channel.send(embed=confirmation_embed)

    # Add reactions to the confirmation message
    await confirmation_message.add_reaction("✅")  # Check mark
    await confirmation_message.add_reaction("❌")  # X mark

    def check(reaction, user):
        return is_auctioneer(user) and str(reaction.emoji) in ["✅", "❌"]

    try:
        reaction, _ = await client.wait_for("reaction_add", check=check, timeout=30)

        if str(reaction.emoji) == "✅":
            # Reset all sets and teams
            auction_sets = copy.deepcopy(copy_auction_sets)
            teams = {}  # Reset teams
            purse = {}  # Reset purse
            sale_history = []
            # Create an embed for the success message
            success_embed = discord.Embed(
                title="Reset Successful",
                description="All sets and teams have been reset.",
                color=discord.Color.green()
            )
            await channel.send(embed=success_embed)
        else:
            # Create an embed for the cancellation message
            cancel_embed = discord.Embed(
                title="Reset Canceled",
                description="Reset operation canceled.",
                color=discord.Color.red()
            )
            await channel.send(embed=cancel_embed)

        await confirmation_message.delete()

    except asyncio.TimeoutError:
        # Create an embed for the timeout message
        timeout_embed = discord.Embed(
            title="Reset Timed Out",
            description="Reset operation timed out. No changes were made.",
            color=discord.Color.red()
        )
        await channel.send(embed=timeout_embed)
        await confirmation_message.delete()

#############################################################
#Show Sets:
#############################################################

async def show_sets(channel):
    embed = discord.Embed(title='Auction Sets', color=discord.Color.blue())

    for set_name, players in auction_sets.items():
        players_list = ', '.join(players)
        embed.add_field(name=f'{set_name.capitalize()}: {base_prices[set_name]}', value=players_list, inline=False)

    await channel.send(embed=embed)

#############################################################
#Show Set:
#############################################################

async def show_set(set_name, channel):
  players = auction_sets[set_name]
  players_message = f'Base Price: **{base_prices[set_name]}**\nRemaining players:\n\n'
  for player in players:
    players_message += f'**{player}**\n'
  color_value = embed_colors.get(set_name, "blue")
  if isinstance(color_value, str):
        color = discord.Color(value=int(color_value, base=16))
  else:
        color = discord.Color(value=color_value)

  embed = discord.Embed(title=f'{set_name.capitalize()}',
                          description=players_message,
                          color=color)
  await channel.send(embed=embed)
#############################################################
#Set Max Purse:
#############################################################
async def set_max_purse(new_max_purse, channel):
    global MAX_PURSE
    try:
        new_max_purse = float(new_max_purse)
        if new_max_purse >= 0:
            MAX_PURSE = new_max_purse
            embed = discord.Embed(
              title="Maximum Purse",
              description=f"The maximum purse has been set to {MAX_PURSE}Cr.",
              color=discord.Color.green()
          )
            await channel.send(embed=embed)
        else:
            embed = discord.Embed(
              title="Maximum Purse",
              description=f"Please provide a non-negative value.",
              color=discord.Color.red()
          )
            await channel.send(embed=embed)
    except ValueError:
        embed = discord.Embed(
              title="Maximum Purse",
              description=f"Invalid value for the maximum purse. Please provide a numeric value.",
              color=discord.Color.red()
          )
        await channel.send(embed=embed)

#############################################################
#Set Max Players:
#############################################################
async def set_max_players(new_max_players, channel):
    global MAX_PLAYERS
    try:
        new_max_players = int(new_max_players)
        if new_max_players >= 0:
            MAX_PLAYERS = new_max_players
            embed = discord.Embed(
              title="Maximum Players",
              description=f"The maximum players has been set to {MAX_PLAYERS}.",
              color=discord.Color.green()
          )
            await channel.send(embed=embed)
        else:
            embed = discord.Embed(
              title="Maximum Players",
              description=f"Please provide a non-negative value.",
              color=discord.Color.red()
          )
            await channel.send(embed=embed)
    except ValueError:
        embed = discord.Embed(
              title="Maximum Players",
              description=f"Invalid value for the maximum players. Please provide a numeric value.",
              color=discord.Color.red()
          )
        await channel.send(embed=embed)
#############################################################
#Timer:
#############################################################


async def timer(secs, channel):
    if secs is None:
        secs = 10
    else:
        secs = int(secs)
    
    def check_stop(reaction, user):
        return str(reaction.emoji) == "❌" and user != client.user and is_auctioneer(user)

    async def update_timer_message(embed, remaining_time):
        embed.description = f"Remaining time: {remaining_time}"
        await timer_message.edit(embed=embed)

    embed = discord.Embed(
        title="Timer",
        description=f"Remaining time: {secs}",
        color=discord.Color.blue()
    )
    timer_message = await channel.send(embed=embed)
    await timer_message.add_reaction("❌")
    for remaining_time in range(secs - 1, 0, -1):
        await asyncio.sleep(0.1)  # Wait for 1 second per interval
        await update_timer_message(embed, remaining_time)

        try:
            reaction, _ = await client.wait_for("reaction_add", check=check_stop, timeout=0.5)
            await timer_message.edit(embed=discord.Embed(
                title="Timer",
                description="Timer has been stopped!",
                color=discord.Color.red()
            ))
            return
        except asyncio.TimeoutError:
            pass

    await timer_message.edit(embed=discord.Embed(
        title="Timer",
        description="Time's up!",
        color=discord.Color.red()
    ))
    await channel.send(embed=discord.Embed(
        title="Timer",
        description="Time's up!",
        color=discord.Color.red()
    ))

        
#############################################################
#Pop Players:
#############################################################


async def pop_and_send(set_name, channel):
  if set_name in auction_sets:
    if auction_sets[set_name]:
      player = random.choice(auction_sets[set_name])
      auction_sets[set_name].remove(player)
      base_price = base_prices.get(set_name, 'Unknown')
      color_value = embed_colors.get(set_name, "blue")
      if isinstance(color_value, str):
        color = discord.Color(value=int(color_value, base=16))
      else:
        color = discord.Color(value=color_value)

      embed = discord.Embed(title=f"Player: {player}",
                            description=f'Base Price: {base_price}',
                            color=color)
      await channel.send(embed=embed)
    else:
      await channel.send(f'{set_name.capitalize()} is empty.')
  else:
    await channel.send(f'Invalid set name: {set_name.capitalize()}')


#############################################################
#Adding Teams:
#############################################################


async def add_team(team_name, full_team_name, color_arg, channel):
    if team_name not in teams:
        if not full_team_name:
            full_team_name = team_name
        teams[team_name] = {}  # Create a new team dictionary
        full_team_names[team_name] = full_team_name  # Store the full team name
        purse[team_name] = MAX_PURSE  # Assign a purse of 100 to the team

        # Store the team color in the team_colors dictionary
        if color_arg:
            try:
                color = discord.Color(int(color_arg, 16))  # Convert hex color code to Color object
                team_colors[team_name] = color
            except ValueError:
                pass  # Ignore invalid color codes

        # Create an embedded message to announce the team creation
        embed = discord.Embed(
            title=f'Team Created: {full_team_name}({team_name})',
            description=f'Team "{full_team_name}" has been created with a purse of {MAX_PURSE:.2f}Cr.',
            color=discord.Color.green()
        )

        # Optionally set the embed color based on the color argument
        if color_arg:
            embed.color = team_colors.get(team_name, discord.Color.green())

        await channel.send(embed=embed)
    else:
        # Create an embedded message to indicate that the team already exists
        embed = discord.Embed(
            title=f'Team Already Exists: {team_name}',
            description=f'Team {team_name} already exists as "{full_team_names[team_name]}".',
            color=discord.Color.red()
        )
        await channel.send(embed=embed)



#############################################################
#Showing Teams:
#############################################################
async def show_teams(channel):
  # Iterate through all existing teams and display their players and purses
  team_info = []

  for team_name, players in teams.items():
    purse_amount = purse.get(team_name, 0)
    players_list = ", ".join(players.keys()) if players else "None"

    # Get the stored team color or default to green
    color = team_colors.get(team_name, discord.Color.green())

    # Create an embedded message to display team information
    embed = discord.Embed(
        title=f'Team: {full_team_names[team_name]}',
        description=f'Purse: **{purse_amount:.2f}Cr**\nPlayers: {players_list}\n',
        color=color)

    team_info.append(embed)

  if team_info:
    for embed in team_info:
      await channel.send(embed=embed)
  else:
    await channel.send('No teams created yet.')


#############################################################
#Selling Players:
#############################################################
async def sell_team(team_name, price, name, channel):
  if team_name in teams:
    player_price = int(price)
    if len(teams[team_name]) >= MAX_PLAYERS:
            # Create an embedded message to indicate that the team has reached the player limit
            embed = discord.Embed(
                title=f'Team Player Limit Reached: {team_name}',
                description=f'Team {team_name} has reached the maximum player limit of {MAX_PLAYERS} players.',
                color=discord.Color.red()
            )
            await channel.send(embed=embed)
    else:
      if player_price/100 <= purse[team_name]:
        teams[team_name][name] = player_price
        purse[team_name] -= player_price/100
    
        add_sale(full_team_names[team_name], name, player_price/100)
        # Get the stored team color or default to green
        color = team_colors.get(team_name, discord.Color.green())
    
        # Create an embedded message to announce the player sale
        embed = discord.Embed(
            title=f'Player Sold: {name}',
            description=
            f'{name} has been sold to Team: {full_team_names[team_name]} for {player_price/100:.2f}Cr.',
            color=color)
        await channel.send(embed=embed)
      else:
        embed = discord.Embed(title=f'Team Over Budget!: {team_name}',
                              description=f'Team "{team_name}" has exceeded their maximum budget.',
                              color=discord.Color.red())
        await channel.send(embed=embed)
  else:
    # Create an embedded message to indicate that the team doesn't exist
    embed = discord.Embed(title=f'Team Not Found: {team_name}',
                          description=f'Team "{team_name}" does not exist.',
                          color=discord.Color.red())
    await channel.send(embed=embed)

##################################################################
#Removing Players:
##################################################################
async def remove_player(team_name, player_name, channel):
    if team_name in teams:
        if player_name in teams[team_name]:
            # Get the price of the player to refund the team's purse
            player_price = teams[team_name][player_name]
            purse[team_name] += player_price / 100

            # Remove the player from the team's roster
            del teams[team_name][player_name]
            for sale in sale_history:
                if sale["team_name"] == full_team_names[team_name] and sale["player_name"] == player_name:
                    sale_history.remove(sale)

            # Create an embedded message to announce the player removal
            embed = discord.Embed(
                title=f'Player Removed: {player_name}',
                description=f'{player_name} has been removed from Team: {full_team_names[team_name]}.',
                color=discord.Color.green()
            )
            await channel.send(embed=embed)
        else:
            # Create an embedded message to indicate that the player is not found in the team
            embed = discord.Embed(
                title=f'Player Not Found: {player_name}',
                description=f'{player_name} is not found in Team: {full_team_names[team_name]}.',
                color=discord.Color.red()
            )
            await channel.send(embed=embed)
    else:
        # Create an embedded message to indicate that the team doesn't exist
        embed = discord.Embed(
            title=f'Team Not Found: {team_name}',
            description=f'Team "{team_name}" does not exist.',
            color=discord.Color.red()
        )
        await channel.send(embed=embed)
  
##################################################################
#Showing Team:
##################################################################
async def show_team(team_name, channel):
    # Convert the provided team_name to lowercase to handle case-insensitive lookup
    team_name_lower = team_name.lower()

    if team_name_lower in map(str.lower, teams):
        # Find the original case team name based on the lowercase version
        original_team_name = next(key for key in teams if key.lower() == team_name_lower)

        players_info = []

        for player, price in teams[original_team_name].items():
            players_info.append(f'Player: **{player}**, Price: **{price/100}Cr**')

        purse_amount = purse.get(original_team_name, 0)
        full_team_name = full_team_names.get(original_team_name, original_team_name)

        if players_info:
            players_message = "\n".join(players_info)
        else:
            players_message = "No players bought by this team."

        embed = discord.Embed(
            title=f'Team: {full_team_name}',
            description=f'**Remaining Purse: {purse_amount}**\n\nPlayers:\n{players_message}',
            color=team_colors.get(original_team_name, discord.Color.green())
        )

        await channel.send(embed=embed)
    else:
        # Create an embedded message to indicate that the team doesn't exist
        embed = discord.Embed(
            title=f'Team Not Found: {team_name}',
            description=f'Team "{team_name}" does not exist.',
            color=discord.Color.red()
        )
        await channel.send(embed=embed)
##################################################################
#Sale History:
##################################################################
async def show_sales(channel):
    if sale_history:
        # Sort the sale history by timestamp
        sorted_history = sorted(sale_history, key=lambda x: x['timestamp'])

        history_message = ""
        for entry in sorted_history:
            timestamp = entry["timestamp"]
            if entry["type"] == "sale":
                history_message += f'[{timestamp} IST] **{entry["player_name"]}** sold to **{entry["team_name"]}** for **{entry["price"]}Cr**\n'
            elif entry["type"] == "trade":
                history_message += f'[{timestamp} IST] **{entry["team_1"]}** traded **{entry["player_1"]}** to **{entry["team_2"]}** for **{entry["player_2"]}**\n'

    # Create an embedded message to display the combined sales message
        embed = discord.Embed(
            title='Sales and Trade History',
            description=history_message,
            color=discord.Color.blue()
      )
    else:
      embed = discord.Embed(
            title='Sales and Trade History',
            description='No sales or trades have been made yet.',
            color=discord.Color.blue()
        )
  
    await channel.send(embed=embed)
##################################################################
#Trade:
##################################################################
async def trade(team1_name, team2_name, players, channel):
    # Split the players argument into two player names using a delimiter ("/")
    player_names = players.split('/')
    if len(player_names) != 2:
        embed = discord.Embed(title="Invalid Trade Command", color=discord.Color.red())
        embed.add_field(name="Usage", value="$trade <team1> <team2> <player1> / <player2>")
        await channel.send(embed=embed)
        return

    player1_name = player_names[0].strip()
    player2_name = player_names[1].strip()
    # Check if both teams exist
    if team1_name not in teams or team2_name not in teams:
        embed = discord.Embed(title="Trade Failed", color=discord.Color.red())
        embed.add_field(name="Error", value="One or both of the teams do not exist.")
        await channel.send(embed=embed)
        return

    # Check if both players exist in their respective teams
    if player1_name not in teams[team1_name] or player2_name not in teams[team2_name]:
        embed = discord.Embed(title="Trade Failed", color=discord.Color.red())
        embed.add_field(name="Error", value="One or both of the players do not exist in their respective teams.")
        await channel.send(embed=embed)
        return

    # Calculate the values of the players
    player1_value = teams[team1_name][player1_name]
    player2_value = teams[team2_name][player2_name]

    # Check if both teams can afford the trade
    if (purse[team1_name] + player1_value/100 - player2_value/100 < 0) or (purse[team2_name] + player2_value/100 - player1_value/100 < 0):
        embed = discord.Embed(title="Trade Failed", color=discord.Color.red())
        embed.add_field(name="Error", value="One or both teams cannot afford this trade.")
        await channel.send(embed=embed)
        return

    # Perform the trade
    del teams[team1_name][player1_name]
    del teams[team2_name][player2_name]

    teams[team1_name][player2_name] = player2_value
    teams[team2_name][player1_name] = player1_value

    # Update purse balances
    purse[team1_name] = purse[team1_name] + player1_value/100 - player2_value/100
    purse[team2_name] = purse[team2_name] + player2_value/100 - player1_value/100

    # Log the trade
    add_trade(full_team_names[team1_name], full_team_names[team2_name], player1_name, player2_name)

    # Send a trade success embed
    embed = discord.Embed(title="Trade Successful", color=discord.Color.green())
    embed.add_field(name=f"Trade Details", value=f"{player1_name} from {team1_name} traded for {player2_name} from {team2_name}.")
    await channel.send(embed=embed)

##################################################################
#Showing Help:
##################################################################
async def show_help(channel):
  embed = discord.Embed(
      title='Help',
      description='Here are the available commands:',
      color=discord.Color.blue())
  embed.add_field(name='$add <shorthand> <color> <team_name> (Auctioneer Only)', value='Creates a new team with the given name.', inline=False)
  embed.add_field(name='$sell <team> <price> <player> (Auctioneer Only)', value='Sells a player to a team.', inline=False)
  embed.add_field(name='$<set_name> (Auctioneer Only)', value='Displays a random player from the set.', inline=False)
  embed.add_field(name='$removeplayer <team> <player> (Auctioneer Only)', value='Removes a player from a team.', inline=False)
  embed.add_field(name='$reset (Auctioneer only)', value='Resets all the sets.' , inline=False)
  embed.add_field(name='$setmaxpurse <value> (Auctioneer Only)', value='Sets the maximum purse value.', inline=False)
  embed.add_field(name='$trade <team1> <team2> <player1>/<player2> (Auctioneer Only)' , value='Trades a player from one team to another.', inline=False)
  embed.add_field(name='$setmaxplayers <value>', value='Sets the maximum players value.', inline=False)
  embed.add_field(name='$teams', value='Shows all the teams.', inline=False)
  embed.add_field(name='$<team>', value='Shows information about a team.',inline=False)
  embed.add_field(name='$help', value='Shows this help message.', inline=False)
  embed.add_field(name='$sets', value='Shows all the sets.', inline=False)
  embed.add_field(name='$set <set_name>', value='Shows the set with the given name.', inline=False)
  embed.add_field(name='$timer <value>', value='Sets a timer for entered seconds. 10 seconds if no input.', inline=False)
  embed.add_field(name='$sales', value='Shows the history of sales and trades.', inline=False)
  
  
  await channel.send(embed=embed)

client.run('MTE1MDA1MTcyMDkwNzQ3MzAyNg.GOap1v.-alulLKYbOwDz-JGce8gFnQmboZ1kAjAIsTpXA')