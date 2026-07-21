ADD_FULL = \
'''Add an item to the hat.
Example: `$add The Room`

This command has the following flags:
* **-h**: Used to specify a hat other than the channel's default hat.
\tExample: `$add -h movies Troll 2`
* **-m**: Indicates your subcommand argument is a comma-seperated list of elements.
\tExample: `$add -m Monster a Go-Go, Birdemic, Batman & Robin`'''

ADD_CONTEXT_FULL = \
'''Add additional system context messages for this channel. This can help get the bot to behave in a more specific manner.
Example: `$add_context You always talk about baseball, even if it doesn't fit the conversation.`'''

BOT_FULL = \
'''Returns the least voted items.

Include an integer argument to specify the number of results to return (default={count}).
Example: `$bot 3`'''

CALC_FULL = \
'''Returns the result of a mathematical expression.
Example: `$calc 6 * 7`
This function supports, addition `+`, subtraction `-`, multiplication `*`, division `/`, modulation `%`, exponentiation `^`, factorials `!`, and parenthesis `()`.
Additionally the constants `{constants}`, and the following functions are supported: `{functions}.`
Example: `$calc sin(pi/2)`

**Note**: All trig functions take input in radians and output their result in radians. To input degrees into trig functions, use the `deg` function: `$calc sin(deg(90))`. Similarly, you can use the `deg` function to interpet the output of a trig function as degrees: `$calc deg(asin(1))`'''

CARD_FULL = \
'''Returns Scryfall data for a given MtG card.
Example: `$card Black Lotus`

This command has the following flags:
* **-r**: Returns the data a random MtG card.
\tExample: `$card -r`'''

CAT_FULL = \
'''Returns the entire contents of a given text file from your server's directory.
Example: `$cat parody_bands`'''

CHOICE_FULL = \
'''Returns one chosen item from a given list. The list can be of any size, with each item seperated by a comma.
Example: `$choice Captain Kirk, Captain Picard, Admiral Adama`

This command has the following flags:
* **c**: Specify a different number of items to chose.
\tExample: `$choice -c 2 White, Blue, Black, Red, Green, Colorless`'''

CLEAR_FULL = \
'''Clear all items from the hat.

To clear a hat other than the channel's default hat, include it as an argument: `$clear movies`'''

COMIC_FULL = \
'''Returns a random comic strip from a given Comic name.
Example: `$comic Garfield`

This command has the following flags:
* **l**: Lists all available comics.
\tExample: `$comic -l`'''

DAILY_FULL = \
'''Configure the daily messages being sent to a channel.
Message categories include:
* *calvin*: Sends a random Calvin & Hobbes comic.
* *card*: Sends a random Magic: The Gathering card.
* *fact*: Sends a random fact.
* *garfield*: Sends a random Garfield comic.
* *peanuts*: Sends a random Peantus comic.
* *tip*: Sends a usage tip for Karn.
* *wiki*: Sends a random Wikipedia article.
* *word*: Sends a random English word and its definition.
* *xkcd*: Sends a random XKCD comic.
Example: `$daily fact`

This command has the following flags:
* **-a**: Instructs the command to use all available categories.
\tExample: `$daily -a`
* **-c**: Change options for a channel other than the current channel.
\tExample: `$daily -c #general garfield`
* **-d**: Stop sending messages from the given category.
\tExample: `$daily -d word`
* **-l**: List the categories currently being sent to this channel.
\tExample: `$daily -l`
* **-m**: Add (or delete) multiple categories given in a comma-seperated list.
\tExample: `$daily -m fact, wiki, word, xkcd`
* **-t**: Trigger the immediate retrieval of a daily item in this channel.
\tExample: `$daily -t`'''

DEFINE_FULL = \
'''Returns definitions for a given English word.
Example: `$define love`'''

