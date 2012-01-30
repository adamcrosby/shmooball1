from flask import Flask
app = Flask(__name__, template_folder='/www/code/templates')
app.debug = False

import shmooball.views
