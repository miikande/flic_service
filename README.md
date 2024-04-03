# Flic Button Controller for Home Assistant

A simple server application to manage [Flic Button](https://flic.io/flic2) events.

This Python script allows you to control Home Assistant entities using Flic buttons. It uses the Flic SDK to interact with the buttons and the Home Assistant API to control the entities.

## Configuration

The script requires the IP address of the Home Assistant and Flic server, which is set in the `server_ip` variable. The Home Assistant API token is read from a file located at `{current user's home}/.HA_API_TOKEN`.

The script also defines several API endpoints and parameters for controlling light entities in Home Assistant.

## Button Actions

Each Flic button is associated with a list of actions. An action consists of an entity_id and a payload, such as '"color_temp_kelvin": 4400'. The list of actions for a button is defined in the `buttons` dictionary.

## Event Handling

The script handles button press and release events. When a button is pressed, the script starts a new thread that checks if the button is still being held down. If the button is released quickly, the script considers it a click event and performs the corresponding action. If the button is held down for more than a certain threshold, the script dims the lights.

## Running the Script

To run the script, simply execute it with Python:

```bash
python3 flic_button_controller.py
```

The script will start listening for button events and handle them accordingly.
