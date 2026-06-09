import json
import feedparser
import yaml
import re
from disco.bot import Plugin
from urllib.parse import urlparse
import dateutil.parser as parser
from datetime import datetime

from FatYoshi.config import is_config_loaded, bot_config


class MediaPlugin(Plugin):
    def load(self, ctx):
        self.loading = True

        if not is_config_loaded():
            self.log.error("Bot config not loaded, unloading plugin.")
            self.unload(ctx)
            return

        self.rss_config = {}

        if not hasattr(bot_config, 'media') or not hasattr(bot_config.media, 'rss'):
            self.log.error("Media not configured, unloading plugin.")
            self.unload(ctx)
            return

        for channel, feed_list in dict(bot_config.media.rss).items():
            for feed in feed_list:
                if not self.rss_config.get(feed):
                    self.rss_config[feed] = [channel]
                else:
                    self.rss_config[feed].append(channel)

        self.log.info(f"Loaded {len(self.rss_config)} RSS Feeds")

        try:
            with open('data/rss_cache.json', 'r') as f:
                self.rss_cache = json.load(f)
        except FileNotFoundError:
            pass

        self.loading = False

        super(MediaPlugin, self).load(ctx)

    def unload(self, ctx):

        # Skip the extra IO is not needed.
        if self.rss_cache == {}:
            return super(MediaPlugin, self).unload(ctx)

        self.log.info("Saving rss news cache")
        with open('data/rss_cache.json', 'w') as f:
            json.dump(self.rss_cache, f)

        return super(MediaPlugin, self).unload(ctx)

    # Time in seconds
    # TODO: Refactor.
    @Plugin.schedule(300)
    def check_rss(self):

        def pubdate_to_timestamp(pub_date):
            return int(parser.parse(pub_date).timestamp())

        def sort_post_by_published(e):
            return pubdate_to_timestamp(e['published'])

        for feed_url in self.rss_config.keys():
            feed = feedparser.parse(feed_url)

            if not feed.get('entries') or len(feed['entries']) == 0:
                continue

            unsorted_feed = [entry for entry in feed['entries'] if entry.get('published')]

            if len(unsorted_feed) == 0:
                continue

            sorted_feed = sorted(unsorted_feed, key=sort_post_by_published, reverse=True)

            domain = urlparse(sorted_feed[0]['link']).netloc

            if pubdate_to_timestamp(sorted_feed[0]['published']) < int(datetime.now().timestamp() - 3600):
                continue

            if domain in self.rss_cache:
                if self.rss_cache[domain] == sorted_feed[0]['link']:
                    continue
                else:
                    self.rss_cache[domain] = sorted_feed[0]['link']
            else:
                self.rss_cache[domain] = sorted_feed[0]['link']

            author = None
            if 'author_detail' in sorted_feed[0].keys():
                author = f" by: {sorted_feed[0]['author_detail']['name']}"

            title = re.sub("<[^>]*>", "", sorted_feed[0]['title'], count=0, flags=0)

            timestamp = pubdate_to_timestamp(sorted_feed[0]['published'])

            content = f"📰 | **{title}**{author or ''} (<t:{timestamp}:R>)\n\n** [Click To Read on *{domain}*]({sorted_feed[0]['link']}) **"

            for channel in self.rss_config[feed_url]:
                msg = self.bot.client.api.channels_messages_create(channel, content=content)
                # TODO: Maybe auto publish?
                # If wanted to use announcement channels and have the bot auto-publish articles
                # try:
                #     self.bot.client.api.channels_messages_publish(channel, msg.id)
                # except:
                #     continue


