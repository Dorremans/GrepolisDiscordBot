import sqlite3
import datetime
import sys
sys.path.append(".")

class sqliteDatabaseHandler():
        def __init__(self, database):
                self.database = database
                self.con = sqlite3.connect(self.database)

        def connection_timeout_error_handler():
                def wrapper(self, *args, **kwargs):
                        try:
                                func(*args, **kwargs)
                        except sqlite3.Error:
                                self.con.close()
                                self.con = sqlite3.connect(self.database)
                return wrapper


        def connectCommitClose(func):
                def wrapper(self, *args, **kwargs):
                        cur = self.con.cursor()

                        insertQuery, values = func(*args, **kwargs)
                        if values == None:
                                cur.execute(insertQuery)
                        else:
                                cur.execute(insertQuery, values)
                        self.con.commit()
                return wrapper

        def connectFetchClose(func):
                def wrapper(self, *args, **kwargs):
                        cur = self.con.cursor()

                        insertQuery = func(*args, **kwargs)

                        cur.execute(insertQuery)
                        rows = cur.fetchall()
                        return rows
                return wrapper
        
        def clearTable(self, table_name):
                cur = self.con.cursor()

                insertQuery = f'''DELETE FROM {table_name}'''

                cur.execute(insertQuery)
                self.con.commit()

        def clearAllTables(self):
                self.clearTable('offence')
                self.clearTable('banned_users')

        @connectCommitClose
        def insertsettingsQuery(guild_id, setting_type, set_value):
                insertQuery = '''INSERT INTO settings (guild_id, 
                                        setting_type, 
                                        set_value)
                                VALUES (?, 
                                        ?,
                                        ?);'''
                values = (guild_id, setting_type, set_value)
                return insertQuery, values

        @connectCommitClose
        def insertbannedUsersQuery(guild_id, user_id, unban_time):
                insertQuery = '''INSERT INTO banned_users (guild_id, 
                                        user_id, 
                                        unban_time)
                                VALUES (?, 
                                        ?,
                                        ?);'''
                values = (guild_id, user_id, unban_time)
                return insertQuery, values

        @connectCommitClose
        def insertOffenceQuery(guild_id, user_id, moderator_id, penalty_points, reason, autoban=None):
                if autoban == None:
                        banned = 0
                else:
                        banned = 1
                insertQuery = f'''INSERT INTO offence (datetime, 
                                        guild_id,
                                        user_id,
                                        moderator_id,
                                        penalty_points,
                                        autoban,
                                        reason,
                                        banned)
                                VALUES (?, 
                                        ?,
                                        ?,
                                        ?,
                                        ?,
                                        ?,
                                        ?,
                                        {banned});'''
                values = (datetime.datetime.now(), guild_id, user_id, moderator_id, penalty_points, autoban, reason)
                return insertQuery, values

        
        @connectFetchClose
        def _sumPenaltyPointsQuery(user_id):
                insertQuery = f'''SELECT SUM(penalty_points)
                                FROM offence
                                WHERE user_id == {user_id}
                
                
                                '''
                return insertQuery

        @connectFetchClose
        def getBansPassed():
                time = datetime.datetime.now()
                insertQuery = f'''SELECT user_id FROM offence
                                WHERE autoban < '{time}' AND banned = 1
                                '''
                return insertQuery

        @connectFetchClose
        def getOffenceMember(user_id):
                insertQuery = f'''SELECT * FROM offence
                                WHERE user_id = {user_id}
                                '''
                return insertQuery

        @connectFetchClose
        def getOffence(offence_id):
                insertQuery = f'''SELECT * FROM offence
                                WHERE offence_id = {offence_id}
                                '''
                return insertQuery

        @connectCommitClose
        def changeBannedState(user_id):
                insertQuery = f'''UPDATE offence SET banned = 0 WHERE user_id = {user_id}'''
                values = None
                return insertQuery, values

        @connectCommitClose
        def removeOffence(offence_id):
                insertQuery = f'''DELETE FROM offence WHERE offence_id = {offence_id}'''
                values = None
                return insertQuery, values

        @connectFetchClose
        def getUserIDBanned(offence_id):
                insertQuery = f'''SELECT user_id FROM offence WHERE offence_id = {offence_id} AND banned = 1'''
                return insertQuery

        def sumPenaltyPoints(self, user_id):
                rows = self._sumPenaltyPointsQuery(user_id)
                if rows[0][0] == None:
                        return 0
                else:
                        return rows[0][0]

        @connectCommitClose
        def editPenaltyPoints(offence_id, penalty_points):
                insertQuery = f'''UPDATE offence SET penalty_points = {penalty_points} WHERE offence_id = {offence_id}'''
                values = None
                return insertQuery, values

        @connectCommitClose
        def editBanTime(offence_id, new_time):
                insertQuery = f'''UPDATE offence SET autoban = ? WHERE offence_id = {offence_id}'''
                values = (new_time, )
                return insertQuery, values
        

if __name__ == '__main__':
        import pathlib
        import os
        database_path = pathlib.PurePath(__file__).parents[1].joinpath('moderation.db')
        database = sqliteDatabaseHandler(database_path)
        user_id = database.getBansPassed()
        print(user_id)