DIG_FULL = \
'''Perform a DNS lookup on a given address.
Example: `$dig verticalbar.org`
You can specify which nameserver to use by denoting it as an argument with a leading `@` symbol.
Example: `$dig @8.8.8.8 verticalbar.org`
By default this command queries for `A` records. To query for different record types include the record type as an argument.
Example: `$dig verticalbar.org MX`

This command has the following flags:
* **-p**: Allows you to specify a port to query through.
\tExample: `$dig -p 5353 verticalbar.org`
* **-x**: Performs a reverse domain lookup.
\tExample: `$dig -x 1.1.1.1`

This command has the following options:
* **+aaflag, +noaaflag:** This option is a synonym for **++aaonly**, **++noaaonly**.
* **++aaonly, +noaaonly:** This option sets the aa flag in the query.
* **+additional, +noadditional:** This option displays [or does not display] the additional section of a reply. The default is to display it.
* **+adflag, +noadflag:** This option sets [or does not set] the AD (authentic data) bit in the query. This requests the server to return whether all of the  answer  and  authority  sections  have  been  validated as secure, according to the security policy of the server. AD=1 indicates that all records have been validated as secure and the answer is not from a OPT-OUT range. AD=0 indicates that some part of the answer was  insecure or not validated.  This bit is set by default.
* **+all, +noall:** This option sets or clears all display flags.
* **+answer, +noanswer:** This option displays [or does not display] the answer section of a reply. The default is to display it.
* **+authority, +noauthority:** This option displays [or does not display] the authority section of a reply. The default is to display it.
* **+cd, +cdflag, +nocdflag:** This option sets [or does not set] the CD (checking disabled) bit in the query. This requests the server to not perform DNSSEC  validation of responses.
* **+cmd, +nocmd:** This  option  toggles  the printing of the initial comment in the output, identifying the version of dig and the query options that have been applied. The  default is to print this comment.
* **+comments, +nocomments:** This option toggles the display of some comment lines in the output, with information about the packet header and OPT pseudosection, and the names of the response section. The default is to print these comments. Other types  of  comments in the output are not affected by this option, but can be controlled using other options. These include **+cmd**, **+question**, **+stats**.
* **+dnssec, +do, +nodnssec, +nodo:** This option requests that DNSSEC records be sent by setting the DNSSEC OK (DO) bit in the OPT record in the additional section  of  the query.
* **+question, +noquestion:** This option toggles the display of the question section of a query when an answer is returned. The default is to print the question section as a comment.
* **+recurse, +norecurse:** This option  toggles  the setting of the RD (recursion desired) bit in the query.  This bit is set by default,  which means dig normally sends recursive queries. Recursion is automatically disabled when the **+trace** query option is used.
* **+short, +noshort:** This option toggles whether a terse answer is provided. The default is to print the answer in a verbose form.
* **+stats, +nostats:** This option toggles the printing of statistics: when the query was made, the size of the reply, etc. The default behavior is  to  print the query statistics as a comment after each lookup.
* **+tcp, +notcp:** This option  indicates  whether  to use TCP when querying name servers.  The default behavior is to use UDP.
* **+trace, +notrace:** This option  toggles tracing of the delegation path from the root name servers for the name being looked up. Tracing is disabled by default. When tracing is enabled, dig makes iterative queries to resolve the name being looked up. It  follows  referrals  from  the  root servers, showing the answer from each server that was used to resolve the lookup. If **@server** is also specified, it affects only the initial query for the root zone name servers. **+dnssec** is also set when **+trace** is set, to better emulate the default queries from a name server.

**Note:** All negative options will override their corresponding positive options if both are given.'''

ECHO_FULL = \
'''Echoes a given string within your current text channel.
Example: `$echo Repeat this back to me`

This command has the following flags:
* **-c**: Echoes the message in a different given channel.
\tExample: `$echo -c #general Repeat this in the general channel`'''

FACT_FULL = \
'''Sends a randomly selected fact.

This command has the following flags:
* **-n**: Select from exclusively "not safe for work" facts.
\tExample: `$fact -n`'''

FLIP_FULL = \
'''Returns either "heads" or "tails" via random selection.
To flip multiple coins simultaneously, include an integer argument.
Example: `$flip 3`'''

GENERATE_FULL = \
'''Generate an image from a given prompt
Example: `$generate a presidential election in minecraft`
**Note:** By default this command will use AI to "enhance" your prompt by adding more detail and context.

This command has the following flags:
* **-c**: Specify the number of images to generate. Must be in range [1, 8].
\tExample: `$generate -c 3 two cat scientists discovering a new element`
* **-p**: Use the raw prompt text for generation without any prompt enhancement.
\tExample: `$generate -p a hand with seven fingers`
* **-v**: Response will include the prompt used for generation. If used with the `-p` command flag, this will simply be the query itself.
\tExample: `$generate -v a white horse`'''

GREP_FULL = \
'''Return lines from a file in your server's directory that match a given pattern string.
Example: `grep parody_bands Von`'''

HEAD_FULL = \
'''Returns the first {line_count} lines of a given file.
Example: `$head fleshsim`
You can include multiple filenames with this command.
Example: `$head nice rude

This command has the following flags
* **-n**: Specifies the number of lines to return
\tExample: `$head -n 5 johnny`'''

