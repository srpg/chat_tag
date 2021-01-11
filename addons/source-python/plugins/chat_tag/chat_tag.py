import os, path
from events import Event
from commands.say import SayFilter
from core import echo_console, SOURCE_ENGINE
from sqlite3 import dbapi2 as sqlite
from players.entity import Player
from players.helpers import index_from_userid, userid_from_index
from menus import ListMenu, Text
from filters.players import PlayerIter
from colors import Color
from messages import SayText2


class SQLiteManager(object):
	players = []
    
	def __init__(self, path):
		self.path	= path 
		self.connection = sqlite.connect(path)
		self.connection.text_factory = str
		self.cursor	= self.connection.cursor()

		self.cursor.execute("PRAGMA journal_mode=OFF")
		self.cursor.execute("PRAGMA locking_mode=EXCLUSIVE")
		self.cursor.execute("PRAGMA synchronous=OFF")

		self.cursor.execute("""\
			CREATE TABLE IF NOT EXISTS Player (
			UserID	INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
			steamid VARCHAR(30) NOT NULL,
 			tag		    INTEGER DEFAULT 'Test',
 			color		INTEGER DEFAULT 'green',
			name	VARCHAR(30) DEFAULT 'default'
		)""")

		self.cursor.execute("CREATE INDEX IF NOT EXISTS PlayerIndex ON Player(SteamID);")

	def __del__(self):
		self.save()
		self.close()
        
	def __contains__(self, key):
		key = str(key)
		if key in self.items:
			return True
		self.execute("SELECT level FROM Player WHERE steamid=?", key)
		result = self.cursor.fetchone()
		if bool(result):
			self.players.append(key)
			return True

	def __iter__(self):
		self.execute("SELECT steamid FROM Player")
		for steamid in self.cursor.fetchall():
			yield steamid[0]

	def execute(self, parseString, *args):
		self.cursor.execute(parseString, args)

	def addPlayer(self, steamid, name):
		self.execute("INSERT INTO Player (steamid, name) VALUES (?,?)", steamid, name)
		return self.cursor.lastrowid
        

	def getUserIdFromSteamId(self, steamId):
		self.execute("SELECT UserID FROM Player WHERE steamid=?", steamId)
		value = self.cursor.fetchone()
		if value is None:
			return None
		return value[0]

	def getPlayerStat(self, userid, statType):
		if not isinstance(userid, int):
			userid = self.getUserIdFromSteamId(userid)
		statType = str(statType).replace("'", "''")
		if hasattr(statType, "__len__"):
			query = "SELECT " + ",".join( map( str, statType)) + " FROM Player WHERE UserID=?"
		else:
			query = "SELECT " + str( statType ) + " FROM Player WHERE UserID=?"
		self.execute(query, userid)
		return self.fetchone()
        
	def update(self, table, primaryKeyName, primaryKeyValue, options):
		keys = ""
		if not isinstance(options, dict):
			raise ValueError("Expected 'options' argument to be a dictionary, instead received: %s" % type(options).__name__)
		if options:
			for key, value in options.iteritems():
				if isinstance(key, str):
					key = key.replace("'", "''")
				if isinstance(value, str):
					value = value.replace("'", "''")
				keys += "%s='%s'," % (key, value)
			keys = keys[:-1]
			query = "UPDATE " + str(table) + " SET " + keys + " WHERE " + str(primaryKeyName) + "='" + str(primaryKeyValue) + "'"
			self.execute(query)

	def increment(self, table, primaryKeyName, primaryKeyValue, options):
		keys = ""
		if not isinstance(options, dict):
			raise ValueError("Expected 'options' argument to be a dictionary, instead received: %s" % type(options).__name__)
		for key, value in options.iteritems():
			if isinstance(key, str):
				key = key.replace("'", "''")
			if isinstance(value, str):
				value = value.replace("'", "''")
			keys += "%s=%s+%i," % (key, key, value)
		keys = keys[:-1]
		self.execute("UPDATE ? SET %s WHERE ?=?+?" % keys, table, primaryKeyName, primaryKeyName, primaryKeyValue)

	def fetchall(self):
		trueValues = []
		for value in self.cursor.fetchall():
			if isinstance(value, tuple):
				if len(value) > 1:
					tempValues = []
					for tempValue in value:
						if isinstance(tempValue, int):
							tempValue = int(tempValue)
						tempValues.append(tempValue)
					trueValues.append(tempValues)
				else:
					if isinstance(value[0], int):
						trueValues.append(int(value[0]))
					else:
						trueValues.append(value[0])
			else:
				if isinstance(value, int):
					value = int(value)
				trueValues.append(value)
		return trueValues

	def fetchone(self):
		result = self.cursor.fetchone()
		if hasattr(result, "__iter__"):
			if len(result) == 1:
				trueResults = result[0]
				if isinstance(trueResults, int):
					trueResults = int(trueResults)
				return trueResults
			else:
				trueResults = []
				for trueResult in result:
					if isinstance(trueResult, int):
						trueResult = int(trueResult)
					trueResults.append(trueResult)
				return trueResults
		if isinstance(result, int):
			result = int(result)
		return result    

	def save(self):
		self.connection.commit()

	def clear(self, saveDatabase = True):
		players.clearList()
		self.execute("DROP TABLE Player")
		if saveDatabase:
			self.save()
		self.__init__(self.path)
		for player in es.getUseridList():
			players.addPlayer(player)

	def close(self):
		self.cursor.close()
		self.connection.close()

