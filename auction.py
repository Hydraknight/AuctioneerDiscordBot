import discord
from discord.ui import Button, View
from discord import InteractionType
import os
import random
import copy
import asyncio
import random
import pytz
from datetime import datetime
import json
import pickle
from keep_alive import keep_alive
import csv

keep_alive()
timer_running = False
counter = 0
sales_channel = None
user_notifications = {}
# iterate through files to find highest numbered .pkl file
pkls = []
for files in os.listdir():
    if files.endswith(".pkl"):
        file = files.removesuffix(".pkl")
        file = files.removeprefix("data_")
        pkls.append(file)
print(pkls)
if len(pkls) != 0:
    filename = str(max(pkls))
    filename = "data_"+filename
else:
    filename = None


def load_data(filename):
    try:
        with open(filename, 'rb') as file:
            data = pickle.load(file)
        return data
    except FileNotFoundError:
        # Handle the case where the file doesn't exist (e.g., for the first run)
        return None
    except Exception as e:
        # Handle other exceptions, e.g., if the file format is invalid
        print(f"Error loading data: {e}")
        return None

# Function to save all relevant data to a pickle file


def save_data(data_to_save):
    global counter
    try:
        # Increment the counter for the next file name
        counter += 1
        file_name = f'data_{counter}.pkl'

        # Save the data to the pickle file
        with open(file_name, 'wb') as file:
            pickle.dump(data_to_save, file)
        for i in range(1, counter-1):
            file = f'data_{i}.pkl'
            if os.path.exists(file):
                os.remove(file)
                print(f"Deleted {file}.")
        print(f"Data saved to {file_name} successfully.")
    except Exception as e:
        print(f"Error saving data: {e}")


MAX_PURSE = 100
MAX_PLAYERS = 25
current_auction_set = None
current_player = None
current_player_price = None
unsold_players = set()
intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)
teams = {}
full_team_names = {}
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
    sale_history.append({
        'type': 'sale',
        'timestamp': get_event_timestamp(),
        'team_name': team_name,
        'player_name': player_name,
        'price': price
    })


def add_trade(team1_name, team2_name, player1_name, player2_name):
    sale_history.append({
        'type': 'trade',
        'timestamp': get_event_timestamp(),
        'team_1': team1_name,
        'team_2': team2_name,
        'player_1': player1_name,
        'player_2': player2_name
    })


auction_data = {
    'teams': teams,
    'purse': purse,
    'auction_sets': auction_sets,
    'sale_history': sale_history,
    'unsold_players': unsold_players,
    'full_team_names': full_team_names,
    'team_colors': team_colors,
    'current_auction_set': current_auction_set,
    'current_player': current_player,
    'current_player_price': current_player_price,
}
#############################################################
# Events:
#############################################################


@client.event
async def on_ready():
    global teams, purse, auction_sets, sale_history, unsold_players, full_team_names, team_colors, user_notifications, current_player_price, current_player, current_auction_set, filename, pkls
    print('We have logged in as {0.user}'.format(client))
    # Load data from the pickle file at the start of the bot
    if pkls != []:
        loaded_data = load_data(filename)
    else:
        loaded_data = None
    for files in os.listdir():
        if files.endswith(".pkl"):
            os.remove(files)
    if loaded_data is not None:
        # Extract individual components as needed
        teams = loaded_data.get('teams', {})
        purse = loaded_data.get('purse', {})
        auction_sets = loaded_data.get('auction_sets', auction_sets)
        sale_history = loaded_data.get('sale_history', [])
        unsold_players = loaded_data.get('unsold_players', set())
        full_team_names = loaded_data.get('full_team_names', {})
        team_colors = loaded_data.get('team_colors', team_colors)
        current_player_price = loaded_data.get('current_player_price', None)
        current_player = loaded_data.get('current_player', None)
        current_auction_set = loaded_data.get('current_auction_set', None)
        user_notifications = loaded_data.get('user_notifications', {})
        # Extract more data as needed
    else:
        # Handle the case where no data was loaded (e.g., first run)
        # Initialize data structures as needed
        teams = {}
        purse = {}
        auction_sets = copy.deepcopy(copy_auction_sets)
        full_team_names = {}
        sale_history = []
        unsold_players = set()
        team_colors = {}
        current_auction_set = None
        current_player = None
        current_player_price = None
        user_notifications = {}

#############################################################
# Message:
#############################################################