IGNORE_FULL = \
'''Toggle whether the bot should respond to your messages without being prompted. The bot will still respond if your message contain its name, or if you use the `$prompt` command.

This command has the following flags:
* **-c**: Toggle unprompted messages for the entire text channel. You can specify a channel other than the current channel by including the channel mention as an argument.
\tExample: `$ignore -c #general`'''

IMAGE_FULL = \
'''Returns images relevant to a given query.
Example: `$image Grant MacDonald`

This command has the following flags:
* **-c**: Specify a number of images to return [default={count}].
\tExample: `$image -c 10 Margaery Tyrell`
* **-r**: Return randomly selected images from the search rather than the most relevant images.
\tExample: `$image -r Cressida`'''

INFO_FULL = "Provides a brief synopsis of Karn, including a link to his Open Source code."

JOIN_FULL = "Adds Karn to your current voice channel."

LEAVE_FULL = "Remove Karn from a voice channel."

LIST_FULL = "List all active hats for this server."

LS_FULL = "Lists the text files currently present in your server's directory."

NUMBER_FULL = \
'''Returns a randomly chosen number between two given integers.
Example: `$number 1 10`

If only one positive integer is given, a number between 1 and that integer will be chosen.
Example: `$number 10`

If only one nonnegative integer is given, a number between that integer and 0 will be chosen.
Example: `$number -10`
'''

PICK_FULL = \
'''Randomly selects an item from the hat.

To pick more than one item, include the desired number of items as an argument: `$pick 3`

This command has the following flags:
* **-h**: Used to specify a hat other than the channel's default hat.
\tExample: `$pick -h movies`'''

PING_FULL = "Returns \"pong\" and the round-trip latency if the bot is online."

POP_FULL = \
'''Randomly selects *and removes* an item from the hat.

To pop more than one item, include the desired number of items as an argument: `$pop 3`

This command has the following flags:
* **-h**: Used to specify a hat other than the channel's default hat.
\tExample: `$pop -h movies`
'''

PROMPT_FULL = \
'''Generates natural language or code from a given prompt.
Example: `$prompt Tell me story about a man who wanted to be a hockey player, but played golf instead`

This command has the following flags:
* **-c**: Generate a response using Chat Completions instead of Responses.
\tExample: `$prompt -c What is the answer to Life, the Universe, and Everything?`
* **-f**: Generate a response in the style of an input file.
\tExample: `$prompt -f dracula`'''

PURGE_FULL = \
'''Delete all messages in a channel older than a given number of days.
Example: `$purge 3`
That command will delete all messages older than 3 days.

Alternatively, you can include two integers to declare a range.
Example: `$purge 3 42`
That command will delete all messages older than 3 days, but not older than 42 days.'''

QR_FULL = \
'''Generate a QR code for input data
Example: `$qr https://www.gnu.org/`'''

READY_FULL = "Performs an \"All-Systems-Go\" check for the bot, and returns a status report."

REMIND_FULL = \
'''Sets a reminder for a given time. You can specify an exact time, or a time relative to now. Examples:
\t`$remind in 1 hour {delimeter} call mom`
\t`$remind tomorrow at this time {delimeter} time to raid`
\t`$remind 2026-01-15 14:30 {delimeter} party time!`

You can use `$remind list` to view your current reminders.'''

REMOVE_FULL = \
'''Remove an item at a given index from the hat.
Example: `$remove 3`
To view the indexes for a hat, use the `$view` command.

This command has the following flags:
* **-h**: Used to specify a hat other than the channel's default hat.
\tExample: `$remove -h movies 3`'''

RM_FULL = "Removes a text file from your server's directory"

ROLL_FULL = \
'''Rolls any number of n-sided dice in the classic "xDn" format.
Where **x** is the quantity of dice being rolled, and **n** is the number of sides on the die.
Example: `$roll 3d20`
When rolling only one die, you may ommit the leading "1".
Example: `$roll d6`

This command has the following flags:
* **-m**: Allows you to roll multiple dice simultaneously given by a comma-seperated list.
\tExample: `$roll -m 4d20, d3, 6d9`'''

SAY_FULL = \
'''Command Karn to say something in your voice channel.
Example: `$say Life is Mizzy`

This command has the following flags:
* **-s**: Specify the playback speed. Speed argument must be in range [0.25, 4.0].
\tExample: `$say -s 1.33 Say this faster`
* **-v**: Specify the voice to use. Supported voices include: **{voices}**.
\tExample: `$say -v shimmer I sound... different somehow`'''