class PlayerManager(object):
	def __init__(self):
		self.players = {}

	def __getitem__(self, userid):
		userid = int(userid)
		if self.__contains__(userid):
			return self.players[userid]
		return None

	def __delitem__(self, userid):
		self.removePlayer(userid)

	def __iter__(self):
		for player in self.players:
			yield self.players[player]

	def __contains__(self, userid):
		userid = int(userid)
		return bool(userid in self.players)

	def addPlayer(self, userid):
		self.players[int(userid)] = PlayerObject(userid)

	def removePlayer(self, userid):
		userid = int(userid)
		if self.__contains__(userid):
			del self.players[userid] # calls deconstructor on PlayerObject class

	def getPlayer(self, userid):
		return self.__getitem__(userid)

	def clearList(self):
		self.players.clear()

class PlayerObject(object):
	def __init__(self, userid):
		self.userid   = int(userid)
		self.steamid  = Player(index_from_userid(userid)).steamid
		self.name     = Player(index_from_userid(userid)).name
		self.isbot    = Player(index_from_userid(userid)).is_bot()
		self.currentAttributes = {}
		self.oldAttributes     = {}
		self.dbUserid = database.getUserIdFromSteamId(self.steamid)
		if self.dbUserid is None:
			self.dbUserid = database.addPlayer(self.steamid, self.name)
		self.update()
		self.playerAttributes = {}

	def __del__(self):
		self.commit()

	def __int__(self):
		return self.userid

	def __str__(self):
		return str(self.userid)

	def __getitem__(self, item):
		if item in self.currentAttributes:
			return self.currentAttributes[item]
		if item in self.playerAttributes:
			return self.playerAttributes[item]
		return None

	def __setitem__(self, item, value):
		if item in self.currentAttributes:
			self.currentAttributes[item] = value
		else:
			self.playerAttributes[item] = value

	def commit(self):
		for key, value in self.currentAttributes.items():
			if key in self.oldAttributes:
					database.execute("UPDATE Player SET %s=? WHERE UserID=?" % key, value, self.dbUserid)    
		self.oldAttributes = self.currentAttributes.copy()

	def update(self):
		database.execute("SELECT * FROM Player WHERE UserID=?", self.dbUserid)
		result = database.fetchone()
		UserID, steamid, tag, color, name = result

		for option in ('steamid', 'tag', 'color', 'name'):
			self.oldAttributes[option] = self.currentAttributes[option] = locals()[option]
# ========================================
# SINGLETONS + GLOBAL VARIABLES
# ========================================
__FILEPATH__ = path.Path(__file__).dirname()
DATABASE_STORAGE_METHOD = SQLiteManager
database = None
databasePath = os.path.join(__FILEPATH__ + '/players.sqlite')
players = PlayerManager()

def load():
	global database
	database = DATABASE_STORAGE_METHOD(databasePath)
	database.execute('VACUUM')
	echo_console('[Tag] Loaded')
	
