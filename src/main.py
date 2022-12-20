from ntpath import join
import discord
from dotenv import dotenv_values
import pathlib
import sys

settings_env_path = pathlib.PurePath(__file__).parent.joinpath('settings.env')
config = dotenv_values(settings_env_path)

bot = discord.Bot()

cogs_list = [
    'moderation'
]

for cog in cogs_list:
    bot.load_extension(f'cogs.{cog}')

@bot.event
async def on_ready():
    print(f"We have logged in as {bot.user}")

@bot.slash_command(guild_ids=[456413000887435285])
@discord.ext.commands.is_owner()
async def reload(ctx):
    for cog in cogs_list:
        bot.reload_extension(f'cogs.{cog}')
    await ctx.respond("Reloaded", ephemeral=True)
    print("Reloaded Cogs")

bot.run(config['DISCORD_API_TOKEN'])