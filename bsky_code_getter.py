from atproto import Client
import psycopg2
import time, telegram
from psycopg2.extras import DictCursor
from atproto import exceptions as ATExceptions
import configparser

conf = configparser.ConfigParser()
conf.read('conf.ini')

while True:
	connection = psycopg2.connect(
		host=conf.get("DATABASE", "host"),
		user=conf.get("DATABASE", "user"),
		port=conf.getint("DATABASE", "port"),
		password= conf.get("DATABASE", "password"),
		database= conf.get("DATABASE", "database")
	)
	cursor = connection.cursor(cursor_factory=DictCursor)

	cursor.execute("SELECT * FROM accounts ORDER BY ID ASC;")
	accounts = cursor.fetchall()

	cursor.execute("SELECT * FROM invites;")
	ext_invites = cursor.fetchall()

	old_inv_dict = {}
	old_inv_list = []
	for inv in ext_invites:
		old_inv_list.append(inv['code'])
		if inv['account_owner'] not in old_inv_dict.keys():
			old_inv_dict[inv['account_owner']] = [{"code": inv['code'], "used": inv['used']}]
		else:
			old_inv_dict[inv['account_owner']].append({"code": inv['code'], "used": inv['used']})
	for account in accounts:
		#bsky = Bluesky(account["username"], account["pw"])
		#invites = bsky.getAccountInviteCodes(includeUsed=True).json()["codes"]
		client = Client()
		print("Logging in to", account["username"])
		try:
			client.login(account["username"], account["pw"])
			invites = client.com.atproto.server.get_account_invite_codes().codes
		except ATExceptions.UnauthorizedError:
			print(f"{account['username']} login problem")
			invites = None
		if invites:
			#print(invites)
			#Used Invite detection
			if account['id'] in old_inv_dict.keys():
				used_list = []
				for inv in invites:
					if len(inv.uses) >= 1:
						used_list.append(inv.code)
				for inv in old_inv_dict[int(account['id'])]:
					if not inv['used'] and inv['code'] in used_list:
						print(f"Used invite on {account['username']} {inv['code']}")
						update_query = """
							UPDATE invites
							SET used = True
							WHERE code = %s;
						"""
						# Execute the UPDATE statement with the provided data
						cursor.execute(update_query, (inv['code'],))

						# Commit the changes to the database
						connection.commit()
			#for invite in invites:
			for inv in invites:
				if inv.code not in old_inv_list:
					msg = f"New invite on {account['username']} {inv.code}"
					print(msg)
					import telegram, asyncio
					# Create a Telegram object
					bot = telegram.Bot(token=conf.get("TELEGRAM", "KEY"))

					# Send a message to a user
					async def send_message():
						await bot.send_message(chat_id=conf.get("TELEGRAM", "CHAT_ID"), text=msg)# Replace CHAT_ID with the chat ID of the user you want to send the message to

					asyncio.run(send_message())

					data_to_insert = {
						'code': inv.code,
						'used': True if len(inv.uses) == 1 else False,
						'sold': False,
						'account_owner': account['id'],
						'created': inv.created_at
						# Add more columns and values as needed
					}

					query = "INSERT INTO invites ({}) VALUES ({})".format(
						', '.join(data_to_insert.keys()),
						', '.join(['%s'] * len(data_to_insert))
					)

					cursor.execute(query, list(data_to_insert.values()))
					connection.commit()
		#print(account["username"], invites.json()["codes"])
		time.sleep(5)
	cursor.close()
	connection.close()
	print("Sleeping")
	time.sleep(60*60*12)