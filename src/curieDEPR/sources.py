# Author: Eric DiGioacchino
import imp
import logging as log
import re
import os
import subprocess

    
class Database:
    def __init__(self, host, port:int, user, password, database, **kwargs):
        self.host_ = host
        self.port_ = None if port == '' else int(port)
        self.user_ = user
        self.password_ = password
        self.database_ = database
        self.kwargs_ = kwargs

    def __repr__(self) -> str:
        return "Database(host={}, port={}, user={}, password={}, database={}, kwargs={})".format(self.host_, self.port_, self.user_, self.password_, self.database_, self.kwargs_)
    

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

        if self.defer_import_:
            self.__defered_import()
        self.__validate_imports()
        pass

    def __defered_import(self):
        global redshift_connector
        import redshift_connector
    
    def __validate_imports(self):
        # check if psycopg2 and redshift_connector are installed
        try:
            return all([imp.find_module('redshift_connector')])
        except ImportError:
            raise ImportError("Error: Could not import redshift_connector. Please install redshift_connector using 'pip install redshift_connector'.")

    def connect(self, help=False):
        # use global variables to connect to redshift
        try:
            self.conn_ = redshift_connector.connect(host=self.host_, port=self.port_, user=self.user_, password=self.password_, database=self.database_, **self.kwargs_)
            log.info("Connected to Redshift...")
            if help:
                print("\n\nExample Usage:\n\nconn = Curie(*args).this_connection.connect()\ncursor = conn.cursor()\ncursor.execute('SELECT * FROM table')\nresults = cursor.fetchall()\n\n")
            return self.conn_
        except Exception as e:
            log.error("Error: Could not connect to Redshift. Check your credentials.")
            log.error(e)
            return None

    def __repr__(self):
        return "Redshift(host={}, port={}, user={}, password={}, database={}, kwargs={})".format(self.host_, self.port_, self.user_, self.password_, self.database_, self.kwargs_)
    
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
        cursor.execute(query)
        if 'mode' in kwargs and kwargs['mode'] == 'save':
            results = cursor.fetch_dataframe()
            self.results_ = results
        cursor.close()
        self.conn_.close()
        return self.results_

class MySQL(Database):
    def __init__(self, host, port, user, password, database, **kwargs):
        super().__init__(host, port, user, password, database, **kwargs)

        if 'defer_import' in kwargs:
            self.defer_import_ = kwargs['defer_import']
            try:
                self.defer_import_ = bool(self.defer_import_)
            except:
                log.warn("Warning: defer_import must be a boolean value. Defaulting to False.")
                self.defer_import_ = False

        if self.defer_import_:
            self.__defered_import()
        self.__validate_imports()
        pass

    def __defered_import(self):
        global mysql
        import mysql
    
    def __validate_imports(self):
        # check if psycopg2 and redshift_connector are installed
        try:
            return all([imp.find_module('mysql')])
        except ImportError:
            raise ImportError("Error: Could not import mysql. Please install mysql using 'pip install mysql'.")

    def connect(self):
        # use global variables to connect to redshift
        try:
            del self.kwargs_['defer_import']
            self.conn_ = mysql.connector.connect(host=self.host_, port=self.port_, user=self.user_, password=self.password_, database=self.database_, **self.kwargs_)
            return self.conn_
        except Exception as e:
            log.error("Error: Could not connect to Redshift. Check your credentials.")
            log.error(e)
            return None
    
class MongoDB(Database):
    def __init__(self, **kwargs):
        pass