def unload():
	savedatabase()

@SayFilter
def say_filter(command, index, teamonly):
	userid = None
	if index:
		userid = userid_from_index(index)
	
	if userid and command:
		text = command[0].replace('!', '', 1).replace('/', '', 1).lower()
		args = command.arg_string
		if text == 'tag':
			if args:
				players[userid]['tag'] = args
				tell(userid, '\x04You have changed your tag to %s[%s]' % (chat_color(players[userid]['color']), args))
				return False
		elif text == 'color':
			if args:
				if args in get_color():
					players[userid]['color'] = args
					tell(userid, '\x04You have changed your color to %s%s' % (chat_color(args), args))
				else:
					tell(userid, '\x04%s color is not avaible' % (args))
					colors(userid)
				return False
		return chat(userid, text, args, command[0] + ' ' + args)

def chat(userid, text_command, args, text):
	name = Player(index_from_userid(userid)).name
	if SOURCE_ENGINE == 'csgo':
		team_color = {1: '\x08', 2: '\x0F', 3: '\x0B'}[Player(index_from_userid(userid)).team] 
		chco = '\x01'
	else:
		naco = {1: '\x07CDCDCD', 2: '\x07FF3D3D', 3: '\x079BCDFF', 0: '\x07CDCDCD'}[Player(index_from_userid(userid)).team]
		chco = '\x07FFB300'
	tell_all('%s[%s]%s %s %s: %s' % (chat_color(players[userid]['color']), players[userid]['tag'], naco,name,chco,text))
	return False

def tell_all(message):
	message = '{}'.format(message)
	for i in getUseridList():
		tell(i, message)
					
def colors(userid):
	menu = ListMenu(
    title='Avaible Colors\n')
	for i in get_color():
		menu.append(Text('%s' % (i)))
	menu.send(index_from_userid(userid))
				
def tell(userid, text):
    SayText2(message='' + text).send(index_from_userid(userid))				

def chat_color(color_name):
	return color[color_name]

def get_color():
	return color

def getUseridList():
	for i in PlayerIter.iterator():
		yield i.userid

if SOURCE_ENGINE == 'csgo':
	color = {
		'light_blue':	'\x0A',
		'blue':			'\x0B',
		'dark_blue':	'\x0C',
		'bright_green': '\x04',
		'pale_green':	'\x05',
		'green':		'\x06',
		'grey':			'\x08',
		'orange':		'\x10',
		'purple':		'\x0E',
		'red':			'\x02',
		'pale_red':		'\x07',
		'dull_red':		'\x0F',
		'white':		'\x01',
		'yellow':		'\x09'
	}
else:
	color = {
		'darkgreen':	 '\x079EC34F',
		'lightgreen':	 '\x079BFF9B',
		'default':		 '\x07FFB300',
		'blue':			 '\x07197DFF',
		'grey':			 '\x07CECECE',
		'brown':		 '\x07D2691E',
		'silver':		 '\x07CDCDC1',
		'cyan':			 '\x0700CED1',
		'green':		 '\x073DFF3D',
		'yellow':		 '\x07FFFF00',
		'orange':		 '\x07FF4B05',
		'red':			 '\x07F82E25',
		'purple':		 '\x079400D3',
		'gold':			 '\x07FFD700',
		'platin':		 '\x07E5E4E2',
		'dark':			 '\x07191919',
		'pig':			 '\x07F4A460',
		'lightorange':	 '\x07FF9B00',
		'lightyellow':	 '\x07DEDE33',
		'lightred':		 '\x07E7470F',
		'lightblue':	 '\x07147FF5',
		'lightbrown':	 '\x07FF710F'
}

@Event('round_end')
def round_end(args):
    savedatabase()
	
@Event('player_activate')
def player_activate(args):
	userid = args.get_int('userid')
	players.addPlayer(userid)
	
@Event('player_disconnect')
def player_disconnect(args):
	userid = args.get_int('userid')
	savedatabase()
	if userid in players:
		del players[userid]
	
def savedatabase():
	echo_console('[Tag]: Saving database...')
	for player in players:
		player.commit()
	database.save()
	echo_console('[Tag]: Database successfully saved!')