@client.event
async def on_message(message):
    global current_auction_set
    global current_player
    global sales_channel
    if message.author == client.user:
        return

    content = message.content
    user = message.author
    if content.startswith('$'):
        try:
            cmd = content[1:]
            # Reset auction
            if cmd == 'ping':
                # calculate ping time
                ping = round(client.latency * 1000)
                await message.channel.send('Pong! {}ms'.format(ping))
            if cmd == 'reset' and is_auctioneer(user):
                await reset_sets_teams(message.channel)
            # Shows all sets
            elif cmd == 'sets':
                await show_sets(message.channel)
            # Pops a player
            elif cmd in auction_sets and is_auctioneer(user):
                await pop_and_send(cmd, message.channel)
            # Starts a timer
            elif cmd.startswith('timer '):
                cmd_args = cmd.split(' ')
                await timer(cmd_args[1], message.channel)
            elif cmd == 'timer':
                await timer('10', message.channel)
            # Adds a new team
            elif cmd.startswith('add ') and is_auctioneer(user):
                cmd_args = cmd.split(' ')
                team_name = cmd_args[1]
                color_arg = cmd_args[2] if len(cmd_args) > 2 else None
                full_name = ' '.join(cmd_args[3:])
                await add_team(team_name, full_name, color_arg, message.channel)
            # Shows details of all teams
            elif cmd == 'teams':
                await show_teams(message.channel)
            # Sells the player to a team
            elif cmd.startswith('sell') and is_auctioneer(user):
                cmd_args = cmd.split(' ')
                team_name = cmd_args[1]
                price = cmd_args[2]
                name = ' '.join(cmd_args[3:])
                await sell_team(team_name, price, name, message.channel)
            # Shows specified team details
            elif cmd.lower() in str(teams.keys()).lower():
                await show_team(cmd, message.channel)
            # Shows Help embed
            elif cmd == 'help':
                await show_help(message.channel)
            # Shows specific set
            elif cmd.startswith('set '):
                cmd_args = cmd.split(' ')
                set_name = cmd_args[1]
                await show_set(set_name, message.channel)
            # Shows sales and trades that occurred
            elif cmd == 'sales':
                await show_sales(message.channel)
            # Sets Maximum purse for all teams
            elif cmd.startswith('setmaxpurse ') and is_auctioneer(user):
                cmd_args = cmd.split(' ')
                if len(cmd_args) == 2:
                    await set_max_purse(cmd_args[1], message.channel)
                else:
                    await message.channel.send(
                        "Invalid usage. Please use: $setmaxpurse <value>")
            # Trade
            elif cmd.startswith('trade ') and is_auctioneer(user):
                cmd_args = cmd.split(' ')
                if len(cmd_args) < 5:
                    # Invalid trade command, show an error message
                    embed = discord.Embed(title="Invalid Trade Command",
                                          color=discord.Color.red())
                    embed.add_field(name="Usage",
                                    value="$trade <team1> <team2> <player1> <player2>")
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
                    await message.channel.send(
                        "Invalid usage. Please use: $setmaxplayers <value>")
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
                        color=discord.Color.red())
                    await message.channel.send(embed=embed)
            # Selling current player
            elif cmd.startswith('sold ') and is_auctioneer(user):
                global current_auction_set
                global current_player
                cmd_args = content.split(' ')
                team = cmd_args[1]
                price = cmd_args[2]
                if current_player is not None:
                    await sell_team(team, price, current_player, message.channel)
                else:
                    await message.channel.send(
                        "No player available to sell. Use $<set_name> to pop a player first."
                    )
            # Requesting a player
            elif cmd.startswith('request '):
                cmd_args = cmd.split(' ')
                if len(cmd_args) > 1:
                    requested_player = ' '.join(cmd_args[1:])
                    await request_player(user, requested_player, message.channel)
                else:
                    await message.channel.send(
                        "Invalid usage. Please use: $request <player_name>")
            # Marking current player as unsold
            elif cmd == 'unsold' and is_auctioneer(user):
                await unsold(message.channel)
            # Getting a random unsold player
            elif cmd == 'getunsold' and is_auctioneer(user):
                await get_unsold(message.channel)
            # Showing unsold players
            elif cmd == 'showunsold':
                await show_unsold(message.channel)
            # Set the sales channel
            elif cmd.startswith('saleschannel') and is_auctioneer(user):
                args = cmd.split(' ')
                if len(args) == 2:
                    channel_id = int(args[1])
                    channel = client.get_channel(channel_id)
                    if channel is not None:
                        sales_channel = channel
                        await message.channel.send(f"Sales channel set to {sales_channel}")
                    else:
                        await message.channel.send("Invalid channel ID.")
            # Remove a team
            elif cmd.startswith('removeteam') and is_auctioneer(user):
                args = cmd.split(' ')
                if len(args) == 2:
                    team_name = args[1]
                    await remove_team(team_name, message.channel)
                else:
                    await message.channel.send("Invalid usage. Please use: $removeteam <team_name>")
            # Export
            elif cmd == 'export' and is_auctioneer(user):
                await export(message.channel)
            elif cmd.startswith('notify '):
                cmd_args = cmd.split(' ')
                players_to_notify = ' '.join(cmd_args[1:]).split(',')
                players_to_notify = [player.strip()
                                     for player in players_to_notify]
                user_notifications[user.id] = players_to_notify
                await message.author.send(
                    f"You will be notified when these players are live in auction: {', '.join(players_to_notify)}"
                )

            save_data({
                'teams': teams,
                'purse': purse,
                'auction_sets': auction_sets,
                'sale_history': sale_history,
                'unsold_players': unsold_players,
                'full_team_names': full_team_names,
                'team_colors': team_colors,
                'current_auction_set': current_auction_set,
                'current_player': current_player,
                'current_player_price': current_player_price,
                'user_notifications': user_notifications
            })
            await message.delete()
        except Exception as e:
            print(e)
            save_data({'teams': teams,
                       'purse': purse,
                       'auction_sets': auction_sets,
                       'sale_history': sale_history,
                       'unsold_players': unsold_players,
                       'full_team_names': full_team_names,
                       'team_colors': team_colors,
                       'current_auction_set': current_auction_set,
                       'current_player': current_player,
                       'current_player_price': current_player_price,
                       'user_notifications': user_notifications})

#############################################################
# Reset:
#############################################################


