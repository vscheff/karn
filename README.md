# Karn

A Discord bot written in Python utilizing discord.py

## Features
- LLM integration including text completion, voice generation, and image generation
- Daily messages configurable per channel
- Text-based games
- Bucket system that allows multiple "hats" to be created, have items added to, and have random items selected
- Query support for images, videos, webpages, Wikipedia articles, Magic: The Gathering cards, comic strips, word definitions, and weather
- Randomization including dice rolling, coin flipping, list selection, list shuffling, and random number generation
- Item rating system that allows users to upvote and downvote abritary words/phrases
- QR code generation
- Creation of arbitary text files that can have lines input into them and have random lines returned

## Requirements
- Python 3.9 or newer
- PIP
- mySQL/MariaDB
- Webserver running on the same machine

## Installation
1. Fill `.env` file with all relevant environment variables (these are explained further down)
2. Install required Python libaries: `pip install -r requirements.txt`
3. Import database schema from `discord.sql` into a table named "discord": `mysqldump discord < /path/to/directory/discord.sql`
4. Move `leonardo_hook.php` into your webserver's directory
5. Start the bot with `python3 bot.py`

## Environment Variables
- `DISCORD_TOKEN` - Discord Application API Token
- `WEATHER_TOKEN` - API Token from openweathermap.org
- `WORDNIK_TOKEN` - API Token from wordnik.com
- `CHATGPT_TOKEN` - API Token from openai.com
- `CHATGPT_ORG` - Organization ID from openai.com
- `SQL_USER` - Username for MariaDB account
- `SQL_PASSWORD` - Password for MariaDB account
- `LEONARDO_TOKEN` - API Token from leonardo.ai
- `LEONARDO_WEBHOOK` - Authorization Token that Leonardo will use for the webhook

## Usage
### Standard Commands
Much of Karn's functionality is accessed through his standard commands. All standard commands are prefixed with `$`. A list of accessible commands can be found by executing `$help`. Additionally, you can pass a command name into the `$help` command to recieve additional help on that command specifically. Many commands accept arguments and/or command flags, usage of which is explained through the use of the `$help` command. The full command list will be explained further down.

### Chat Completion
Karn utilizes the ChatGPT 3.5-Turbo LLM for chat completion tasks. The basic way to access this functionality is through the use of the `$prompt` command. However, any message that contains "karn" will prompt a response from Karn that will be generated from the LLM. Additionally, there is a random chance that messages sent in the server will receive a response generated from the LLM. The likelyhood of this occuring will increase as more messages are received that don't trigger a response. Through the use of the `$ignore` command you can prevent Karn from responding to unprompted messages from a specific user or within a specific channel. Karn will never send an unprompted response to a message that is only one word, only contains tags, only contains voted items, or contains a URL.

When generating a response from the LLM, Karn will include preceeding messages as context for the request. This helps the LLM understand the context of the conversation, allowing for more relevant replies. The exact number of messages included is variable, and depends on the token length of the messages. Karn will devote 3/4 of the available tokens for context to these preceeding messages, up to a maximum of 256 messages.

There is a default System Context message that is sent with all LLM requests. You can view this context message by using the `$view_context` command. The System Context message can be configured per-channel. By using the `$set_context` command you can set the System Context message for a channel, or you can use the `$add_context` command to add additional System Context messages for a channel. This allows you to customize the bot's behaviour as it responds to messages using the LLM.

Karn also has a system to detect "rude" and "nice" messages that he will send custom responses to without making a request to the LLM. You can figure what messages he considers "rude" and "nice" by using the `$tee` command to add lines to `rude` or `nice`. For example, the command `$tee nice I like you` will add the phrase "I like you" to the phrases Karn considers "nice". Any message that contains the phrase "I like you" that triggers a response from Karn will be generated from his "nice" responses. To configure Karn's responses to "rude" and "nice" messages, use the `$tee` command to add lines to `respond_rude` or `respond_nice` respectively.

