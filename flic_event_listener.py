import os
import threading
import time
from flic_lib import fliclib
from requests import get, post

# IP address of the Home Assistant and Flic server.
server_ip = "127.0.0.1"

# The Home Assistant API URL.
ha_api_url = "http://" + server_ip + ":8123/api/"

# HA light switch API endpoints.
ha_light_switch_on_api_endpoint = "services/light/turn_on"
ha_light_switch_off_api_endpoint = "services/light/turn_off"

# Read the Home Assistant API token from a file: {current user's home}/.HA_API_TOKEN
ha_api_token = open(os.path.expanduser('~/.HA_API_TOKEN'), "r").read().strip()

# Home Assistant API headers.
ha_headers = {
    "Authorization": "Bearer " + ha_api_token,
    "content-type": "application/json",
}

# Flic client to interact with Flic buttons.
client = fliclib.FlicClient(server_ip)

# The maximum queue time in seconds for a button event.
# If max time has been exceeded, the event is ignored.
max_diff_time = 2

# Click threshold in seconds. If the button is held down for more 
# than this time, it is considered a hold event.
click_threshold = 0.3

# Sleep time in seconds between each dim step.
dim_step_sleep_time = 0.01

# Dimming step in brightness units.
dimming_step = 5

# Brightness threshold for switching the lights off.
brightness_threshold_for_switch_off = 2

# Create a structure for connected buttons.
connected_buttons = {}

# Create a structure for button actions and buttons' attributes.
buttons = {}

buttons["80:e4:da:7d:11:86"] = {
    'action_url': ha_light_switch_on_api_endpoint,
    'action_url_off': ha_light_switch_off_api_endpoint,
    'click_payloads': [
        '{"entity_id": "light.keittion_valot", "color_temp_kelvin": 4400}',             # Neutral white
        '{"entity_id": "light.keittion_valot", "color_temp_kelvin": 3200}',             # Warm white
        '{"entity_id": "light.keittion_valot", "color_temp_kelvin": 2700}',             # Even warmer white
        '{"entity_id": "light.keittion_valot", "rgbww_color": [255, 119, 0, 0, 125]}',  # Light orange
        '{"entity_id": "light.keittion_valot", "rgbww_color": [255, 80, 0, 0, 0]}',     # Orange
        '{"entity_id": "light.keittion_valot", "rgbww_color": [255, 0, 105, 0, 0]}',    # Pink
        '{"entity_id": "light.keittion_valot", "rgbww_color": [0, 0, 255, 0, 0]}',      # Blue
        '{"entity_id": "light.keittion_valot", "rgbww_color": [0, 126, 255, 0, 0]}',    # Light blue
        '{"entity_id": "light.keittion_valot", "rgbww_color": [0, 255, 187, 0, 0]}',    # Turquoise
        '{"entity_id": "light.keittion_valot", "rgbww_color": [0, 255, 38, 0, 0]}',     # Green
        
    ], 
    'click_count': 0,
    "is_held": False,
    "time_pressed": 0,
    "time_released": 0,
    "brightness": 255,
}

def make_post_request(action=None, payload=None):
    if action is None or payload is None: return
    #print("POST: " + action + "\n" + payload)
    full_url = ha_api_url + action
    response = post(url=full_url, headers=ha_headers, data=payload)
    #print("RESP:\n" + response.text)

def handle_button_event(channel, click_type, was_queued, time_diff):
    #print(channel.bd_addr + " " + str(click_type) + (" (queued)" if was_queued else "") + " " + str(time_diff) + " seconds ago")
    
    # Get the button's bd_addr.
    bd_addr = channel.bd_addr
    
    # Return if the button is not connected or if no actions are defined for the button.
    if bd_addr not in connected_buttons or bd_addr not in buttons:
        return
        
    # If button was pressed down, set the time it was pressed down.
    if click_type == fliclib.ClickType.ButtonDown:
        buttons[bd_addr]["time_pressed"] = time.time()
        buttons[bd_addr]["is_held"] = True
        #print("Button down")
        
        # Start a new thread that checks if the button is still being held down
        threading.Thread(target=check_button_hold, args=(bd_addr,)).start()
    
    # Handle release event
    if click_type == fliclib.ClickType.ButtonUp:
        buttons[bd_addr]["time_released"] = time.time()

        buttons[bd_addr]["is_held"] = False
        #print("Button up")

        # Determine if this was a click event.
        if buttons[bd_addr]["time_released"] - buttons[bd_addr]["time_pressed"] < click_threshold:
            # Reset button attributes before handling the click event.
            reset_button_attributes(bd_addr)
            handle_click(bd_addr)
            