async def reset_sets_teams(channel):

    # Create an embed for the confirmation message
    confirmation_embed = discord.Embed(
        title="Reset Confirmation",
        description="WARNING: This action will reset all sets and teams.",
        color=discord.Color.from_str("#FFFFFF"))
    confirmation_embed.add_field(
        name="Confirmation:", value="Are you sure you want to reset all sets and teams?")

    # Send the confirmation embed
    confirmation_message = await channel.send(embed=confirmation_embed)
    confirm = Button(style=discord.ButtonStyle.green, label="Confirm")
    cancel = Button(style=discord.ButtonStyle.red, label="Cancel")
    view = View()
    view.add_item(confirm)
    view.add_item(cancel)
    await confirmation_message.edit(view=view)
    # Add reactions to the confirmation message

    def check_stop(interaction):
        return is_auctioneer(interaction.user) and interaction.message == confirmation_message

    # Define a check function to check which button they clicked
    async def confirmed(interaction):
        global teams, purse, auction_sets, sale_history, unsold_players, full_team_names, team_colors, user_notifications, current_player_price, current_player, current_auction_set, filename, pkls
        if interaction.message == confirmation_message and is_auctioneer(interaction.user):
            teams = {}
            purse = {}
            auction_sets = copy.deepcopy(copy_auction_sets)
            full_team_names = {}
            sale_history = []
            unsold_players = set()
            team_colors = {}
            current_auction_set = None
            current_player = None
            current_player_price = None
            user_notifications = {}
            save_data(auction_data)

            success_embed = discord.Embed(
                title="Reset Successful",
                description="All sets and teams have been reset.",
                color=discord.Color.green())
            await channel.send(embed=success_embed)
            await confirmation_message.delete()
        return

    async def cancel_check(interaction):
        if interaction.message == confirmation_message and is_auctioneer(interaction.user):
            cancel_embed = discord.Embed(title="Reset Canceled",
                                         description="Reset operation canceled.",
                                         color=discord.Color.red())
            await channel.send(embed=cancel_embed)
            await confirmation_message.delete()
        return

    confirm.callback = confirmed
    cancel.callback = cancel_check


#############################################################
# Show Sets:
#############################################################


async def show_sets(channel):
    embed = discord.Embed(title='Auction Sets', color=discord.Color.blue())

    for set_name, players in auction_sets.items():
        players_list = ', '.join(players)
        embed.add_field(name=f'{set_name.capitalize()}: {base_prices[set_name]}',
                        value=players_list,
                        inline=False)

    await channel.send(embed=embed)


#############################################################
# Show Set:
#############################################################


async def show_set(set_name, channel):
    players = auction_sets[set_name]
    players_message = f'Base Price: **{base_prices[set_name]}**\nRemaining players:\n\n'
    for player in players:
        players_message += f'**{player}**\n'
    color_value = embed_colors.get(set_name, "blue")
    if isinstance(color_value, str):
        color = discord.Color.from_str(color_value)
    else:
        color = discord.Color(value=color_value)

    embed = discord.Embed(title=f'{set_name.capitalize()}',
                          description=players_message,
                          color=color)
    await channel.send(embed=embed)


#############################################################
# Set Max Purse:
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
                color=discord.Color.green())
            await channel.send(embed=embed)
        else:
            embed = discord.Embed(
                title="Maximum Purse",
                description=f"Please provide a non-negative value.",
                color=discord.Color.red())
            await channel.send(embed=embed)
    except ValueError:
        embed = discord.Embed(
            title="Maximum Purse",
            description=f"Invalid value for the maximum purse. Please provide a numeric value.",
            color=discord.Color.red())
        await channel.send(embed=embed)


#############################################################
# Set Max Players:
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
                color=discord.Color.green())
            await channel.send(embed=embed)
        else:
            embed = discord.Embed(
                title="Maximum Players",
                description=f"Please provide a non-negative value.",
                color=discord.Color.red())
            await channel.send(embed=embed)
    except ValueError:
        embed = discord.Embed(
            title="Maximum Players",
            description=f"Invalid value for the maximum players. Please provide a numeric value.",
            color=discord.Color.red())
        await channel.send(embed=embed)


#############################################################
# Timer:
#############################################################
async def deny_timer(channel):
    global timer_running

    if timer_running:
        embed = discord.Embed(
            title="Timer Already Running",
            description="A timer is currently running. You cannot start a new timer until the current one finishes.",
            color=discord.Color.red())
        msg = await channel.send(embed=embed)
        await asyncio.sleep(2)
        await msg.delete()
        return True  # Return True to indicate denial
    else:
        return False  # Return False to indicate permission


async def timer(secs, channel):
    global timer_running
    if await deny_timer(channel):
        return
    if secs is None:
        secs = 10
    else:
        secs = int(secs)

    if secs > 30 or secs < 1:
        embed = discord.Embed(
            title="Timer",
            description=f"Timer cannot be set for more than 30 seconds and less than 1 second.",
            color=discord.Color.red())
        await channel.send(embed=embed)
        return
    timer_running = True

    def check_stop(interaction):
        return is_auctioneer(interaction.user) and interaction.message == timer_message

    async def update_timer_message(embed, remaining_time):
        embed.description = f"Remaining time: {remaining_time}"
        await timer_message.edit(embed=embed)

    embed = discord.Embed(title="Timer",
                          description=f"Remaining time: {secs}",
                          color=discord.Color.blue())
    timer_message = await channel.send(embed=embed)
    view = View()
    stop_button = Button(style=discord.ButtonStyle.danger, label="Stop")
    view.add_item(stop_button)

    # Set the initial value of the flag
    timer_stopped = False

    async def on_button_click(interaction):
        nonlocal timer_stopped
        global timer_running
        if check_stop(interaction):
            timer_stopped = True
            timer_running = False

    # Set the button callback
    stop_button.callback = on_button_click

    await timer_message.edit(view=view)

    for remaining_time in range(secs - 1, 0, -1):
        await asyncio.sleep(0.5)  # Wait for 1 second per interval
        await update_timer_message(embed, remaining_time)

        # Check if the timer should be stopped
        if timer_stopped:
            await timer_message.edit(
                embed=discord.Embed(
                    title="Timer",
                    description="Timer has been stopped!",
                    color=discord.Color.red()),
                view=None)
            timer_running = False
            return

    await timer_message.edit(embed=discord.Embed(
        title="Timer", description="Time's up!", color=discord.Color.red()), view=None)
    embed = discord.Embed(title="Timer",
                          description="Time's up!",
                          color=discord.Color.red())
    embed.set_thumbnail(
        url="https://cdn.discordapp.com/emojis/880003196339236884.png")
    timer_running = False
    await channel.send(embed=embed)
