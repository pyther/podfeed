#!/usr/bin/env python
from .base import BaseParser, BaseEpisode

import base64
import json
import re
import datetime
import pytz
from bs4 import BeautifulSoup


class NprEpisode(BaseEpisode):
    def __init__(self, data, publication_time=(12, 0)):
        super(NprEpisode).__init__()
        self.data = data
        self.title = data['title']
        self.id = data['uid']
        self.link = data['storyUrl']
        self.media_duration = data['duration']
        self.publication_time = publication_time

    def get_audio_url(self):
        audio_url = self.data['audioUrl']
        if not audio_url.startswith('http'):
            audio_url = base64.b64decode(audio_url).decode('utf-8')
        return audio_url

    @property
    def media_url(self):
        audio_url = self.get_audio_url()
        return audio_url.split('?', 1)[0]

    def get_url_query(self):
        audio_url = self.get_audio_url()
        audio_query = audio_url.split('?', 1)[1]
        return {k: v for k, v in (x.split('=', 1) for x in audio_query.split('&'))}

    @property
    def media_size(self):
        try:
            size = self.get_url_query()['size']
        except KeyError:
            size = 0
        return size

    @property
    def publication_date(self):
        # The media_url contain the publication date in the filename, ex:
        # 20230917_wesun_ukraine_step-back.mp3. Recently, some media_urls do
        # not have the publication date, ex: NPR7011631224.mp3. Fallback, to
        # the story_url to obtain the publication date.

        media_match = re.match(r'.*/(\d{4})(\d{2})(\d{2}).*\.mp3', self.media_url)
        story_match = re.match(r'.*/(\d{4})/(\d{2})/(\d{2})/', self.link)
        if media_match:
            year, month, day = media_match.groups()
        elif story_match:
            year, month, day = story_match.groups()
        else:
            raise ValueError(f'Unable to determine publication date from {self.media_url} or {self.story_url}')

        date = datetime.date(int(year), int(month), int(day))
        time = datetime.time(*self.publication_time)
        dt = datetime.datetime.combine(date, time)
        return pytz.timezone('America/New_York').localize(dt)


class NprParser(BaseParser):
    def __init__(self, data, name, publication_time='12:00'):
        super(NprParser).__init__()
        self.soup = BeautifulSoup(data, features="html.parser")
        self.name = name
        self.__publication_time = self.extract_pub_time(publication_time)

    @property
    def title(self):
        return [x.strip() for x in self.soup.title.text.split(':')][0]

    @property
    def author(self):
        return [x.strip() for x in self.soup.title.text.split(':')][1]

    @property
    def image(self):
        # See if we can find a logo based on name
        try:
            return self.soup.findAll('img', {"src": re.compile(f"logos.*{self.name}")})[0]['src']
        except IndexError:
            pass

        try:
            return self.soup.findAll('img', {"class": "branding__image-title"})[0]['src']
        except IndexError:
            pass

        return None

    def extract_pub_time(self, time):
        hour, minute = time.split(':', 1)
        return (int(hour), int(minute))

    @property
    def episodes(self):
        results = []

        # Daily Stories
        storylist = self.soup.find("div", {"id": "story-list"}).findAll("div", attrs={'data-audio': True})
        for story in storylist:
            segment = json.loads(story.get('data-audio'))
            results.append(NprEpisode(segment, publication_time=self.__publication_time))

        # Full Episodes (previous days)
        program_shows = self.soup.findAll('article', {"class": "program-show"})
        play_all = [show.find(attrs={'data-play-all': True}) for show in program_shows]
        data_all = [json.loads(x.get('data-play-all')) for x in play_all]
        for show in data_all:
            for segment in show['audioData']:
                results.append(NprEpisode(segment, publication_time=self.__publication_time))
        return results
