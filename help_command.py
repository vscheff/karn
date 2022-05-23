# Custom help command for BUSTER
# Inititialized by ./bot.py and used to override the defualt help command

from discord.ext import commands as c


class CustomHelpCommand(c.HelpCommand):
    def __init__(self):
        super().__init__()

    # Called when a user gives the $help command
    # param mapping - a mapping of cogs to commands
    async def send_bot_help(self, mapping):
        cog_list = []
        misc_commands = []
        for cog, commands in mapping.items():
            # Skip cogs that don't contain commands
            if not commands:
                continue
            # Only include this cog if it has at least one public command
            if command_list := self.get_command_list(commands):
                if cog:
                    cog_list.append(f'**{cog.qualified_name}**:\n{command_list}')
                else:
                    cog_list.append(f'**Miscellaneous**:\n{command_list}')
        await self.get_destination().send('\n'.join(cog_list))

    # Called when user gives the $help {cog_name} command
    # param cog - the cog that was requested for help
    async def send_cog_help(self, cog):
        command_list = self.get_command_list(cog.get_commands())
        await self.get_destination().send(f'**{cog.qualified_name}**:\n{command_list}')

    # Called when user gives the $help {command_name} command
    # param command - the command that was requested for help
    async def send_command_help(self, command):
        if command.hidden and not self.context.author.guild_permissions.administrator:
            return
        await self.get_destination().send(f'**{command.name}**:\n{command.help}')

    def get_command_list(self, commands):
        if self.context.author.guild_permissions.administrator:
            return '\n'.join(sorted([f'    *{i.name}* - {i.brief}' for i in commands]))
        return '\n'.join(sorted([f'    *{i.name}* - {i.brief}' for i in commands if not i.hidden]))