#############################################################
# Pop Players:
#############################################################


async def pop_and_send(set_name, channel):
    global teams, purse, auction_sets, sale_history, unsold_players, full_team_names, team_colors, current_player_price, current_player, current_auction_set

    if current_player is not None:
        await complete_sale(channel)
        return None

    if set_name in auction_sets:
        if auction_sets[set_name]:
            player = random.choice(auction_sets[set_name])
            auction_sets[set_name].remove(player)
            current_auction_set = set_name
            base_price = base_prices.get(set_name, 'Unknown')
            current_player_price = base_price
            color_value = embed_colors.get(set_name, "blue")
            if isinstance(color_value, str):
                color = discord.Color.from_str(color_value)
            else:
                color = discord.Color(value=color_value)

            embed = discord.Embed(title=f"Player: {player}",
                                  description=f'Base Price: {base_price}',
                                  color=color)
            player_image_file = f'images/{player}.png'
            if os.path.isfile(player_image_file):
                player_image = discord.File(
                    player_image_file, filename='Player.png')
                embed.set_image(url="attachment://Player.png")
                await channel.send(file=player_image, embed=embed)
            else:
                await channel.send(embed=embed)
            current_player = player
            # Send a DM to users who signed up for notifications
            for user_id, players_to_notify in user_notifications.items():
                if player in players_to_notify:
                    user = await client.fetch_user(user_id)
                    if user:
                        await user.send(f"**{player}** is live in the auction!")
        else:
            await channel.send(f'{set_name.capitalize()} is empty.')
    else:
        await channel.send(f'Invalid set name: {set_name.capitalize()}')
    return None


#############################################################
# Adding Teams:
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
                color = discord.Color(int(
                    color_arg, 16))  # Convert hex color code to Color object
                team_colors[team_name] = color
            except ValueError:
                pass  # Ignore invalid color codes

        # Create an embedded message to announce the team creation
        embed = discord.Embed(
            title=f'Team Created: {full_team_name}({team_name})',
            description=f'Team "{full_team_name}" has been created with a purse of {MAX_PURSE:.2f}Cr.',
            color=discord.Color.green())

        # Optionally set the embed color based on the color argument
        if color_arg:
            embed.color = team_colors.get(team_name, discord.Color.green())

        await channel.send(embed=embed)
    else:
        # Create an embedded message to indicate that the team already exists
        embed = discord.Embed(
            title=f'Team Already Exists: {team_name}',
            description=f'Team {team_name} already exists as "{full_team_names[team_name]}".',
            color=discord.Color.red())
        await channel.send(embed=embed)


#############################################################
# Showing Teams:
#############################################################
async def show_teams(channel):
    # Iterate through all existing teams and display their players and purses
    team_info = []
    team_logo = []

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

        team_image_file = f'teams/{team_name}.png'
        if os.path.isfile(team_image_file):
            team_image = discord.File(
                team_image_file, filename='Team.png')
            embed.set_thumbnail(
                url="attachment://Team.png")
            await channel.send(file=team_image, embed=embed)
        else:
            await channel.send(embed=embed)
        team_info.append(embed)

    if team_info:
        pass
    else:
        await channel.send('No teams created yet.')


