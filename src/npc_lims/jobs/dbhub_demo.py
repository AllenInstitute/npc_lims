import os
import pathlib
import sqlite3

from pydbhub import dbhub

db_file = pathlib.Path('jobs.db')
db_file.unlink(missing_ok=True)

db = sqlite3.connect(db_file.as_posix())

drop_table = "DROP TABLE IF EXISTS {table};"
rename_table = "ALTER TABLE {existing} RENAME TO {new};"
create_table = """
CREATE TABLE IF NOT EXISTS {table}(
    session_id TEXT PRIMARY KEY,
    priority INTEGER DEFAULT 0,
    added DATETIME DEFAULT (datetime('now','utc', '-7 hours')),
    started DATETIME DEFAULT NULL,
    hostname TEXT DEFAULT NULL,
    finished BOOLEAN DEFAULT FALSE,
    error TEXT DEFAULT NULL
    );
"""
insert_test_values = "INSERT INTO {table} (session_id, priority) VALUES ('test1', 1);"

get_tables = "SELECT name FROM sqlite_master WHERE type='table';"
select = "SELECT * FROM {table};"

# %%
template_table_name = '_template'

cur = db.cursor()

db.commit()
cur.execute(drop_table.format(table=template_table_name))
cur.execute(create_table.format(table=template_table_name))
cur.execute(create_table.format(table='jobs_1'))
cur.execute(create_table.format(table='jobs_2'))
cur.execute(insert_test_values.format(table=template_table_name))
cur.execute(insert_test_values.format(table='jobs_1'))
cur.execute(insert_test_values.format(table='jobs_2'))
db.commit()
cur.execute(select.format(table=template_table_name))
print(cur.fetchall())

#%% Create a view across tables to give status of all sessions in all jobs
tables = [_[0] for _ in cur.execute(get_tables).fetchall()]
tables.remove(template_table_name)

view_select = (
    f"SELECT {template_table_name}.session_id, "
    f"{', '.join([table + '.finished AS ' + table for table in tables])}\n"
)

view_join = (
    f"FROM {template_table_name}\n"
    + '\n'.join([f"FULL JOIN {table} ON {template_table_name}.session_id = {table}.session_id" for table in tables])
)
view_join = (
    f"FROM {template_table_name}\n"
    + '\n'.join([f"CROSS JOIN {table}" for table in tables])
)
create_view_across_tables = (
    "CREATE VIEW IF NOT EXISTS {view} AS\n" +
    view_select + view_join + f"\nGROUP BY {template_table_name}.session_id" +';'
)
view_name = 'status'

db.commit()
cur.execute(create_view_across_tables.format(view=view_name))
cur.execute(select.format(table=view_name))

print(cur.fetchall())


#%%

DB_OWNER = os.environ['DBHUB_DB_OWNER']
DB_NAME = os.environ['DBHUB_JOB_DB_NAME']
API_KEY = os.environ['DBHUB_API_KEY']

CONFIG_DATA = f"""
[dbhub]
db_owner = {DB_OWNER}
db_name = {DB_NAME}
api_key = {API_KEY}
"""

# # Create a connection to pydbhub
connection = dbhub.Dbhub(CONFIG_DATA)

import functools

execute = functools.partial(connection.Execute, DB_OWNER, DB_NAME)
query = functools.partial(connection.Query, DB_OWNER, DB_NAME)

execute(
    "UPDATE jobs_1 SET finished = datetime('now', 'utc', '-7 hours') WHERE session_id = 'test1';",
)

execute(
    "INSERT INTO jobs_2 (session_id) VALUES ('test2');"
)

execute(f'DROP VIEW IF EXISTS {view_name}')
execute(create_view_across_tables.format(view=view_name))

response = query(
    select.format(table=view_name)
)
print(response)
