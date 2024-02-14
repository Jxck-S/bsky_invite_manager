from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ForceReply
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler, MessageHandler
import psycopg2
import configparser
from functools import partial, wraps
from psycopg2.extras import DictCursor
import json

with open('telegram_conf.json', 'r') as f:
	config = json.load(f)
print(config)
conf = configparser.ConfigParser()
conf.read('conf.ini')
TELEGRAM_API_KEY = conf.get("TELEGRAM", "KEY")
class restricted(object):
	"""
	Decorator class used to restrict usage of commands.
	Sends a "disallowed" reply if necessary. Works on functions and methods.
	"""
	def __init__(self, func):
		self._func = func
		self._obj = None
		self._wrapped = None

	def __call__(self, *args, **kwargs):
		if not self._wrapped:
			if self._obj:
				self._wrapped = self._wrap_method(self._func)
				self._wrapped = partial(self._wrapped, self._obj)
			else:
				self._wrapped = self._wrap_function(self._func)
		return self._wrapped(*args, **kwargs)

	def __get__(self, obj, type_=None):
		self._obj = obj
		return self

	def _wrap_method(self, method): # Wrapper called in case of a method
		@wraps(method)
		def inner(self, *args, **kwargs): # `self` is the *inner* class' `self` here
			user_id = str(args[0].effective_user.id) # args[0]: update
			if user_id not in config['USERS']:
				print(f'Unauthorized access denied on {method.__name__} for {user_id} : {args[0].message.chat.username}.')
				args[0].message.reply_text(f'User disallowed. Tell admin to add your id {user_id}')
				return None # quit handling command
			return method(self, *args, **kwargs)
		return inner

	def _wrap_function(self, function): # Wrapper called in case of a function
		@wraps(function)
		def inner(*args, **kwargs): # `self` would be the *restricted* class' `self` here
			user_id = str(args[0].effective_user.id) # args[0]: update
			if user_id not in config['USERS']:
				print(f'Unauthorized access denied on {function.__name__} for {user_id} : {args[0].message.chat.username}.')
				args[0].message.reply_text(f'User disallowed. Tell admin to add your id {user_id}')
				return None # quit handling command
			return function(*args, **kwargs)
		return inner




async def lookup_main(update, context, sql):
	id = str(update.message.from_user.id)
	print(f"Running {sql} for {config['USERS'][id]}:{id}")
	mydb = psycopg2.connect(
	host=conf.get("DATABASE", "host"),
	user=conf.get("DATABASE", "user"),
	port=conf.getint("DATABASE", "port"),
	password= conf.get("DATABASE", "password"),
	database= conf.get("DATABASE", "database"),
	)
	table = conf.get("DATABASE", "table")
	print("Connected to db")
	cur = mydb.cursor(cursor_factory=DictCursor)
	try:
		cur.execute(sql)
	except Exception as e:
		print(e)
		await update.message.reply_text(f"Lookup ERROR\n{e}")
	else:
		if cur.description:
			result = cur.fetchall()
			message = ''
			show_count = 0
		else:
			mydb.commit()
			result = mydb.status
	cur.close()
	mydb.close()
	return result


@restricted
async def list_invites(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
	"""List good invites."""
	chat_id = update.message.chat_id
	sql = "SELECT code from public.invites WHERE (sold = FALSE) AND (used = FALSE) AND (resrvd IS NULL OR resrvd = False)"
	results = await lookup_main(update, context, sql)
	text = "Listing Invites\n"
	print(results)
	buttons = []
	for inv in results:
		text += f"\n {inv['code']}\n"
		button = InlineKeyboardButton(text=inv["code"], callback_data=inv["code"])
		buttons.append([button])
		keyboard_inline = InlineKeyboardMarkup(buttons)
	await update.message.reply_text("Codes", reply_markup=keyboard_inline)	


@restricted
async def count(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
	"""Count invites."""
	sql = "SELECT COUNT(*) AS count FROM public.invites WHERE (sold = FALSE) AND (used = FALSE) AND (resrvd IS NULL OR resrvd = False)"
	results = await lookup_main(update, context, sql)
	text = f"Good codes: {results[0]['count']}"
	print(text)
	await update.message.reply_text(text)	


@restricted
async def sold_invite(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
	"""Sell invites."""
	chat_id = update.message.chat_id
	code = context.chat_data['code']
	buyer = context.chat_data['buyer']
	net_price = context.chat_data['net']
	sql = f"UPDATE public.invites SET sold_to_ebay = '{buyer}', net = '{net_price}', sold = True WHERE code = '{code}'"
	results = await lookup_main(update, context, sql)
	text = f"Marking {code} as sold to {buyer} for {net_price}"
	text += f"\n\nUpdate: {'Ok' if results else 'Fail'}\n"
	print(text)
	await update.message.reply_text(text)	

async def button(update: Update, context) -> None:
	query = update.callback_query
	await query.answer()
	buttons = []
	print(query.data)
	context.chat_data['code'] = query.data
	button = InlineKeyboardButton(text="Mark as Sold", callback_data="mark_sold")
	buttons.append([button])
	keyboard_inline = InlineKeyboardMarkup(buttons)
	await query.message.reply_text(query.data, reply_markup=keyboard_inline)

async def sold_button(update: Update, context) -> None:
	query = update.callback_query
	code = context.chat_data['code']
	print("Preparing to mark sold:", code)
	await query.answer()
	message = await context.bot.send_message(chat_id=update.effective_chat.id, text=f'Reply with buyer and amount for {code}', reply_markup=ForceReply())
	context.chat_data['sold_message_id'] = message.message_id
	
async def handle_reply(update: Update, context) -> None:
	if update.message.reply_to_message and update.message.reply_to_message.message_id == context.chat_data.get('sold_message_id'):
		user_reply = update.message.text.split()
		context.chat_data['buyer'] = user_reply[0]
		context.chat_data['net'] = user_reply[1]
		# Do something with the user's reply
		await sold_invite(update, context)
"""Run bot."""
# Create the Application and pass it your bot's token.
application = Application.builder().token(TELEGRAM_API_KEY).build()

# on different commands - answer in Telegram
application.add_handler(CommandHandler(["list"], list_invites))
application.add_handler(CommandHandler(["sold"], sold_invite))
application.add_handler(CommandHandler("count", count))
application.add_handler(CallbackQueryHandler(button, "^bsky-social"))
application.add_handler(CallbackQueryHandler(sold_button, "^mark_sold"))
application.add_handler(MessageHandler(None, handle_reply))


# Run the bot until the user presses Ctrl-C
application.run_polling(allowed_updates=Update.ALL_TYPES)
