CAT_FULL = \
'''Returns the entire contents of a given text file
Example: `cat parody_bands'''

DIG_FULL = \
'''Perform a DNS lookup on a given address.
Example: `$dig verticalbar.org`
You can specify which nameserver to use by denoting it as an argument with a leading `@` symbol.
Example: `$dig @8.8.8.8 verticalbar.org`
By default this command queries for `A` records. To query for different record types include the record type as an argument.
Example: `$dig verticalbar.org MX`

This command has the following flags:
* **-p**: Allows you to specify a port to query through
\tExample: `$dig -p 5353 verticalbar.org`
* **-x**: Performs a reverse domain lookup
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
* **+trace, +notrace:** This option  toggles tracing of the delegation path from the root name servers for the name being looked up. Tracing is disabled by default. When tracing is enabled, dig makes iterative queries to resolve the name being looked up. It  follows  referrals  from  the  root servers, showing the answer from each server that was used to resolve the lookup. If **@server** is also specified, it affects only the initial query for the root zone name servers. **+dnssec** is also set when **+trace** is set, to better emulate the default queries from a name server.'''

ECHO_FULL = \
'''Echoes a given string within your current text channel.
Example: `/echo Repeat this back to me`

This command has the following flags:
* **-c**: Echoes the message in a different given channel
\tExample: `$echo -c #general Repeat this in the general channel`'''

GENERATE_FULL = \
'''Generate an image from a given prompt
Example: `$generate a presidential election in minecraft`
Note: By default this command will use AI to "enhance" your prompt by adding more detail and context.

This command has the following flags:
* **-c**: Specify the number of images to generate. Must be in range [1, 8].
\tExample: `$generate -c 3 two cat scientists discovering a new element`
* **-p**: Use the raw prompt text for generation without any prompt enhancement.
\tExample: `$generate -p a hand with seven fingers`
* **-v**: Response will include the prompt used for generation. 
If used with the `-p` command flag, this will simply be the query itself.
\tExample: `$generate -v a white horse`'''

GREP_FULL = \
'''Return lines froa a file that match a given pattern string
Example: `grep parody_bands Von`'''

HEAD_FULL = \
'''Returns the first {line_count} lines of a given file.
Example: `$head fleshsim`
You can include multiple filenames with this command
This command has the following flags
* **-c**: Specifies the number of lines to return
\tExample: `$head -c 5 johnny`'''

JOIN_FULL = "Adds the bot to your current voice channel"

LEAVE_FULL = "Remove the bot from a voice channel"

LS_FULL = "Lists the text files currently present in the directory"

RM_FULL = "Removes a text file from the directory"

SAY_FULL = \
'''Command the bot to say something in your voice channel.
Example: `$say Life is Mizzy`

This command has the following flags:
* **-s**: Specify the playback speed. Must be in range [0.25, 4.0].
\tExample: `$say -s 1.33 Say this faster`
* **-v**: Specify the voice to use. Supported voices include: {voices}.
\tExample: `$say -v shimmer I sound... different somehow`'''

TAIL_FULL = \
'''Returns the last {line_count} lines of a given file.
Example: `$tail silverhand`
You can include multiple filenames with this command
This command has the following flags
* **-c**: Specifies the number of lines to return
\tExample: `$tail -c 5 dracula`'''

TEE_FULL = \
'''Writes user input into a given text file
Example: `tee parody_bands Jon Von Jovi`'''

WC_FULL = \
'''Returns the line count, word count, and character count for a given file. 
Multiple files can be specified in the same command.

This command has the following flags:
* **-c**: Return the number of bytes in the file
\tExample: `$wc -c dracula`
* **-l**: Return the line count for the file
\tExample: `$wc -l johnny`
* **-m**: Return the character count for the file
\tExample: `$wc -m silverhand`
* **-w**: Return the word count for the file
\tExample: `$wc -w jules`'''
