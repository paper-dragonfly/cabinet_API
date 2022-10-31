from sqlite3 import sqlite_version
import psycopg2
import yaml
import os
import pdb

ENV = os.getenv('ENV')


def get_conn_str(env:str=ENV, config_file:str='config/config.yaml') ->str:
    with open(f'{config_file}', 'r') as f:
        config_dict = yaml.safe_load(f)
    conn_str = config_dict[env]['conn_str']
    return conn_str

def db_connect(env:str=ENV, autocommit:bool=True) ->tuple:
    conn_str = get_conn_str(env)
    conn = psycopg2.connect(conn_str)
    cur = conn.cursor()
    conn.autocommit = autocommit
    return conn, cur 

def get_env_host(env:str=ENV, config_file:str='config/config.yaml')->str:
    with open(f'{config_file}', 'r') as f:
        config_dict = yaml.safe_load(f)
    env_host = config_dict[env]['host']
    return env_host


def add_blob(blob_bytes:str, env:str=ENV) -> int:
    try:
        conn, cur = db_connect(env)
        cur.execute('INSERT INTO blob (bytes) VALUES (%s)', (f'{blob_bytes}',))
        cur.execute('SELECT MAX(blob_id) FROM blob')
        blob_id = cur.fetchone()[0]
    finally:
        cur.close()
        conn.close()
        return blob_id


def build_insert_query(table:str, metadata:dict) -> tuple:
    # generate str of column names
    columns:list = metadata.keys()
    col_str = ""
    for i in columns:
        col_str += i + ', '
    col_str = col_str[0:-2]
    # generate str of entry metadata values
    entry_vals = tuple(metadata.values())
    # generate %s str of correct length
    s = ("%s,"*len(entry_vals))[0:-1]
    # create query
    sql = f'INSERT INTO {table}({col_str}) VALUES({s})'
    return sql, entry_vals


def add_entry(table:str, metadata:dict, cur, env:str=ENV)->int:
    sql_query, entry_vals = build_insert_query(table, metadata)
    cur.execute(sql_query, entry_vals)
    cur.execute(f'SELECT MAX(entry_id) FROM {table}') 
    entry_id = cur.fetchone()[0] 
    return entry_id


def get_column_names(table:str, cur, env:str=ENV) -> list: 
    cur.execute(f'SELECT * FROM {table}')
    col_names = [desc[0] for desc in cur.description]
    return col_names
    

def get_current_metadata(table:str, entry_id:int, cur, env:str=ENV)-> dict:
    s_sub = '%s'
    cur.execute(f"SELECT * FROM {table} WHERE entry_id = {s_sub}", (entry_id,))
    old_metadata_vals: list= list(cur.fetchone())
    col_names:list = get_column_names(table, cur)
    old_metadata = {}
    for i in range(len(col_names)):
        old_metadata[f'{col_names[i]}'] = old_metadata_vals[i]
    return old_metadata


def make_full_update_dict(updates:dict, old_metadata:dict):
    full_update = updates 
    for key in old_metadata.keys():
        if not key in full_update:
            full_update[key]=old_metadata[key]
    full_update.pop('entry_id', 'No entry_id key') #or use del ?
    return full_update

 