Karn will modify the response from the LLM to replace descriptors of himself with customizable descriptors. You can add additional descriptors by using the `$tee` command to add lines to `$descriptor`. For example, using the command `$tee descriptor a funny guy` will allow Karn to describe himself as "a funny guy". So, if the LLM generates a response like "As an AI, I aim to assist you.", Karn can modify the message to instead be "As a funny guy, I aim to assist you." Descriptors will be chosen at random from the `descriptor.txt` file.

### Item Rating
Karn will search through all messages to detect the usage of both `++` and `--`, which will upvote or downvote, respectively, a specified word or phrase. For example, the message `I love coffee++` will add an upvote for "coffee". Multiple votes can be sent within the same message. For example, the message `I love coffee++ but I hate tea--` will add an upvote for "coffee" and a downvote for "tea". To submit a vote for a mutli-word phrase, simply enclose the phrase with parentheses. For example, the message `I don't trust (Google products)--` will add a downvote for "Google products". Scores for individual items can be viewed with the `$show` command.

### Line Response
Through the use of the `$tee` command you can add lines into arbitary files. For example, using the command `$tee test This is a test line` will add "This is a test line" into a file named `test.txt`. If `test.txt` doesn't already exist, the file will be created and filled with this line. Any future `$tee` commands that specify `test` will simply append the line to the bottom of `test.txt`. The real power of this is utilized by sending the message `#test`. Doing so will cause Karn to reply with a random line from the "test" file. This allows users to dynamically create "call and response" style commands. For example, your users could append several "Good Morning" messages to a file named `gm`, then they could receive these "Good Morning" messages by sending `#gm`.

## Full Command List
Contained here is an exhaustive explanation of Karn's standard commands (excluding hidden commands) sorted by category.

### AI
- `add_context` - Adds additional system context messages for a channel. This can be used to fine-tune Karn's behaviour within a given channel. For example, if you wanted Karn to always discuss baseball within his responses in a channel you could use the command: `$add_context You always talk about baseball, even if it doesn't fit the conversation`. Note, this command simply adds additional system context messages. It does not overwrite or remove any previously set or added system context messages. So, if you previously added a system context message like "You never talk about baseball", the responses generated may continue to not include baseball related text.
- `generate` - Generates an image from a given prompt using Leonardo. For example, if you want an image of a Minecraft presidential election you could use the command: `$generate a presidential election in Minecraft`. By default, this command will only generate one image. If you want more than one image, use the `-c` command flag and specify the number of images: `$generate -c 3 two cat scientists discovering a new element`. Note, Leonardo will use AI to "enhance" your given prompt by default. This generally results in better generated images. However, if you want to avoid this, use the `-p` command flag.
- `ignore` - This command toggles whether Karn should respond to your messages without being prompted. By default Karn has the ability to respond to all users in all channels without being prompted. To prevent Karn from sending unprompted responses to any user in a given channel, use the `-c` command flag.
- `join` - Instructs Karn to join your current voice channel. Note, this command is not required to use to the `$say` command, as Karn will temporarily join your voice channel to execute the `$say` command if he is not already present. Using the `join` command prevents Karn from continually joining/leaving if members of your voice channel are using several `$say` commands in rapid succession. Additionally, if you have instructed Karn to join your current voice channel, any responses you trigger from Karn's Chat Completion or Line Response functionality will be read aloud in your voice channel.
- `leave` - Instructs Karn to leave your current voice channel. Note, Karn will automatically leave a voice channel when he detects he is the only member of the voice channel.
- `prompt` - Generates a response from the LLM. Further information on this functionality is described above.
- `say` - Generates text-to-speech for a given message and plays the message aloud in your voice channel. If Karn is not present in your voice channel, he will temporarily join the channel to play the message. You can specify playback speed by using the `-s` command flag and specifying a speed as a float: `$say -s 1.33 Say this faster`. By default, Karn will use OpenAI's "Onyx" voice. You can specify a different supported voice by using the `-v` command flag: `$say -v shimmer I sound... different somehow`.
- `set_context` - Sets the genesis system context message for a channel. By default, this will only add on to the default genesis system context message for Karn. If you want to completely overwrite the default genesis system context message, use the `-o` command flag. Please note, when overwriting the default genesis system context message, Karn may not fully understand his own name or role within your server.
- `view_context` - View all system context messages for a channel.

### DailyLoop
- `daily` - Allows you to configure the daily messages that are sent to a channel. By default, Karn will not send a daily message to any channel. By using this command you can specify what category of daily messages you want to be sent to a channel. For example, if you want a channel to receive a random fact each day, use the command `$daily fact`. If you later decide you would also like to receive a "word of the day" within the same channel, us the command `$daily word`. Use `$help daily` to view a list of all available categores. Each day Karn will chose a random category from the enabled categories in a channel, and send a message from that category. To add all available categories to a channel, use the `-a` command flag. If you wish to configure the daily message settings for a channel other than the channel your sending the command within, use the `-c` command flag. For example, if you want Karn to send a daily fact to #general, use the command: `$daily -c #general fact`. To stop sending messages from a given category, use the `-d` command flag: `$daily -d fact`. To view all categories currently enabled for a channel, use the `-l` command flag. To configure multiple categories within one command, use the `-m` flag with a comma-seperated list of categories: `$daily -m fact, word`. You can trigger the immediate retreival of a daily message by using the `-t` command flag. The time at which Karn will send the daily message is determined between 0:00 and 00:59. Karn will select weighted-random hour from 1-23 for each channel. Hour 12 is most likely to be chosen, with each hour away from 12 being less likely. The minute/second the message is sent is determined by when the `daily_loop` function is started, which is shortly after the program is started.

