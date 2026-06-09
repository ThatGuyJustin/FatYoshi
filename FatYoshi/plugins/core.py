import time
import yaml
from disco.bot import Plugin
from disco.bot.command import CommandEvent
from disco.types.application import InteractionType, InteractionCallbackType
from disco.types.message import MessageFlags

from FatYoshi.config import bot_config, load_config


class CorePlugin(Plugin):
    def load(self, ctx):

        cfg_loaded = load_config()

        if not cfg_loaded:
            self.log.error("Unable to load config file. Some plugins may automatically-disable.")

        self.admin_role = None

        if not hasattr(bot_config, "admin_role"):
            self.log.warning("admin_role not defined in config. You will not be able to run any text commands.")
        else:
            self.admin_role = bot_config.admin_role

        super(CorePlugin, self).load(ctx)

    def _get_ping(self, event):
        pre = time.perf_counter_ns()
        post = time.perf_counter_ns() - pre

        vc = None
        if event.guild.id in self.bot.client.state.voice_clients:
            vc = ' `VC: {:,}ms`'.format(float(self.bot.client.state.voice_clients[event.guild.id].latency))

        return {"bot": int(post), "vc": vc, "api": float(self.bot.client.gw.latency)}

    @Plugin.listen('Ready')
    def on_ready(self, event):
        self.log.info(f"Bot connected as {self.client.state.me}")

        self.log.info("Attempting to update registered commands...")
        try:
            with open("./config/commands.yaml", "r") as raw_commands:
                parsed_commands = yaml.safe_load(raw_commands)

            if parsed_commands.get('commands') is None:
                self.log.info("No commands found. Skipping...")
                return

            commands_to_register = parsed_commands.get('commands')

            if commands_to_register.get('global'):
                new_commands = self.client.api.applications_global_commands_bulk_overwrite(
                    commands_to_register.get('global'))
                self.log.info(f"Updated {len(new_commands)} global commands")

            if commands_to_register.get('guild'):
                self.log.warning("NYI.")

        except FileNotFoundError:
            self.log.warning(f"Couldn't find command file 'config/commands.yaml'")

    @Plugin.listen('MessageCreate')
    def on_command_msg(self, event):
        """
        Written by Nadie#0063 as a basic command handler for Disco instead of using the build in one.
        """
        if event.message.author.bot:
            return
        if not event.guild:
            return

        if (self.admin_role is None) or (self.admin_role not in event.member.roles):
            return

        commands = self.bot.get_commands_for_message(False, {}, '!', event.message)
        if not commands:
            return
        for command, match in commands:
            return command.plugin.execute(CommandEvent(command, event, match))

    # Text Command
    @Plugin.command('ping')
    def ping(self, event):
        """
        Display the delay between the bot and the Discord API.
        """
        ping_values = self._get_ping(event)
        return event.reply(':eyes: `BOT: {:,}ns` `API: {:,}ms`{}'.format(ping_values["bot"], ping_values["api"],
                                                                         ping_values.get("vc", '')))

    # Slash Command
    @Plugin.listen('InteractionCreate', conditional=lambda e: e.type == InteractionType.APPLICATION_COMMAND and e.data.name == "ping")
    def ping_command(self, event):
        """
        Display the delay between the bot and the Discord API.
        """
        ping_values = self._get_ping(event)
        return event.reply(content=':eyes: `BOT: {:,}ns` `API: {:,}ms`{}'.format(ping_values["bot"], ping_values["api"],
                                                                         ping_values.get("vc", '')), type=InteractionCallbackType.CHANNEL_MESSAGE_WITH_SOURCE, flags=MessageFlags.EPHEMERAL)