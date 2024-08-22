This is a simple yt-dlp web based frontend, based on flask. It supports downloading files to a server running Youload from any source yt-dlp is able to download from and keeping it there for a set length of time. All behind basic password
![image](https://github.com/user-attachments/assets/9315b27b-14a7-44fc-a822-912c715dea02)

![image](https://github.com/user-attachments/assets/1de97b04-56f4-4232-a32f-2798d196515d)



# Installation instructions
1. git clone this repository
2. Create virtualenv: `python3 -m venv venv`
3. Activate virtualenv `. venv/bin/activate`
4. install dependencies: pip install -r requirements.txt
5. Make sure you have `ffmpeg` installed in `PATH`
6. create downloaded folder in top folder: `mkdir downloaded`
7. create database file: `cat database.sql | sqlite3 app.db`
8. copy `config.example.py` to `config.py` and edit for setting username/password and secret key
9. try running it by Flask to verify everything is working: `FLASK_DEBUG=True flask run`
10. Deploy using uwsgi, it counts on using uwsgi mules
11. Set cron to run `deleteold.py` to keep sane amount of old entries


