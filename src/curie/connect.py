# Author: Eric DiGioacchino
import imp
import logging as log
import re
import os
import subprocess
import pandas as pd
# import display for jupyter notebooks
try:
    from IPython.display import display
except:
    pass

    
class Database:
    def __init__(self, host, port:int, user, password, database, **kwargs):
        self.host_ = host
        try:
            self.port_ = None if port == '' else int(port)
        except:
            self.port_ = None
        self.user_ = user
        self.password_ = password
        self.database_ = database
        self.kwargs_ = kwargs
        self.reminder_ = None
    def __repr__(self) -> str:
        return "Database(host={}, port={}, user={}, password={}, database={}, kwargs={})".format(self.host_, self.port_, self.user_, self.password_, self.database_, self.kwargs_)
    
    def raise_error(self, e):
        if 'reminder' in self.kwargs_:
            log.error(self.kwargs_['reminder'])
        log.error(e)
        return None
    
class Redshift(Database):
    def __init__(self, host, port, user, password, database, **kwargs):
        super().__init__(host, port, user, password, database, **kwargs)

        if 'defer_import' in kwargs:
            self.defer_import_ = kwargs['defer_import']
            del self.kwargs_['defer_import']
            try:
                self.defer_import_ = bool(self.defer_import_)
            except:
                log.warn("Warning: defer_import must be a boolean value. Defaulting to False.")
                self.defer_import_ = False

        if hasattr(self, 'defer_import_') and self.defer_import_:
            self.__defered_import()
        self.__validate_imports()

        if 'reminder' in kwargs:
            self.reminder_ = kwargs['reminder']

        delfrom = ['secrets', 'reminder', 'defer_import']
        for key in delfrom:
            if key in self.kwargs_:
                del self.kwargs_[key]

    def __defered_import(self):
        global redshift_connector
        import redshift_connector
    
    def __validate_imports(self):
        # check if psycopg2 and redshift_connector are installed
        try:
            return all([imp.find_module('redshift_connector')])
        except ImportError:
            return False

    def connect(self, help=False):
        # use global variables to connect to redshift
        try:
            self.conn_ = redshift_connector.connect(host=self.host_, port=self.port_, user=self.user_, password=self.password_, database=self.database_, **self.kwargs_)
            log.info("Connected to Redshift...")
            if help:
                print("\n\nExample Usage:\n\nconn = Curie(*args).this_connection.connect()\ncursor = conn.cursor()\ncursor.execute('SELECT * FROM table')\nresults = cursor.fetchall()\n\n")
            return self.conn_
        except Exception as e:
            if self.reminder_:
                log.error("REMINDER: " + self.reminder_)
            log.error("Error: Could not connect to Redshift. Check your credentials.")
            log.error(e.with_traceback())
            return None

    def __repr__(self):
        return "Redshift(host={}, port={}, user={}, database={}, kwargs={})".format(self.host_, self.port_, self.user_, self.database_, self.kwargs_)
    
    def method_patterns(self):
        return {
            'seed': lambda q: [q],
            'replace': lambda q: ['DROP TABLE IF EXISTS {{this}}', 'CREATE TABLE {{this}} AS (' + q + ')'],
            'truncate': lambda q: ['TRUNCATE TABLE {{this}}', 'INSERT INTO {{this}} (' + q + ')'],
        }
    
    def execute(self, query, **kwargs):
        self.results_ = None
        self.conn_ = self.connect()
        self.conn_.autocommit = True
        if self.conn_ is None:
            return None
        cursor = self.conn_.cursor()
        try:
            cursor.execute(query)
        except Exception as e:
            print(query)
            raise e
        # if 'store_results' in kwargs and kwargs['store_results']:
        if cursor.description is not None:
            results = cursor.fetch_dataframe()
            self.results_ = results
        cursor.close()
        self.conn_.close()
        return self.results_

    def test(self):
        try:
            self.conn_ = self.connect()
            self.conn_.close()
            return True
        except Exception as e:
            log.error(e.with_traceback())
            return False
        
class MySQL(Database):
    def __defered_import(self):
        global mysql_connector
        import mysql.connector as mysql_connector
    
    def __validate_imports(self):
        # check if psycopg2 and redshift_connector are installed
        try:
            return all([imp.find_module('mysql_connector')])
        except ImportError:
            return False
    
    def __init__(self, host, port, user, password, database, **kwargs):
        super().__init__(host, port, user, password, database, **kwargs)

        if 'defer_import' in kwargs:
            self.defer_import_ = kwargs['defer_import']
            del self.kwargs_['defer_import']
            try:
                self.defer_import_ = bool(self.defer_import_)
            except:
                log.warn("Warning: defer_import must be a boolean value. Defaulting to False.")
                self.defer_import_ = False

        if hasattr(self, 'defer_import_') and self.defer_import_:
            self.__defered_import()
        self.__validate_imports()

        if 'reminder' in kwargs:
            self.reminder_ = kwargs['reminder']

        delfrom = ['secrets', 'reminder', 'defer_import']
        for key in delfrom:
            if key in self.kwargs_:
                del self.kwargs_[key]
    
    def connect(self):
        # use global variables to connect to redshift
        try:
            self.conn_ = mysql_connector.connect(host=self.host_, port=self.port_, user=self.user_, password=self.password_, database=self.database_, **self.kwargs_)
            log.info("Connected to MySQL...")
            return self.conn_
        except Exception as e:
            if self.reminder_:
                log.error("REMINDER: " + self.reminder_)
            log.error("Error: Could not connect to MySQL. Check your credentials.")
            log.error(e.with_traceback())
            return None
    
    def __repr__(self):
        return "MySQL(host={}, port={}, user={}, database={}, kwargs={})".format(self.host_, self.port_, self.user_, self.database_, self.kwargs_)
    
    def method_patterns(self):
        return {
            'seed': lambda q: [q],
            'replace': lambda q: ['DROP TABLE IF EXISTS {{this}}', 'CREATE TABLE {{this}} AS (' + q + ')'],
            'truncate': lambda q: ['TRUNCATE TABLE {{this}}', 'INSERT INTO {{this}} (' + q + ')'],
        }
    
    def execute(self, query, **kwargs):
        self.results_ = None
        self.conn_ = self.connect()
        self.conn_.autocommit = True
        if self.conn_ is None:
            return None
        cursor = self.conn_.cursor()
        try:
            cursor.execute(query)
        except Exception as e:
            print(query)
            raise e
        # if 'store_results' in kwargs and kwargs['store_results']:
        if cursor.description is not None:
            rows = cursor.fetchall()
            columns = [i[0] for i in cursor.description]
            self.results_ = pd.DataFrame(rows, columns=columns)
        cursor.close()
        self.conn_.close()
        return self.results_
    
    def test(self):
        try:
            self.conn_ = self.connect()
            self.conn_.close()
            return True
        except Exception as e:
            log.error(e.with_traceback())
            return False  