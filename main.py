import os
import json
import asyncio
import configparser
from telethon.sync import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.types import Message

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
            return {int(k): v for k, v in json.load(f).items()}
    return {}

def save_id_map(id_map):
    with open(ID_MAP_FILE, 'w') as f:
        json.dump(id_map, f, indent=4)

# --- Main Cloning Logic ---
async def main():
    print("Initializing Telegram client...")
    async with TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH) as client:
        # Load state and mapping
        state = load_state()
        id_map = load_id_map()
        last_message_id = state.get("last_message_id", 0)
        
        print(f"Client initialized. Starting clone from message ID: {last_message_id}")

        source_entity = await client.get_entity(SOURCE_ID)
        destination_entity = await client.get_entity(DESTINATION_ID)
        
        messages_to_process = []
        # We fetch messages in reverse chronological order and then reverse the list
        # to process them from oldest to newest.
        async for message in client.iter_messages(source_entity, min_id=last_message_id, reverse=False):
            messages_to_process.append(message)
        
        # Process from oldest to newest to maintain order
        messages_to_process.reverse()
        
        print(f"Found {len(messages_to_process)} new messages to clone.")
        
        media_group_cache = {}

        for message in messages_to_process:
            try:
                # Handle grouped media (albums)
                if message.grouped_id:
                    if message.grouped_id not in media_group_cache:
                        media_group_cache[message.grouped_id] = []
                    media_group_cache[message.grouped_id].append(message)
                    # Wait until we have all messages of the group
                    # This simple approach assumes they come in sequence. A more robust
                    # solution might need to check the next message before sending.
                    continue # Skip sending until the group is complete or a new message appears
                
                # If there's a cached media group, send it now
                if media_group_cache:
                    for group_id, group_messages in list(media_group_cache.items()):
                        print(f"Sending media group {group_id} with {len(group_messages)} items.")
                        # Find reply_to mapping if the first item is a reply
                        reply_to_msg_id = id_map.get(group_messages[0].reply_to_msg_id) if group_messages[0].reply_to else None
                        
                        sent_group = await client.send_file(
                            destination_entity,
                            file=[m.media for m in group_messages],
                            caption=[m.text for m in group_messages],
                            reply_to=reply_to_msg_id
                        )
                        # Map all old message IDs to the new sent messages
                        for i, old_msg in enumerate(group_messages):
                            id_map[old_msg.id] = sent_group[i].id
                    media_group_cache.clear()

                # Handle single messages
                reply_to_msg_id = None
                if message.reply_to:
                    reply_to_msg_id = id_map.get(message.reply_to.reply_to_msg_id)

                print(f"Cloning message ID: {message.id}")
                sent_message = await client.send_message(
                    destination_entity,
                    message=message,
                    reply_to=reply_to_msg_id,
                    link_preview=False # Avoids creating link previews that might not have existed
                )
                
                id_map[message.id] = sent_message.id
                state["last_message_id"] = message.id
            
            except Exception as e:
                print(f"Error cloning message {message.id}: {e}")
                # Save progress even if one message fails
                save_state(state)
                save_id_map(id_map)
                continue

        # Send any remaining media groups at the end
        if media_group_cache:
             for group_id, group_messages in list(media_group_cache.items()):
                print(f"Sending final media group {group_id}...")
                reply_to_msg_id = id_map.get(group_messages[0].reply_to_msg_id) if group_messages[0].reply_to else None
                sent_group = await client.send_file(destination_entity, file=[m.media for m in group_messages], caption=[m.text for m in group_messages], reply_to=reply_to_msg_id)
                for i, old_msg in enumerate(group_messages):
                    id_map[old_msg.id] = sent_group[i].id
        
        # Final save
        save_state(state)
        save_id_map(id_map)
        print("Cloning run finished successfully.")


if __name__ == "__main__":
    asyncio.run(main())