def reset_button_attributes(bd_addr):
    button = buttons[bd_addr]
    button["is_held"] = False
    button["time_pressed"] = 0
    button["time_released"] = 0
    button["brightness"] = 255
            
def handle_click(bd_addr):
    button = buttons[bd_addr]
    actions = button['click_payloads']
    click_count = button['click_count']
    action = actions[click_count]
    
    # Add brightness to the action
    action = action[:-1] + ', "brightness": ' + str(button['brightness']) + '}'

    make_post_request(button['action_url'], action)

    # Increase the click count and reset it to 0 if it exceeds the number of actions.
    click_count = (click_count + 1) % len(actions)
    
    button['click_count'] = click_count

def check_button_hold(bd_addr):
    start_time = buttons[bd_addr]["time_pressed"]
    elapsed_time = time.time() - start_time

    while buttons[bd_addr]["is_held"] and buttons[bd_addr]["brightness"] >= brightness_threshold_for_switch_off:
        if (elapsed_time >= click_threshold):
            #print("Button held for " + str(elapsed_time) + " seconds")
            dim_lights(bd_addr)
            
        time.sleep(dim_step_sleep_time)
        elapsed_time = time.time() - start_time
    
    if buttons[bd_addr]["is_held"] and buttons[bd_addr]["brightness"] < brightness_threshold_for_switch_off:
        # TODO: entity id shouldn't be hardcoded
        make_post_request(buttons[bd_addr]["action_url_off"], '{"entity_id": "light.keittion_valot"}')
        
        # On next click, start from the current action.
        buttons[bd_addr]['click_count'] = get_current_action_idx(bd_addr)

def dim_lights(bd_addr):
    button = buttons[bd_addr]
    brightness = button["brightness"] - dimming_step
    #print("Dimming lights to " + str(brightness))
    button["brightness"] = brightness
    
    button = buttons[bd_addr]
    actions = button['click_payloads']
    action = actions[get_current_action_idx(bd_addr)]
    
    # Add brightness to the action
    action = action[:-1] + ', "brightness": ' + str(button['brightness']) + '}'

    make_post_request(button['action_url'], action)
    
def get_current_action_idx(bd_addr):
    # Get the current action which is click_count - 1 because click_count was already increased in handle_click().
    # If click_count is 0, the current action is the last one in the list.
    button = buttons[bd_addr]
    actions = button['click_payloads']
    current_action_idx = button['click_count'] - 1 if button['click_count'] > 0 else len(actions) - 1
    
    return current_action_idx
    
def got_button(bd_addr):
    cc = fliclib.ButtonConnectionChannel(bd_addr)
 
    cc.on_button_up_or_down = \
        lambda channel, click_type, was_queued, time_diff: \
            handle_button_event(channel, click_type, was_queued, time_diff) if time_diff <= max_diff_time else None
         
    cc.on_connection_status_changed = \
        lambda channel, connection_status, disconnect_reason: \
            update_status(channel, connection_status, disconnect_reason)
    
    client.add_connection_channel(cc)

def update_status(channel, connection_status, disconnect_reason):
    #print(channel.bd_addr + " " + str(connection_status) + (" " + str(disconnect_reason) if connection_status == fliclib.ConnectionStatus.Disconnected else ""))
    
    if connection_status == fliclib.ConnectionStatus.Connected:
        connected_buttons[channel.bd_addr] = channel
    elif connection_status == fliclib.ConnectionStatus.Disconnected:
        del connected_buttons[channel.bd_addr]
        
        
def got_info(items):
	print(items)
	for bd_addr in items["bd_addr_of_verified_buttons"]:
		got_button(bd_addr)

client.get_info(got_info)
client.on_new_verified_button = got_button
client.handle_events()