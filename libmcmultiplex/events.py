import re

EVENTS = {
#generic message
#re.compile(r'^(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) \[(?P<log_level>[A-Z]+)\] (?P<message>.*)$'),
    'tell':
        re.compile(r'^(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) \[(?P<log_level>[A-Z]+)\] §7(?P<src_player>[A-Za-z0-9_-]+) whispers (?P<message>.*) to (?P<dest_player>[A-Za-z0-9_-]+)$'),
    'chat_message':
        re.compile(r'^(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) \[(?P<log_level>[A-Z]+)\] \<(?P<player>[A-Za-z0-9_-]+)\> (?P<message>.*)$'),
    'console_message':
        re.compile(r'^(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) \[(?P<log_level>[A-Z]+)\] \[CONSOLE\] (?P<message>.*)$'),
    'server_action':
        re.compile(r'^(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) \[(?P<log_level>[A-Z]+)\] (?P<source>[A-Za-z0-9_-]+): (?P<action>.*)$'),
    'command':
        re.compile(r'^(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) \[(?P<log_level>[A-Z]+)\] (?P<player>[A-Za-z0-9_-]+) issued server command: (?P<command>[A-Za-z-]+)(?: (?P<args>.*))?$'),
    'failed_command':
        re.compile(r'^(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) \[(?P<log_level>[A-Z]+)\] (?P<player>[A-Za-z0-9_-]+) tried command: (?P<command>[A-Za-z-]+)(?: (?P<args>.*))?$'),
    'join':
        re.compile(r'^(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) \[(?P<log_level>[A-Z]+)\] (?P<player>[A-Za-z0-9_-]+) \[/(?P<ip_address>(?:\d{1,3}\.){3}\d{1,3})):(?P<port>\d{1,5})\] logged in$'),
    'part':
        [re.compile(r'^(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) \[(?P<log_level>[A-Z]+)\] (?P<player>[A-Za-z0-9_-]+) lost connection: (?P<reason>.*)$'),
        re.compile(r'^(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) \[(?P<log_level>[A-Z]+)\] /(?P<ip_address>(?:\d{1,3}\.){3}\d{1,3})):(?P<port>\d{1,5}) lost connection$')],
    'disconnect':
        [re.compile(r'^(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) \[(?P<log_level>[A-Z]+)\] Disconnecting (?P<player>[A-Za-z0-9_-]+) \[/(?P<ip_address>(?:\d{1,3}\.){3}\d{1,3})):(?P<port>\d{1,5})\]: (?P<reason>.*)$'),
        re.compile(r'^(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) \[(?P<log_level>[A-Z]+)\] Disconnecting /(?P<ip_address>(?:\d{1,3}\.){3}\d{1,3})):(?P<port>\d{1,5}): (?P<reason>.*)$')],
    'home':
        re.compile(r'^(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) \[(?P<log_level>[A-Z]+)\] (?P<player>[A-Za-z0-9_-]+) returned home$'),
    'player_list':
        re.compile(r'^(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) \[(?P<log_level>[A-Z]+)\] Connected players: ?(?P<player_list>.*)$'),
#runecraft
#re.compile(r'^(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) \[(?P<log_level>[A-Z]+)\] (?P<spell>.*) destroyed\.$'),
#re.compile(r'^(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) \[(?P<log_level>[A-Z]+)\] (?P<player>[A-Za-z0-9_-]+) used a (?P<spell>.*)\.$'),
}