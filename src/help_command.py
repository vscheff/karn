from discord.ext.commands import Command, HelpCommand

from src.utils import package_message


class CustomHelpCommand(HelpCommand):
    def __init__(self):
        super().__init__()

    # Called when a user gives the $help command
    # param mapping - a mapping of cogs to commands
    async def send_bot_help(self, mapping):
        cog_list = {}

        for cog, commands in mapping.items():
            # Skip cogs that don't contain commands
            if not commands:
                continue
            
            cog_list[cog.qualified_name if cog else "Miscellaneous"] = commands

        for command in self.context.bot.tree.get_commands():
            cog_name = command.binding.__class__.__name__ if command.binding else "Miscellaneous"
            cog_list.setdefault(cog_name, [])
            
            if not any(i.name == command.name for i in cog_list[cog_name]):
                cog_list[cog_name].append(command)

        command_list = [f"# {key}\n{self.get_command_list(val)}" for key, val in cog_list.items()]
        await package_message('\n'.join(command_list), self.get_destination(), multi_send=True)

    # Called when user gives the $help {cog_name} command
    # param cog - the cog that was requested for help
    async def send_cog_help(self, cog, return_text=False):
        command_list = cog.get_commands()

        for cmd in self.context.bot.tree.get_commands():
            if cmd.binding and cmd.binding.__class__.__name__ == cog.qualified_name and not any(i.name == cmd.name for i in command_list):
                command_list.append(cmd)
        
        response = f"# {cog.qualified_name}\n{self.get_command_list(command_list)}"

        if return_text:
            return response

        await self.get_destination().send(response)

    # Called when user gives the $help {command_name} command
    # param command - the command that was requested for help
    async def send_command_help(self, command):
        if command.hidden:
            return
        await self.get_destination().send(f"# {command.name}\n{command.help}")

    async def command_not_found(self, name):
        for command in self.context.bot.tree.get_commands():
            if command.name != name:
                continue

            return f"# {name}\n{command.extras['help']}"

        for cog in self.context.bot.cogs.values():
            if cog.qualified_name.lower() == name:
                return await self.send_cog_help(cog, return_text=True)

        return f"No command called \"{name}\" found."

    def get_command_list(self, commands):
        ret_list = []

        for command in commands:
            if isinstance(command, Command):
                if command.hidden:
                    continue
                
                ret_list.append({"name": command.name, "brief": command.brief, "prefix": "$"})
            else:
                if command.extras.get("hidden"):
                    continue

                ret_list.append({"name": command.name, "brief": command.extras.get("brief", ""), "prefix": "/"})
        
        return "* " + "\n* ".join([f"`{i['prefix']}{i['name']}` - {i['brief']}" for i in sorted(ret_list, key=lambda x: x["name"])])
