# bsky_invite_manager
- No longer maintained, BlueSky disabled invites in February 2024, [ArsTechnica: Bluesky finally gets rid of invite codes, lets everyone join](https://arstechnica.com/tech-policy/2024/02/bluesky-opens-to-the-public-with-choose-your-own-algorithm-options/) 
- Program to manage BlueSky invites from several accounts and put in DB/notify of them on Telegram
- This program allowed me to manage/sell several hundred dollars worth of BlueSky codes.



### Technologies
- BlueSky API using [MarshalX/atproto](https://github.com/MarshalX/atproto) Wrapper
- Postgres DB
- Telegram Bot
- Python3

### Programs


#### bsky_code_getter.py
  - automatically calls BlueSky API every x time, using the accounts configured in the DB to check for new invite codes and puts them in the DB, also sends alerts to Telegram of new codes.

#### telegram_bot.py
  - is an interactive bot on a telegram channel. Commands can be used to retrieve codes from the Postgres DB and also mark codes as sold.

