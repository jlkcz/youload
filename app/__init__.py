import os
import time
import sqlite3
import datetime
from operator import attrgetter
from pprint import pprint
from flask import Flask, render_template, redirect, url_for, flash, request, send_from_directory, g
from flask_bootstrap import Bootstrap4
from flask_wtf import FlaskForm
from flask_simplelogin import SimpleLogin, login_required
from wtforms import TextAreaField, SelectField, SubmitField
from wtforms.validators import DataRequired
import yt_dlp as youtube_dl
from yt_dlp.utils import DownloadError
from uwsgi_tasks import task, TaskExecutor

app = Flask(__name__)
app.config.from_pyfile('../config.py')
app.config["DOWNLOADED_DIR"] = os.path.join(os.path.dirname(os.path.realpath(__file__)), "../downloaded")


bootstrap = Bootstrap4(app)
SimpleLogin(app)

##### YT-DLP settings ####

#For log collection
class MyLogger(object):
    def __init__(self):
        self.lines = []

    def debug(self, msg):
        self.lines.append(msg)

    def warning(self, msg):
        self.lines.append(msg)

    def error(self, msg):
        self.lines.append(msg)

    def get_log(self):
        return "\n".join(self.lines)

#for filename collection
class FilenameCollectorPP(youtube_dl.postprocessor.common.PostProcessor):
    def __init__(self):
        super(FilenameCollectorPP, self).__init__(None)
        self.filenames = []

    def run(self, information):
        self.filenames.append(information['filepath'])
        return [], information

ydl_opts_audio = {
    'format': 'bestaudio/best',
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '256',
    }],
    'restrictfilenames': True,
    'nooverwrites': True,
}

ydl_opts_video = {
    'format': 'bestvideo+bestaudio/best',
    'restrictfilenames': True,
    'nooverwrites': True,
}

##### DB helpers for Flask #####

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect('app.db')
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

## Download Form for WTF

class DownloadForm(FlaskForm):
    urls = TextAreaField('URL adresy videa', validators=[DataRequired()])
    filetype = SelectField('Formát', choices={'mp3':'mp3', 'video':'video'})
    submit = SubmitField('Stáhnout videa', render_kw={'class': 'btn btn-primary btn-lg'})


#actual task for downloading
@task(executor=TaskExecutor.AUTO)
def run_downloader():
    os.chdir(app.config["DOWNLOADED_DIR"])
    con = get_db()
    cur = con.cursor()
    cur.execute("SELECT * FROM urls WHERE state IS NULL ORDER BY id")
    to_download = cur.fetchall()
    for item in to_download:
        if item["audio"] == 1:
            ydl_opts = ydl_opts_audio
        else:
            ydl_opts = ydl_opts_video

        filename_collector = FilenameCollectorPP()
        logger = MyLogger()
        ydl_opts["logger"] = logger
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            ydl.add_post_processor(filename_collector)
            try:
                ydl.download([item["url"]])
            except DownloadError:
                cur.execute("UPDATE urls SET state=1, errorlog=? WHERE id=?", (logger.get_log(),item["id"]))
                continue
            for filename in filename_collector.filenames:
                cur.execute("INSERT INTO files (url, filename) VALUES (?,?)", (item["id"], filename))
            cur.execute("UPDATE urls SET state=0 WHERE id=?", (item["id"],))
    con.commit()
    return True

#### Routes ####

@app.route('/', methods=["GET","POST"])
@app.route('/index', methods=["GET","POST"])
@login_required
def index():
    con = get_db()
    cur = con.cursor()
    form = DownloadForm()
    if form.validate_on_submit():
        audio = 0
        if form.filetype.data == "mp3":
            audio = 1
        insert_data = [(url, audio) for url in form.urls.data.splitlines()]
        cur.executemany("INSERT INTO urls (url, audio) VALUES (?,?)", insert_data)
        con.commit()
        run_downloader()
        flash(f'Stahování {len(insert_data)} videí úspěšně spuštěno', 'success')
        return redirect(url_for('index'))
    return render_template('index.html', form=form)


@app.route("/list")
@login_required
def list():
    cur = get_db().cursor()
    cur.execute("SELECT id,url,audio,state,created_at, (SELECT group_concat(filename, ';') FROM files WHERE urls.id=files.url) AS files FROM urls ORDER BY id DESC")
    rows = cur.fetchall()
    return render_template('list.html', items=rows)

@app.route("/errorlog/<int:urlid>")
@login_required
def errorlog(urlid):
    cur = get_db().cursor()
    cur.execute("SELECT * FROM urls WHERE id=?", (urlid, ))
    row = cur.fetchone()
    return render_template('errorlog.html', row=row)

@app.route("/down/<filename>")
@login_required
def down(filename):
    directory = app.config["DOWNLOADED_DIR"]
    return send_from_directory(
        directory, filename, as_attachment=True
    )

@app.route("/redownload/<int:urlid>")
@login_required
def redownload(urlid):
    con = get_db()
    cur = con.cursor()
    cur.execute("INSERT INTO urls (url, audio) SELECT url, audio FROM urls WHERE id=?", (urlid, ))
    con.commit()
    run_downloader()
    flash(f'Znovustahování úspěšně spuštěno', 'success')
    return redirect(url_for('list'))

