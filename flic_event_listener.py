# Create an event listener for Flic Button 2.
# This script is based on the example script provided by Fliclib-linux-hci.

import sys
sys.path.append('./flic_lib')
import fliclib

# Constant for the Flic server's IP address.
server_ip = "127.0.0.1"

client = fliclib.FlicClient(server_ip)

def got_button(bd_addr):
    cc = fliclib.ButtonConnectionChannel(bd_addr)
 
    # Drop queued button click events
    cc.on_button_click = \
        lambda channel, click_type, was_queued, time_diff: \
            print(channel.bd_addr + " " + str(click_type)) if not was_queued else None
            
    cc.on_connection_status_changed = \
        lambda channel, connection_status, disconnect_reason: \
            print(channel.bd_addr + " " + str(connection_status) + (" " + str(disconnect_reason) if connection_status == fliclib.ConnectionStatus.Disconnected else ""))
    client.add_connection_channel(cc)

def got_info(items):
	print(items)
	for bd_addr in items["bd_addr_of_verified_buttons"]:
		got_button(bd_addr)

client.get_info(got_info)

client.on_new_verified_button = got_button

client.handle_events()
