import os
import time
import datetime
from operator import attrgetter
from pprint import pprint
from flask import Flask, render_template, redirect, url_for, flash, request, send_file
from flask_bootstrap import Bootstrap
from flask_wtf import FlaskForm
from wtforms import SelectField, SubmitField
from wtforms.validators import DataRequired
from wtforms.fields.html5 import URLField
from werkzeug.utils import secure_filename
import youtube_dl 
from uwsgi_tasks import task, TaskExecutor

app = Flask(__name__)
app.config.from_pyfile('../config.py')
app.config['SECRET_KEY'] = 'veryrandomstringindeed'

bootstrap = Bootstrap(app)

ydl_opts = {
    'format': 'bestaudio/best',
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
    }],
    'quiet': True,
    'restrictfilenames': True,
    'nooverwrites': True,
}

class DownloadForm(FlaskForm):
    url = URLField('WWW adresa videa', validators=[DataRequired()])
    location = SelectField('Kam uložit', choices=app.config['DOWNLOAD_DIRS'].keys(), validators = [DataRequired()])
#    filetype = SelectField('Formát', choices={'mp3':'mp3', 'video':'video'})
    submit = SubmitField('Uložit video', render_kw={'class': 'btn btn-primary btn-lg'})

@task(executor=TaskExecutor.AUTO)
def download(url, full_dir):
    os.chdir(full_dir)
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    return True
 
@app.route('/', methods=["GET","POST"])
@app.route('/index', methods=["GET","POST"])
def index():
    form = DownloadForm()
    if form.validate_on_submit():
        target_dir = app.config['DOWNLOAD_DIRS'][form.location.data]
        full_dir = app.config['WORKING_DIR'] + '/' + target_dir
        download(form.url.data, full_dir)
        flash(f'Video úspěšně staženo do {target_dir}', 'success')
        return redirect(url_for('index'))
    return render_template('index.html', form=form)