### Games
- `wordle` - Starts a new game of Wordle in your channel. Once a game is started, simply send your guess as a message into the chat. Use the command again to view how many guesses you have left. After submitting a guess, Karn will respond with the same word, but formatted to display your progress. Bold letters indicate a letter in the correct spot, underlined letters indicate a letter present in the word but not in the correct spot, and standard letters indicate an incorrect letter. Guesses that are not five letter words or guessses not present in the game's dictionary will not count against your total guesses. To quit an ongoing game and start a new game use the `-n` command flag. To quit an an ongoing game without starting a new game, use the `-q` command flag.

### Hat
All hat commands (excluding `$list` and `$set_default`) use the hat set as default for the channel. By default, all channels use the "main" hat. To use a different hat than the channels default (without changing the default) use the `-h` command flag and specify a different hat
- `add` - Adds an item to the hat. To add multiple items, use the `-m` command flag with a comma-seperated list of items: `$add -m this, that, and the other thing`.
- `clear` - Remove all items from the hat.
- `list` - List all active hats in the server.
- `pick` - Chose a random item from the hat. To chose more than one item, use the `-c` command flag and specify the number of items: `$pick -c 3`.
- `pop` - Chose *and remove* a random item from the hat. To chose more than one item, use the `-c` command flag and specify the number of items: `$pop -c 3`.
- `remove` - Remove a specified item from the hat. Items are specified by the index in which they appear when using the `$view` command, which is the same order they were added in. For example, to remove the third item added, use the command `$remove 3`.
- `set_default` - Sets the default hat to use for Hat commands sent in the current channel.
- `view` - View all items in the hat.

### Query
- `card` - Sends an image of a given Magic: the Gathering card and its market price. To retrieve a random card, use the `-r` command flag.
- `comic` - Sends a random strip from a given comic.
- `define` - Sends the definition(s) cor a given word
- `image` - Sends the most relevant image for a given search query. Only one image is sent by default. To retrieve more than one image, use the `-c` command flag: `$image -c 3 Shane Gillis`. You can opt to receieve a random image frim the search in liue of the most relevant image by using the `-r` command flaf.
- `search` - Sends the most relevant URL for a given search query. By default only one URL is sent. To retrieve more than one URL, use the `-c` command flag: `$search -c 3 tires`.
- `video` - Sends the most relevant video for a given search query. Only one video is sent by default. To retrieve more than one video, use the `-c` command flag: `$video -c 3 funny cats`.
- `weather` - Sends the current weather for a given location. Location can be input in any of the following formats: CITY; CITY, STATE; ZIPCODE. Two letter state abbreviations can be used to specify USA states: `$weather Houston, TX`.
- `wiki` - Sends the summary of a given Wikidia article. To retrieve the full text of a Wikipedia article, use the `-f`. You can retrieve all images from a Wikipedia article through the use of the `-i` command flag. Optionally, you may specify a maximum number of images to retrieve with the `-i` command flag by including an integer argument: `$wiki -i 3 Michigan`. You can retrieve a random Wikipedia article with the `-r` command flag.
- `xkcd` - Sends the xkcd comic strip for a given strip number. To retrieve the latest xkcd comic strip, use the `-l` command flag. To retrieve a random xkcd comic strip, use the `-r` command flag.