SEARCH_FULL = \
'''Search the web with a given query.
Example: `$search Chris Chan`

This command has the following flags:
* **-c**: Specify a number of results to return [default={count}].
\tExample: `search -c 10 Sam Hyde`'''

SET_CONTEXT_FULL = \
'''Set the genesis system context message for this channel. This "primes" the bot to behave in a desired manner.
Example: `$set_context you must answer all prompts in J. R. R. Tolkien's writing style`
                                    
This command has the following flags:                                                                                        
* **-c**: Clears the current system context message and resets it to the default system context message.                     
\tExample: `$set_context -c`                                                                                 
* **-o**: Overwrite the default genesis message for the bot.                                                                 
\tExample: `$set_context -o You are a depressed and bored robot named Marvin the Paranoid Android`'''

SET_DEFAULT_FULL = \
'''Set the default hat for this channel.
Example: `$set_default movies`'''

SHOW_FULL = \
'''Show the rating score for a given item.
Example: `$show linux`'''

SHUFFLE_FULL = \
'''Returns a given list in a randomized order.
The list can be of any size, with each item seperated by a comma
Example: `$shuffle Cryzel Rosechu, Magi-Chan, Mewtwo, Sylvana`'''

TAIL_FULL = \
'''Returns the last {line_count} lines of a given file.
Example: `$tail silverhand`
You can include multiple filenames with this command.
Example: `$tail respond_nice response_rude`

This command has the following flags
* **-n**: Specifies the number of lines to return
\tExample: `$tail -n 5 dracula`'''

TEE_FULL = \
'''Writes user input into a given text file from your server's directory.
Example: `tee parody_bands Jon Von Jovi`'''

TIP_FULL = "Sends a random bot usage tip."

TOP_FULL = \
'''Returns the top voted items

Include an integer argument to specify the number of results to return (default={count}).
Example: `$top 3`'''

VIDEO_FULL = \
'''Search the web for videos with a given query
Example: `$search Dizaster - Love Me Long Time`

This command has the following flags:
* **-c**: Specify a number of results to return [default={count}].
\tExample: `$search -c 10 Fishtank`'''

VIEW_FULL = \
'''View all items in the hat.

To view a hat other than the channel's default hat, include it as an argument.
Example: `$view movies`'''

VIEW_CONTEXT_FULL = "View the system context message(s) for this channel."

WC_FULL = \
'''Returns the line count, word count, and character count for a given file.
Example: `$wc nice`
Multiple files can be specified in the same command.
Example: `$wc nice rude`

This command has the following flags:
* **-c**: Return the number of bytes in the file.
\tExample: `$wc -c dracula`
* **-l**: Return the line count for the file.
\tExample: `$wc -l johnny`
* **-m**: Return the character count for the file.
\tExample: `$wc -m silverhand`
* **-w**: Return the word count for the file.
\tExample: `$wc -w jules`'''

WEATHER_FULL = \
'''Returns the current weather for a given city
Example: `$weather 49078`
The city can be input in any of the following formats: `kalamazoo`; `kalamazoo, mi`; `kalamazoo, michigan`; `49006`'''

WIKI_FULL = \
'''Returns the summary of a given Wikipedia article
Example: `$wiki Thelema`

This command has the following flags:
* **-f**: Used to retrieve the full text of the given article.
\tExample: `$wiki -f Jack Parsons`
* **-i**: Used to retrieve all images from the given article.
\tExample: `$wiki -i L. Ron Hubbard`
\tOptionally, you may provide an integer sub-argument to limit the number of images sent.
\tExample: `$wiki -i 3 L. Ron Hubbard` will only result in three images sent.
* **-r**: Used to retrieve a random Wikipedia article.
\tExample: `$wiki -r`'''

WORDLE_FULL = \
'''Starts a new game of Wordle in the chat.

This command has the following flags:
* **-n**: Quits an ongoing game and starts a new game of Wordle.
\tExample: `$wordle -n`
* **-q**: Quits an ongoing game of Wordle.
\tExample: `$wordle -q`'''

XKCD_FULL = \
'''Returns the XKCD comic for a given comic number.

This command has the following flags:
* **-r**: Returns a random XKCD comic.
\tExample: `$xkcd -r`
* **-l**: Returns the latest XKCD comic
\tExample: `$xkcd -l'''
