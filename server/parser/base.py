#!/usr/bin/env python

class BaseEpisode:
    def __init__(self, data):
        self.data = data
        self.title = None
        self.id = None
        self.link = None
        self.media_url = None
        self.media_duration = None
        self.media_size = None
        self.publication_date = None


class BaseParser:
    def __init__(self):
        self.title = None
        self.author = None
        self.image = None
        self.episodes = None
