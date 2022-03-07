import peewee

db = peewee.SqliteDatabase('websites.db')

class Model(peewee.Model):
	class Meta:
		database = db