#############################################################
# Selling Players:
#############################################################
async def sell_team(team_name, price, name, channel):
    global teams, purse, auction_sets, sale_history, unsold_players, full_team_names, team_colors, current_player_price, current_player, current_auction_set, sales_channel

    if team_name in teams:
        player_price = int(price)
        if len(teams[team_name]) >= MAX_PLAYERS:
            # Create an embedded message to indicate that the team has reached the player limit
            embed = discord.Embed(
                title=f'Team Player Limit Reached: {team_name}',
                description=f'Team {team_name} has reached the maximum player limit of {MAX_PLAYERS} players.',
                color=discord.Color.red())
            await channel.send(embed=embed)
        else:
            if player_price / 100 <= purse[team_name]:
                teams[team_name][name] = player_price
                purse[team_name] -= player_price / 100

                add_sale(full_team_names[team_name], name, player_price / 100)
                # Get the stored team color or default to green
                color = team_colors.get(team_name, discord.Color.green())

                # Create an embedded message to announce the player sale
                embed = discord.Embed(
                    title=f'Player Sold: {name}',
                    description=f'**{name}** has been sold to **{full_team_names[team_name]}** for **{player_price/100:.2f}Cr**.',
                    color=color)
                player_image_file = f'images/{name}.png'
                team_image_file = f'teams/{team_name}.png'
                files = []  # List to store files to be sent as attachments

                if os.path.isfile(player_image_file):
                    player_image = discord.File(
                        player_image_file, filename='Player.png')
                    files.append(player_image)
                    # Player image as an attachment
                    embed.set_image(url="attachment://Player.png")

                if os.path.isfile(team_image_file):
                    team_image = discord.File(
                        team_image_file, filename='Team.png')
                    files.append(team_image)
                    embed.set_thumbnail(
                        url="attachment://Team.png")  # Team image as a thumbnail

                await channel.send(files=files, embed=embed)
                if sales_channel:
                    await sales_channel.send(embed=embed)  # type: ignore
                for set_name, players in auction_sets.items():
                    if name in players:
                        players.remove(name)
                current_player = None  # Reset the current player name
                current_auction_set = None  # Reset the current auction set name

            else:
                embed = discord.Embed(
                    title=f'Team Over Budget!: {team_name}',
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
# Unsold:
##################################################################


async def unsold(channel):
    global teams, purse, auction_sets, sale_history, unsold_players, full_team_names, team_colors, current_player_price, current_player, current_auction_set, auction_data
    price = 'Unknown'
    if current_player:
        price = current_player_price
        unsold_players.add(
            (current_player, price))

        # Create an embedded message to confirm the player is marked as unsold
        embed = discord.Embed(
            title="Player Marked as Unsold",
            description=f'{current_player} has been marked as unsold and saved for later use.',
            color=discord.Color.greyple())
        await channel.send(embed=embed)
        current_player = None
        current_player_price = None

    else:
        # Create an embedded message to indicate there is no current player to mark as unsold
        embed = discord.Embed(title="No Player Unsold",
                              description="No player to mark as unsold.",
                              color=discord.Color.red())
        await channel.send(embed=embed)


async def show_unsold(channel):
    global current_auction_set
    global current_player
    global unsold_players
    if unsold_players:
        # Create a formatted message with unsold players and their base prices
        unsold_message = "\n".join([
            f'{player} (Base Price: {price})' for player, price in unsold_players
        ])

        # Create an embedded message to display unsold players
        embed = discord.Embed(title="Unsold Players",
                              description=unsold_message,
                              color=discord.Color.greyple())
        await channel.send(embed=embed)
    else:
        # Create an embedded message to indicate there are no unsold players
        embed = discord.Embed(title="No Unsold Players",
                              description="There are no unsold players available.",
                              color=discord.Color.greyple())
        await channel.send(embed=embed)


async def get_unsold(channel):
    global current_auction_set
    global current_player
    global unsold_players

    if current_player is not None:
        await complete_sale(channel)
        return None
    if unsold_players:
        # Pop and send one random player from the unsold set
        player, base_price = unsold_players.pop()
        embed = discord.Embed(title=f"Unsold Player: {player}",
                              description=f'Base Price: {base_price}',
                              color=discord.Color.greyple())
        await channel.send(embed=embed)
        current_player = player
        for user_id, players_to_notify in user_notifications.items():
            if player in players_to_notify:
                user = await client.fetch_user(user_id)
                if user:
                    await user.send(f"**{player}** is live in the auction!")
    else:
        # Create an embedded message to indicate there are no unsold players
        embed = discord.Embed(title="No Unsold Players",
                              description="There are no unsold players available.",
                              color=discord.Color.greyple())
        await channel.send(embed=embed)
        current_player = None


##################################################################
# Removing Players:
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
                if sale["team_name"] == full_team_names[team_name] and sale[
                        "player_name"] == player_name:
                    sale_history.remove(sale)

            # Create an embedded message to announce the player removal
            embed = discord.Embed(
                title=f'Player Removed: {player_name}',
                description=f'{player_name} has been removed from Team: {full_team_names[team_name]}.',
                color=discord.Color.green())
            await channel.send(embed=embed)
        else:
            # Create an embedded message to indicate that the player is not found in the team
            embed = discord.Embed(
                title=f'Player Not Found: {player_name}',
                description=f'{player_name} is not found in Team: {full_team_names[team_name]}.',
                color=discord.Color.red())
            await channel.send(embed=embed)
    else:
        # Create an embedded message to indicate that the team doesn't exist
        embed = discord.Embed(title=f'Team Not Found: {team_name}',
                              description=f'Team "{team_name}" does not exist.',
                              color=discord.Color.red())
        await channel.send(embed=embed)

##################################################################
# Removing teams:
##################################################################


async def remove_team(team_name, channel):
    global teams
    global unsold_players

    # Check if the team exists
    if team_name not in teams:
        embed = discord.Embed(title="Remove Team Failed",
                              color=discord.Color.red())
        embed.add_field(
            name="Error", value=f"The team '{team_name}' does not exist.")
        await channel.send(embed=embed)
        return

    # Add all players from the team to the unsold_players set with a base price of 1 Cr
    for player_name in teams[team_name]:
        unsold_players.add((player_name, 1))

    # Remove the team from the teams dictionary
    del teams[team_name]

    embed = discord.Embed(title="Remove Team Successful",
                          color=discord.Color.green())
    embed.add_field(name="Team Removed",
                    value=f"The team '{team_name}' has been removed, and all its players are set as unsold at 1 Cr.")
    await channel.send(embed=embed)

##################################################################
# Requesting Players:
##################################################################
request_semaphore = asyncio.Semaphore(1)


async def request_player(user, player_name, channel):
    global auction_sets
    global unsold_players
    global current_player

    # Attempt to acquire the semaphore
    async with request_semaphore:
        # Check if there is a current player being auctioned
        if current_player is not None:
            embed = discord.Embed(
                title=f"Request Denied for {player_name}",
                description=f"A player is currently being auctioned: {current_player}",
                color=discord.Color.red()
            )
            await channel.send(embed=embed)
            return

        # Check if the requested player is in the current auction set
        if current_player == player_name:
            embed = discord.Embed(
                title=f"Requested Player: {player_name}",
                description="This player is currently in the auction set.",
                color=discord.Color.red()
            )
            await channel.send(embed=embed)
            return

        # Send a message indicating that the request is pending confirmation
        confirmation_embed = discord.Embed(
            title=f'Request for **{player_name}**',
            description=f'{user} is requesting for **{player_name}** to be put on sale.',
            color=discord.Color.red()
        )
        confirmation_embed.add_field(
            name="Auctioneer to confirm:",
            value="Please confirm or deny this request.",
            inline=False
        )

        def check_stop(interaction):
            return is_auctioneer(interaction.user) and interaction.message == confirmation_message
        # Send the confirmation embed
        confirmation_message = await channel.send(embed=confirmation_embed)
        confirm = Button(style=discord.ButtonStyle.green, label="Confirm")
        cancel = Button(style=discord.ButtonStyle.red, label="Cancel")
        view = View()
        view.add_item(confirm)
        view.add_item(cancel)
        await confirmation_message.edit(view=view)

        # Define a check function to check which button they clicked
        async def confirmed(interaction):
            # Check if the requested player is in any of the auction sets
            global current_player
            await confirmation_message.delete()
            for set_name, players in auction_sets.items():
                if player_name in players:
                    # Send the player's card
                    base_price = base_prices.get(set_name, 'Unknown')
                    color_value = embed_colors.get(set_name, "blue")
                    if isinstance(color_value, str):
                        color = discord.Color.from_str(color_value)
                    else:
                        color = discord.Color(value=color_value)

                    embed = discord.Embed(
                        title=f"**{player_name}**",
                        description=f"Base Price: {base_price}\n Set: {set_name}",
                        color=color
                    )
                    player_image_file = f'images/{player_name}.png'
                    if os.path.isfile(player_image_file):
                        player_image = discord.File(
                            player_image_file, filename='Player.png')
                        embed.set_image(url="attachment://Player.png")
                        await channel.send(file=player_image, embed=embed)
                    else:
                        await channel.send(embed=embed)
                    for user_id, players_to_notify in user_notifications.items():
                        if player_name in players_to_notify:
                            user = await client.fetch_user(user_id)
                            if user:
                                await user.send(f"**{player_name}** is live in the auction!")

                    # Remove the player from the auction set
                    current_player = player_name
                    players.remove(player_name)
                    return

            # Check if the requested player is in the unsold players set
            for player, base_price in unsold_players:
                if player == player_name:
                    # Send the player's card
                    embed = discord.Embed(
                        title=f"**{player_name}**",
                        description=f"Base Price: {base_price},\n Set: Unsold Players",
                        color=discord.Color.greyple()
                    )
                    await channel.send(embed=embed)
                    # Remove the player from the unsold players set
                    current_player = player
                    for user_id, players_to_notify in user_notifications.items():
                        if player in players_to_notify:
                            user = await client.fetch_user(user_id)
                            if user:
                                await user.send(f"**{player}** is live in the auction!")
                    unsold_players.remove((player, base_price))
                    return

            # If the player is not found in either set, send a message
            embed = discord.Embed(
                title=f"Player Not Found: {player_name}",
                description="The requested player was not found in the auction sets or the unsold players set.",
                color=discord.Color.red()
            )
            await channel.send(embed=embed)

        async def cancel_check(interaction):
            cancel_embed = discord.Embed(
                title="Denied request",
                description=f"Request denied  for **{player_name}**.",
                color=discord.Color.red()
            )
            await channel.send(embed=cancel_embed)
            await confirmation_message.delete()
            return
        confirm.callback = confirmed
        cancel.callback = cancel_check


##################################################################
# Showing Team:
##################################################################


async def show_team(team_name, channel):
    # Convert the provided team_name to lowercase to handle case-insensitive lookup
    team_name_lower = team_name.lower()

    if team_name_lower in map(str.lower, teams):
        # Find the original case team name based on the lowercase version
        original_team_name = next(key for key in teams
                                  if key.lower() == team_name_lower)

        players_info = []
        count = 0
        for player, price in teams[original_team_name].items():
            count += 1
            players_info.append(
                f'{count}.**{player}({price/100}Cr)**')

        purse_amount = purse.get(original_team_name, 0)
        full_team_name = full_team_names.get(original_team_name,
                                             original_team_name)

        if players_info:
            players_message = "\n".join(players_info)
        else:
            players_message = "No players bought by this team."

        embed = discord.Embed(
            title=f'Team: {full_team_name}',
            description=f'**Remaining Purse: {purse_amount}**\n\nPlayers:\n{players_message}',
            color=team_colors.get(original_team_name, discord.Color.green()))
        team_image_file = f'teams/{team_name}.png'
        if os.path.isfile(team_image_file):
            team_image = discord.File(
                team_image_file, filename='Team.png')
            embed.set_thumbnail(
                url="attachment://Team.png")
            await channel.send(file=team_image, embed=embed)
        else:
            await channel.send(embed=embed)
    else:
        # Create an embedded message to indicate that the team doesn't exist
        embed = discord.Embed(title=f'Team Not Found: {team_name}',
                              description=f'Team "{team_name}" does not exist.',
                              color=discord.Color.red())
        await channel.send(embed=embed)


##################################################################
# Sale History:
##################################################################
async def show_sales(channel):
    if sale_history:
        # Sort the sale history by timestamp
        sorted_history = sorted(sale_history, key=lambda x: x['timestamp'])

        # Split the sorted_history into chunks of 30 entries each
        chunk_size = 30
        chunks = [
            sorted_history[i:i + chunk_size]
            for i in range(0, len(sorted_history), chunk_size)
        ]

        for chunk in chunks:
            history_message = ""
            for entry in chunk:
                timestamp = entry["timestamp"]
                if entry["type"] == "sale":
                    history_message += f'[{timestamp} IST] **{entry["player_name"]}** sold to **{entry["team_name"]}** for **{entry["price"]}Cr**\n'
                elif entry["type"] == "trade":
                    history_message += f'[{timestamp} IST] **{entry["team_1"]}** traded **{entry["player_1"]}** to **{entry["team_2"]}** for **{entry["player_2"]}**\n'

            # Create an embedded message to display the combined sales message for this chunk
            embed = discord.Embed(title='Sales and Trade History',
                                  description=history_message,
                                  color=discord.Color.blue())
            await channel.send(embed=embed)
    else:
        embed = discord.Embed(title='Sales and Trade History',
                              description='No sales or trades have been made yet.',
                              color=discord.Color.blue())
        await channel.send(embed=embed)


##################################################################
# Trade:
##################################################################
async def trade(team1_name, team2_name, players, channel):
    global sales_channel
    # Split the players argument into two player names using a delimiter ("/")
    player_names = players.split('/')

    if len(player_names) != 2:
        embed = discord.Embed(title="Invalid Trade Command",
                              color=discord.Color.red())
        embed.add_field(name="Usage",
                        value="$trade <team1> <team2> <player1> / <player2>")
        await channel.send(embed=embed)
        return

    player1_name = player_names[0].strip()
    player2_name = player_names[1].strip()
    if player1_name.isnumeric() or player2_name.isnumeric():
        if player1_name.isnumeric():
            player1_value = int(player1_name)
            player2_value = teams[team2_name][player2_name]
            if (purse[team1_name] - player1_value/100 < 0):
                embed = discord.Embed(
                    title="Trade Failed", color=discord.Color.red())
                embed.add_field(name="Error",
                                value=f"**{team1_name}** cannot afford this trade.")
                await channel.send(embed=embed)
                return
            del teams[team2_name][player2_name]
            teams[team1_name][player2_name] = player2_value
            purse[team2_name] = purse[team2_name] + player1_value / 100
            purse[team1_name] = purse[team1_name] - player1_value / 100
            add_trade(full_team_names[team1_name], full_team_names[team2_name],
                      f'{player1_value/100}Cr', player2_name)
            embed = discord.Embed(title="Trade Successful",
                                  color=discord.Color.green())
            embed.add_field(
                name=f"Trade Details",
                value=f"**{player2_name}** from **{team2_name}** bought for **{player1_value/100}Cr** by **{team1_name}**."
            )
            await channel.send(embed=embed)

            return
        if player2_name.isnumeric():
            player2_value = int(player2_name)
            player1_value = teams[team1_name][player1_name]
            if (purse[team2_name] - player2_value/100 < 0):
                embed = discord.Embed(
                    title="Trade Failed", color=discord.Color.red())
                embed.add_field(name="Error",
                                value=f"**{team2_name}** cannot afford this trade.")
                await channel.send(embed=embed)
                return
            del teams[team1_name][player1_name]
            teams[team2_name][player1_name] = player1_value
            purse[team1_name] = purse[team1_name] + player2_value / 100
            purse[team2_name] = purse[team2_name] - player2_value / 100
            add_trade(full_team_names[team2_name], full_team_names[team1_name],
                      f'{player2_value/100}Cr', player1_name)
            embed = discord.Embed(title="Trade Successful",
                                  color=discord.Color.green())
            embed.add_field(
                name=f"Trade Details",
                value=f"**{player1_name}** from **{team1_name}** bought for **{player2_value/100}Cr** by **{team2_name}**."
            )
            await channel.send(embed=embed)
            return

    # Check if both teams exist
    if team1_name not in teams or team2_name not in teams:
        embed = discord.Embed(title="Trade Failed", color=discord.Color.red())
        embed.add_field(name="Error",
                        value="One or both of the teams do not exist.")
        await channel.send(embed=embed)
        return

    # Check if both players exist in their respective teams
    if player1_name not in teams[team1_name] or player2_name not in teams[
            team2_name]:
        embed = discord.Embed(title="Trade Failed", color=discord.Color.red())
        embed.add_field(
            name="Error",
            value="One or both of the players do not exist in their respective teams.")
        await channel.send(embed=embed)
        return

    # Calculate the values of the players
    player1_value = teams[team1_name][player1_name]
    player2_value = teams[team2_name][player2_name]

    # Check if both teams can afford the trade
    if (purse[team1_name] + player1_value / 100 - player2_value / 100 < 0) or (
            purse[team2_name] + player2_value / 100 - player1_value / 100 < 0):
        embed = discord.Embed(title="Trade Failed", color=discord.Color.red())
        embed.add_field(name="Error",
                        value="One or both teams cannot afford this trade.")
        await channel.send(embed=embed)
        return

    # Perform the trade
    del teams[team1_name][player1_name]
    del teams[team2_name][player2_name]

    teams[team1_name][player2_name] = player2_value
    teams[team2_name][player1_name] = player1_value

    # Update purse balances
    purse[team1_name] = purse[
        team1_name] + player1_value / 100 - player2_value / 100
    purse[team2_name] = purse[
        team2_name] + player2_value / 100 - player1_value / 100

    # Log the trade
    add_trade(full_team_names[team1_name], full_team_names[team2_name],
              player1_name, player2_name)

    # Send a trade success embed
    embed = discord.Embed(title="Trade Successful",
                          color=discord.Color.green())
    embed.add_field(
        name=f"Trade Details",
        value=f"{player1_name} from {team1_name} traded for {player2_name} from {team2_name}."
    )
    await channel.send(embed=embed)
    if sales_channel:
        await sales_channel.send(embed=embed)  # type: ignore


##################################################################
# Complete Sale:
##################################################################
async def complete_sale(channel):
    global auction_sets
    global teams
    global purse
    global sale_history

    # Create an embed for the confirmation message
    confirmation_embed = discord.Embed(
        title=f'Ongoing bid: **{current_player}**',
        description=f'**{current_player}** is currently being bid for.',
        color=discord.Color.red())
    confirmation_embed.add_field(name="Do you wish to mark as Unsold?:",
                                 value="Please confirm or deny this request.",
                                 inline=False)

    # Send the confirmation embed
    confirmation_message = await channel.send(embed=confirmation_embed)
    confirm = Button(style=discord.ButtonStyle.green, label="Confirm")
    cancel = Button(style=discord.ButtonStyle.red, label="Cancel")
    view = View()
    view.add_item(confirm)
    view.add_item(cancel)
    await confirmation_message.edit(view=view)

    # Define a check function to check which button they clicked
    async def confirmed(interaction):
        await unsold(channel)
        await confirmation_message.delete()
        return

    async def cancel_check(interaction):
        cancel_embed = discord.Embed(title="Player Still On Sale",
                                     description="Unsold marking canceled.",
                                     color=discord.Color.red())
        await channel.send(embed=cancel_embed)
        await confirmation_message.delete()
        return

    confirm.callback = confirmed
    cancel.callback = cancel_check
##################################################################
# Export to csv
##################################################################


async def export(channel):
    global teams
    with open(f'cricket_data.csv', 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["Name"])
        for team_name, players in teams.items():
            for player, price in players.items():
                writer.writerow([player])
    await channel.send(file=discord.File(f'cricket_data.csv'))
    return

##################################################################
# Showing Help:
##################################################################


async def show_help(channel):
    embed = discord.Embed(title='Help Commands for Auctioneer:',
                          description='Here are the available commands:',
                          color=discord.Color.red())
    embed.add_field(name='$add <shorthand> <color> <team_name>',
                    value='Creates a new team with the given name.',
                    inline=False)
    embed.add_field(name='$sell <team> <price> <player>',
                    value='Sells a player to a team.',
                    inline=False)
    embed.add_field(name='$sold <team> <price>',
                    value='Sells the current player to a team.',
                    inline=False)
    embed.add_field(name='$trade <team1> <team2> <player1>/<player2>',
                    value='Trades a player from one team to another.\nPurchases one player from other team if one of the player fields is a number, in Lakhs', inline=False)
    embed.add_field(name='$<set_name>',
                    value='Displays a random player from the set.',
                    inline=False)
    embed.add_field(name='$removeplayer <team> <player>',
                    value='Removes a player from a team.',
                    inline=False)
    embed.add_field(name='$removeteam <team>',
                    value='Removes a team.', inline=False)
    embed.add_field(name='$reset', value='Resets all the sets.', inline=False)
    embed.add_field(name='$setmaxpurse <value>',
                    value='Sets the maximum purse value. Default 100',
                    inline=False)
    embed.add_field(name='$setmaxplayers <value>',
                    value='Sets the maximum players value. Default 25',
                    inline=False)
    embed.add_field(name='$unsold',
                    value='Marks the current player as unsold.',
                    inline=False)
    embed.add_field(name='$getunsold',
                    value='Gets a player from the unsold list.',
                    inline=False)
    embed.add_field(
        name='$export', value='Exports the data to a csv file.', inline=False)
    await channel.send(embed=embed)
    embed = discord.Embed(title='Help Commands for All Users:',
                          description='Here are the available commands:',
                          color=discord.Color.brand_green())
    embed.add_field(name='$request <player>',
                    value='Shows the player if available.',
                    inline=False)
    embed.add_field(name='$showunsold',
                    value='Shows all the unsold players.',
                    inline=False)
    embed.add_field(name='$teams', value='Shows all the teams.', inline=False)
    embed.add_field(name='$<team>',
                    value='Shows information about a team.',
                    inline=False)
    embed.add_field(
        name='$help', value='Shows this help message.', inline=False)
    embed.add_field(name='$sets', value='Shows all the sets.', inline=False)
    embed.add_field(name='$set <set_name>',
                    value='Shows the set with the given name.',
                    inline=False)
    embed.add_field(
        name='$timer <value>',
        value='Sets a timer for entered seconds. 10 seconds if no input.',
        inline=False)
    embed.add_field(name='$sales',
                    value='Shows the history of sales and trades.',
                    inline=False)
    embed.add_field(name='$notify <player(s) seperated by comma>',
                    value='Notifies you when the player is live in the auction.(Can use in DM)', inline=False)

    await channel.send(embed=embed)


@client.event
async def on_disconnect():
  global teams, purse, auction_sets, sale_history, unsold_players, full_team_names, team_colors, current_player_price, current_player, current_auction_set, filename, pkls
  save_data({
      'teams': teams,
      'purse': purse,
      'auction_sets': auction_sets,
      'sale_history': sale_history,
      'unsold_players': unsold_players,
      'full_team_names': full_team_names,
      'team_colors': team_colors,
      'current_auction_set': current_auction_set,
      'current_player': current_player,
      'current_player_price': current_player_price,
  })


client.run(os.environ['TOKEN'])