### Random
- `choice` - Selects one random item from a comma-seperated list.
- `fact` - Sends a randm fun fact. By using the `-n` command flag you can request only "Not Safe For Work" fun facts.
- `flip` - Sends either "heads" or "tails" by randoom selection. You can flip multiple coins by including an integer argument: `$flip 3`.
- `number` - Sends a random number within a given range. If only one integer argument is specified, a value of 1 will be implicitly used as the lower bound of the range for positive numbers and a value of 0 will be implicity used the upper bound of the range for non-positive numbers.
- `roll` - Sends the result of rolling a specified set of dice. Arguments need to be in the format xDn where `x` is the number of dice and `n` is the number of sides on the dice: `$roll 4d20`. If only one dice is being rolled, the 1 can be ommited: `$roll d20`. You can multiple types of dice by using the `-m` command flag and specifying the dice as a comma-seperated list: `$roll -m 4d20, 3d6, 2d100`. Note, dice can have any number of sides, they do not have to be "standard" dice: `$roll 2d13`.
- `shuffle` - Shuffles the order of a comma-seperated list.

### Rating
- `bot` - Sends the lowest rated items in the server. By default this command sends the five lowest items. You can specify the number of items to send by including an integer argument: `$bot 10`.
- `show` - Sends the score for a given item.
- `top` - Sends the highest rated items in the server. By default this command sends the five highest items. You can specify the number of items to send by including an integer argument: `$top 10`.

### Terminal
- `cat` - Sends the entire contents of a given file from the server's directory.
- `grep` - Sends all lines from a given file from the server's directory that match a given search string. The search string support Regular Expressions.
- `ls` - Sends all present files for the server's directory.
- `rm` - Removes a given file from the server's directory.
- `tee` - Writes a given input string into a file in the server's directory. If the given filename doesn't exist, this will create a new file with that name. If the given file already exists, the input string will be appended to the end of the file.

### Utility
- `calc` - Sends the result of a mathematical expression. Supported operators are: `+` `-` `*` `/` `^`.
- `info` - Sends a brief synopsis on Karn, including a link to his Open Source code on GitHub.
- `ping` - Sends "pong" if the bot is online, as well as the round trip message time.
- `purge` - Bulk deletes messages in the current channel. This command accepts an integer argument, and messages that are older than that many days are deleted. For example, to delete messages older than 3 days: `$purge 3`. Alternatively, you can pass two integer arguments to declare a range. For example, to delete messages older than 3 days but not older than 42 days: `$purge 3 42`.
- `qr` - Generates a QR code for a given string.
- `read` - Performs an "All Systems Go" check on the bot, and sends a status report.

### Miscellaneous
- `help` - Sends the entire accessible command list with a brief description of each command. You can view just the commands in a given category by including that category as an argument: `$help Utility`. You can view expanded information for a given command by including the command as an argument: `$help daily`.

## Backups and Data Recovery
Every day at 03:00 Eastern Time all files in each server's directory are backed up. In addition, the entire SQL database is backed up. Any of the following items can be restored if you have erroneously deleted/altered them:
- Files in your server's directory
- Hats
- System Context Messages
- Daily Message settings
Should you require any data recovery assistance, please contact me on Discord @newboard.