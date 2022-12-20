import pathlib
import datetime
from dotenv import dotenv_values
from math import ceil, floor
from discord.ext import tasks, commands
import discord
from classes.sqliteDatabase import sqliteDatabaseHandler
import os
import sys
sys.path.append(".")


database_path = pathlib.PurePath(__file__).parents[1].joinpath('moderation.db')
database = sqliteDatabaseHandler(database_path)


def get_config():
    settings_env_path = pathlib.PurePath(__file__).parents[1].joinpath('settings.env')
    return dotenv_values(settings_env_path)


config = get_config()


class Moderation(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.unban_passed_bans.start()

    @discord.slash_command(guild_ids=[456413000887435285],
                           description="Report a misbehaving user.",
                           )
    async def report(self, ctx, name: discord.Option(discord.Member)):
        modal = ReportModal(name)
        await ctx.send_modal(modal)

    @discord.slash_command(guild_ids=[456413000887435285])
    @commands.has_role(456486518756999178)
    async def offence(self, ctx, user: discord.Option(discord.User), penalty_points: discord.Option(int), days: discord.Option(int) = None):
        modal = OffenceModal(user, penalty_points, days, title="Offence Report")
        await ctx.send_modal(modal)

    @discord.slash_command(guild_ids=[456413000887435285])
    async def list(self, ctx, name: discord.Option(discord.User)):
        offences = database.getOffenceMember(name.id)
        offences.reverse()
        if len(offences) == 0:
            await ctx.respond("This user has no offences.", ephemeral=True)
        else:
            embed = await generatePage(1, ctx, offences)
            await ctx.respond(embeds=[embed], view=OffenceListMessage(ctx, offences), ephemeral=True)

    @discord.slash_command(guild_ids=[456413000887435285])
    @commands.has_role(456486518756999178)
    async def removeoffence(self, ctx, offence_id: discord.Option(int)):
        user_id = database.getUserIDBanned(offence_id)
        if user_id:
            try:
                user = await self.bot.fetch_user(user_id[0][0])
                guild = await self.bot.fetch_guild(456413000887435285)
                await guild.unban(user, reason="Offence Removed")
            except discord.errors.NotFound:
                pass
        database.removeOffence(offence_id)
        await ctx.respond("Offence removed.", ephemeral=True)

    @discord.slash_command(guild_ids=[456413000887435285])
    @commands.has_role(456486518756999178)
    async def editoffence(self, ctx, offence_id: discord.Option(int), column: discord.Option(str, choices=['Penalty Points', 'Ban Time']), new_value):
        if column == 'Penalty Points':
            try:
                int(new_value)
            except ValueError:
                await ctx.respond("ERROR: Use an integer when chaning the penalty points.", ephemeral=True)
                return
            database.editPenaltyPoints(offence_id, new_value)
        elif column == 'Ban Time':
            try:
                int(new_value[:-1])
            except ValueError:
                await ctx.respond("ERROR: please use '10d' or '4h' for example.", ephemeral=True)
                return
            offence = database.getOffence(offence_id)[0]
            datetime_offence = datetime.datetime.strptime(
                offence[1], '%Y-%m-%d %H:%M:%S.%f')
            if int(new_value[:-1]) == 0:
                new_datetime = None
                user_id = database.getUserIDBanned(offence_id)
                if user_id:
                    try:
                        guild = await self.bot.fetch_guild(456413000887435285)
                        user = await self.bot.fetch_user(offence[3])
                        await guild.unban(user, reason="Automatic Unban")
                    except discord.errors.NotFound:
                        pass
            elif new_value[-1] == 'd':
                new_datetime = datetime.timedelta(
                    days=int(new_value[:-1])) + datetime_offence
            elif new_value[-1] == 'h':
                new_datetime = datetime.timedelta(
                    hours=int(new_value[:-1])) + datetime_offence
            else:
                await ctx.respond("ERROR: only hours (h) or days (d) are available.", ephemeral=True)
                return
            database.editBanTime(offence_id, new_datetime)
        await ctx.respond("Offence edited", ephemeral=True)

    @tasks.loop(seconds=60)
    async def unban_passed_bans(self):
        guild = await self.bot.fetch_guild(456413000887435285)
        user_ids = database.getBansPassed()
        for user_id in user_ids:
            try:
                user = await self.bot.fetch_user(user_id[0])
                await guild.unban(user, reason="Automatic Unban")
            except discord.errors.NotFound:
                pass
            database.changeBannedState(user_id[0])


def setup(bot):
    bot.add_cog(Moderation(bot))

#################################################################################################

#################################################################################################


class ReportModal(discord.ui.Modal):

    def __init__(self, name, *args, **kwargs) -> None:
        super().__init__(title='Creating a report', *args, **kwargs)
        self.name = name

        self.add_item(discord.ui.InputText(
            label="Tell Us What Happend", style=discord.InputTextStyle.long))

    async def callback(self, interaction: discord.Interaction):
        embed = discord.Embed(title="New Report", color=0xff0000)
        embed.set_author(name=interaction.user,
                         icon_url=interaction.user.display_avatar)
        embed.add_field(
            name="**__INFO__**", value=f"**Reported by:** {interaction.user} {interaction.user.mention}\n **Reported User:** {self.name} {self.name.mention}\n **From:** {interaction.channel.mention}", inline=False)
        embed.add_field(name="Report About", value=self.children[0].value)

        channel = interaction.guild.get_channel(int(config["REPORT_CHANNEL"]))

        await interaction.response.send_message("Report has been sent!", ephemeral=True)
        await channel.send(embeds=[embed], view=ReportLogMessage(self.name, self.children[0].value, interaction, timeout=None))


class OffenceModal(discord.ui.Modal):
    config = dotenv_values(".env")

    def __init__(self, name, penalty_points, days, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.name = name
        self.penalty_points = penalty_points
        self.days = days

        self.add_item(discord.ui.InputText(
            label="Reason", style=discord.InputTextStyle.long))

    async def callback(self, interaction: discord.Interaction):
        total_penalty_points_before = database.sumPenaltyPoints(self.name.id)
        total_penalty_points_now = total_penalty_points_before + self.penalty_points

        embed = discord.Embed(title="Offence", color=0xff9500)
        embed.add_field(
            name="**__INFO__**", value=f"**Responsible moderator:** {interaction.user} {interaction.user.mention}\n\n**User:** {self.name} {self.name.mention} \n **Penalty Points:** {self.penalty_points}\n**Total Penalty Points:** {total_penalty_points_now}", inline=False)
        embed.add_field(name="Reason", value=self.children[0].value)

        mod_channel = interaction.guild.get_channel(
            int(config["MODERATION_LOG_CHANNEL"]))
        public_channel = interaction.guild.get_channel(
            int(config["PUBLIC_MODERATION_LOG_CHANNEL"]))

        await mod_channel.send(self.name.mention, embeds=[embed])
        await public_channel.send(self.name.mention, embeds=[embed])
        
        hours_banned = 10*6**(total_penalty_points_now/8)

        if self.days:
            if self.days > hours_banned/24:
                hours_banned = self.days*24
        if floor(total_penalty_points_before/5) != floor((total_penalty_points_now)/5) | isinstance(self.days, int)  :
            ban_time = datetime.datetime.now() + datetime.timedelta(hours=hours_banned)
            database.insertOffenceQuery(interaction.guild.id, self.name.id, interaction.user.id,
                                        self.penalty_points, self.children[0].value, autoban=ban_time)

            ban_length_string = ' %d days and %d hours' % (
                hours_banned // 24, hours_banned % 24)
            if self.days:
                if self.days*24 == hours_banned:
                    embed = discord.Embed(title="CUSTOM BAN", color=0xff0000)
            else:
                embed = discord.Embed(title="AUTO BAN", color=0xff0000)
            embed.add_field(
                name="**__INFO__**", value=f"**Responsible moderator:** {interaction.user} {interaction.user.mention}\n\n**User:** {self.name} {self.name.mention} \n\n **Banned for:** {ban_length_string}\n **Banned till:** {ban_time.strftime('%H:%M %d-%m-%Y')}\n**Total Penalty Points:** {total_penalty_points_now}", inline=False)

            await self.name.send(f"Reason: {self.children[0].value}", embeds=[embed])
            await mod_channel.send(self.name.mention, embeds=[embed])
            await public_channel.send(self.name.mention, embeds=[embed])

            await self.name.ban(reason=self.children[0].value)
        else:
            database.insertOffenceQuery(interaction.guild.id, self.name.id, interaction.user.id,
                                        self.penalty_points, self.children[0].value, autoban=None)

        await interaction.response.send_message("Offence has been processed!", ephemeral=True)


class ReportLogMessage(discord.ui.View):
    def __init__(self, name, about, interaction, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.name = name
        self.about = about
        self.interaction = interaction

    @discord.ui.button(label="Solved", row=0, style=discord.ButtonStyle.success)
    async def first_button_callback(self, button, interaction):
        embed = discord.Embed(title="Report Solved", color=0x00ff00)
        embed.set_author(name=interaction.user,
                         icon_url=interaction.user.display_avatar)
        embed.add_field(
            name="**__INFO__**", value=f"**Reported by:** {self.interaction.user} {self.interaction.user.mention}\n **Reported User:** {self.name} {self.name.mention}\n **From:** {self.interaction.channel.mention}", inline=False)
        embed.add_field(name="Report About", value=self.about)
        await interaction.response.edit_message(embeds=[embed], view=None)


class OffenceListMessage(discord.ui.View):
    def __init__(self, ctx, offences, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ctx = ctx
        self.offences = offences
        self.page_no = 1

        number_offences = len(offences)
        self.num_pages = ceil(number_offences/6)

        self.disable_buttons()

    def disable_buttons(self):
        for child in self.children:
            if self.page_no == 1 and child.label == 'PREVIOUS':
                child.disabled = True
            elif self.page_no == self.num_pages and child.label == 'NEXT':
                child.disabled = True
            else:
                child.disabled = False

    @discord.ui.button(label="PREVIOUS")
    async def first_button_callback(self, button, interaction):
        self.page_no -= 1
        embed = await generatePage(self.page_no, self.ctx, self.offences)
        self.disable_buttons()
        await interaction.response.edit_message(embeds=[embed], view=self)

    @discord.ui.button(label="NEXT")
    async def second_button_callback(self, button, interaction):
        self.page_no += 1
        embed = await generatePage(self.page_no, self.ctx, self.offences)
        self.disable_buttons()
        await interaction.response.edit_message(embeds=[embed], view=self)

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True

#################################################################################################

#################################################################################################


async def generatePage(page_no, interaction, offences):
    number_offences = len(offences)
    num_pages = ceil(number_offences/6)

    embed = discord.Embed(title=f"Page {page_no}/{num_pages}", color=0x0027FF)

    if 6*page_no > number_offences:
        offences_on_page = offences[6*(page_no-1):number_offences]
    else:
        offences_on_page = offences[6*(page_no-1):6*page_no]
    for offence in offences_on_page:
        moderator = await interaction.bot.fetch_user(offence[4])
        if offence[6] == None:
            embed.add_field(name=f"#{offence[0]} | warn | {offence[1][0:10]}",
                            value=f"""Moderator: {moderator.mention} 
Penalty points: {offence[5]}

Reason: {offence[7]}""",
                            inline=True)
        else:
            ban_time = datetime.datetime.strptime(
                offence[6], '%Y-%m-%d %H:%M:%S.%f') - datetime.datetime.strptime(offence[1], '%Y-%m-%d %H:%M:%S.%f')
            days_banned = ban_time.days
            hours_banned = ban_time.seconds/3600
            ban_length_string = f'{days_banned:.0f} days and {hours_banned % 24:.0f} hours'
            embed.add_field(name=f"#{offence[0]} | ban | {offence[1][0:10]}",
                            value=f"""Moderator: {moderator.mention}
Penalty points: {offence[5]}
Banned for: {ban_length_string}

Reason: {offence[7]}""",
                            inline=True)

    return embed
