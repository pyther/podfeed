from flask import Flask
from flask_caching import Cache

app = Flask(__name__)
app.debug = True
app.config['CACHE_TYPE'] = 'simple'

app.cache = Cache(app)

from app import views
