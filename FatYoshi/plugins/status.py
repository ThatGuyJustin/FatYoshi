import json
from datetime import datetime

import yaml
from disco.api.http import APIException
from disco.bot import Plugin
from disco.types.channel import ChannelType
from disco.types.user import ActivityTypes

from FatYoshi.config import is_config_loaded, bot_config


class StatusPlugin(Plugin):
    def load(self, ctx):
        self.users = {}
        self.cache = {}
        self.user_queue = {}

        if not is_config_loaded():
            self.log.error("Bot config not loaded, unloading plugin.")
            self.unload(ctx)
            return

        for snowflake, channel_id in dict(bot_config.status_watching).items():
            # Validation.
            user = self.bot.client.api.users_get(snowflake)
            channel = self.bot.client.api.channels_get(channel_id)

            if not user:
                self.log.warning(f"{snowflake} is not a valid user ID, skipping.")
                continue

            if not channel:
                self.log.warning(f"{channel_id} is not a valid channel ID for user {user.username}. Check Bot Permissions or ID. Skipping.")
                continue

            if snowflake not in self.cache:
                self.users[snowflake] = [channel_id]
            else:
                self.users[snowflake].append(channel_id)

        self.log.info(f"Loaded {len(self.users)} users")

        try:
            with open('./data/status_cache.json', 'r') as f:
                cache = json.load(f)
                self.cache = cache
        except FileNotFoundError:
            pass

        super(StatusPlugin, self).load(ctx)

    def unload(self, ctx):

        # Skip, extra IO is not needed.
        if not len(self.cache):
            return super(StatusPlugin, self).unload(ctx)

        self.log.info("Saving status cache")

        with open('./data/status_cache.json', 'w') as f:
            json.dump(self.cache, f)

        return super(StatusPlugin, self).unload(ctx)

    def send_status_messages(self, user, status):
        for channel in self.users[user.id]:
            api_channel = self.client.api.channels_get(channel)
            _format = f"> {status}\n-# {user.mention} –– <t:{int(datetime.now().timestamp())}:s>"
            msg = api_channel.send_message(_format, allowed_mentions={})

            # Auto-Publish Post.
            if api_channel.type == ChannelType.GUILD_ANNOUNCEMENT:
                try:
                    self.client.api.channels_messages_publish(channel, msg.id)
                except APIException:
                    pass


    @Plugin.listen('PresenceUpdate')
    def watch_kirby(self, event):

        if event.user.id not in self.users:
            return

        if event.user.id in self.user_queue:
            return

        self.user_queue[event.user.id] = 1
        for activity in event.activities:
            if activity.type != ActivityTypes.CUSTOM:
                continue

            if self.cache.get(str(event.user.id)) and activity.state in self.cache.get(str(event.user.id)):
                break

            # Send message to all channels
            self.send_status_messages(event.user, activity.state)

            if not self.cache.get(str(event.user.id)):
                self.cache[str(event.user.id)] = []

            if activity.state not in self.cache.get(str(event.user.id)):
                self.cache[str(event.user.id)].append(activity.state)
                if len(self.cache[str(event.user.id)]) >= 10:
                    self.cache[str(event.user.id)].pop(0)

            break

        del self.user_queue[event.user.id]
