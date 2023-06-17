Instruction: how to launch the bot
1. Create a database in pgAdmin4 with any name you want
2. Create a "config.py" file in the root project directory
3. Open config.py and fill it like that:

              DB_HOST = "your pgAdmin4 username here"  # default is "localhost"
              DB_NAME = "your pgAdmin4 database name here"  
              DB_USER = "your pgAdmin4 username here"  # default is "postgres"
              DB_PASS = "your pgAdmin4 pass here"
              
              BOT_TOKEN = "your bot token here"
