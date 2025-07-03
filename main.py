import os
import json
import asyncio
import configparser
import time
from telethon.sync import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.types import Message
# --- MODIFIED: Import FloodWaitError to specifically handle it ---
from telethon.errors.rpcerrorlist import FloodWaitError

# --- Configuration ---
# Load configuration from config.ini
config = configparser.ConfigParser()
config.read('config.ini')
SOURCE_ID = int(config['telegram']['source_channel_id'])
DESTINATION_ID = int(config['telegram']['destination_channel_id'])

# Load credentials from environment variables (set as GitHub Secrets)
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
SESSION_STRING = os.environ.get("SESSION_STRING")

# State and mapping files
STATE_FILE = "state.json"
ID_MAP_FILE = "id_map.json"

# --- State Management ---
def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    return {"last_message_id": 0}

def save_state(state):
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=4)

def load_id_map():
    if os.path.exists(ID_MAP_FILE):
        with open(ID_MAP_FILE, 'r') as f:
            # Ensure keys are loaded as integers
            return {int(k): v for k, v in json.load(f).items()}
    return {}

def save_id_map(id_map):
    with open(ID_MAP_FILE, 'w') as f:
        json.dump(id_map, f, indent=4)

# --- NEW: Helper function to handle sending with FloodWaitError retry logic ---
async def send_message_with_retry(client, entity, **kwargs):
    while True:
        try:
            # Use send_message for single messages
            if 'file' not in kwargs:
                message = await client.send_message(entity, **kwargs)
                return message
            # Use send_file for media/albums
            else:
                message = await client.send_file(entity, **kwargs)
                return message
        except FloodWaitError as e:
            print(f"Flood wait error: sleeping for {e.seconds + 5} seconds.")
            await asyncio.sleep(e.seconds + 5) # Wait for the specified time + a small buffer
        except Exception as e:
            # For other errors, log them and stop trying to send this message
            print(f"An unexpected error occurred: {e}")
            return None # Indicate failure

# --- Main Cloning Logic (Modified) ---
async def main():
    print("Initializing Telegram client...")
    async with TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH) as client:
        state = load_state()
        id_map = load_id_map()
        last_message_id = state.get("last_message_id", 0)

        print(f"Client initialized. Starting clone from message ID: {last_message_id}")

        source_entity = await client.get_entity(SOURCE_ID)
        destination_entity = await client.get_entity(DESTINATION_ID)

        messages_to_process = []
        async for message in client.iter_messages(source_entity, min_id=last_message_id, reverse=True):
            messages_to_process.append(message)

        print(f"Found {len(messages_to_process)} new messages to clone.")

        media_group_cache = {}
        new_last_message_id = last_message_id

        for message in messages_to_process:
            # Process media groups
            if message.grouped_id:
                if message.grouped_id not in media_group_cache:
                    media_group_cache[message.grouped_id] = []
                media_group_cache[message.grouped_id].append(message)
                continue

            # If a media group is ready to be sent, process it first
            if media_group_cache:
                for group_id, group_messages in list(media_group_cache.items()):
                    print(f"Sending media group {group_id} with {len(group_messages)} items.")
                    
                    # Sort messages in the group by their ID to ensure correct order
                    group_messages.sort(key=lambda m: m.id)

                    reply_to_msg_id = id_map.get(group_messages[0].reply_to_msg_id) if group_messages[0].reply_to else None
                    
                    sent_group = await send_message_with_retry(
                        client,
                        destination_entity,
                        file=[m.media for m in group_messages],
                        caption=[m.text for m in group_messages],
                        reply_to=reply_to_msg_id
                    )

                    if sent_group:
                        for i, old_msg in enumerate(group_messages):
                            id_map[old_msg.id] = sent_group[i].id
                        new_last_message_id = max(new_last_message_id, group_messages[-1].id)
                media_group_cache.clear()

            # Process single messages
            reply_to_msg_id = id_map.get(message.reply_to.reply_to_msg_id) if message.reply_to else None

            print(f"Cloning message ID: {message.id}")
            sent_message = await send_message_with_retry(
                client,
                destination_entity,
                message=message,
                reply_to=reply_to_msg_id,
                link_preview=False
            )

            if sent_message:
                id_map[message.id] = sent_message.id
                new_last_message_id = max(new_last_message_id, message.id)

            # Save state periodically to avoid losing progress on long runs
            if message.id % 20 == 0:
                state["last_message_id"] = new_last_message_id
                save_state(state)
                save_id_map(id_map)
                print("--- Progress saved ---")

        # Send any remaining media groups at the end
        if media_group_cache:
            for group_id, group_messages in list(media_group_cache.items()):
                print(f"Sending final media group {group_id}...")
                group_messages.sort(key=lambda m: m.id)
                reply_to_msg_id = id_map.get(group_messages[0].reply_to_msg_id) if group_messages[0].reply_to else None
                
                sent_group = await send_message_with_retry(
                    client,
                    destination_entity,
                    file=[m.media for m in group_messages],
                    caption=[m.text for m in group_messages],
                    reply_to=reply_to_msg_id
                )

                if sent_group:
                    for i, old_msg in enumerate(group_messages):
                        id_map[old_msg.id] = sent_group[i].id
                    new_last_message_id = max(new_last_message_id, group_messages[-1].id)

        # Final save
        state["last_message_id"] = new_last_message_id
        save_state(state)
        save_id_map(id_map)
        print("Cloning run finished successfully.")

if __name__ == "__main__":
    asyncio.run(main())
