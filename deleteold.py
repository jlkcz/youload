#!/usr/bin/env python3

import datetime
import os
import sqlite3

con = sqlite3.connect("app.db")
con.row_factory = sqlite3.Row
cur = con.cursor()

day_ago = datetime.datetime.now() - datetime.timedelta(days=1)
cur.execute(
    "SELECT urls.id as id, filename FROM urls LEFT JOIN files ON urls.id=files.url WHERE created_at < ? AND state != 99",
    (day_ago,),
)
rows = cur.fetchall()
os.chdir(os.path.join(os.path.dirname(os.path.realpath(__file__)), "downloaded"))
for file in rows:
    print(f"Setting state=99 for ID: {file['id']}")
    cur.execute("UPDATE urls SET state=99 WHERE id=?", (file["id"],))
    print(f"Removing file {file['filename']}")
    os.remove(file["filename"])
con.commit()
