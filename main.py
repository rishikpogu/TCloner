import os
import json
import asyncio
import configparser
from typing import List, Dict, Any, Optional, Union
from telethon.sync import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.types import Message
from telethon.errors.rpcerrorlist import FloodWaitError

# --- Configuration ---
config = configparser.ConfigParser()
config.read('config.ini')

SOURCE_ID = int(config['telegram']['source_channel_id'])
DESTINATION_ID = int(config['telegram']['destination_channel_id'])
# NEW: Read the delay from the config file
DELAY_SECONDS = float(config['telegram'].get('delay_seconds', 1.0))

# Load credentials from environment variables
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
SESSION_STRING = os.environ.get("SESSION_STRING")

# State and mapping files
STATE_FILE = "state.json"
ID_MAP_FILE = "id_map.json"

# --- Utility Functions ---
def load_json_file(filename: str, default_data: Any = {}) -> Any:
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            return json.load(f)
    return default_data

def save_json_file(filename: str, data: Any):
    with open(filename, 'w') as f:
        json.dump(data, f, indent=4)

# --- Core Logic ---
async def send_with_retry(client, state, id_map, **kwargs) -> Optional[Union[Message, List[Message]]]:
    """Wraps the client's send functions with robust FloodWaitError handling."""
    while True:
        try:
            if 'file' in kwargs: # Use send_file for media
                return await client.send_file(**kwargs)
            else: # Use send_message for text
                return await client.send_message(**kwargs)
        except FloodWaitError as e:
            print(f"Flood wait: saving progress and sleeping for {e.seconds + 5}s.")
            save_json_file(STATE_FILE, state)
            save_json_file(ID_MAP_FILE, id_map)
            await asyncio.sleep(e.seconds + 5)
        except Exception as e:
            print(f"Error sending message/file: {e}")
            return None

async def main():
    """Main function to run the cloning process."""
    print("🚀 Initializing Telegram Cloner...")
    async with TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH) as client:
        
        state = load_json_file(STATE_FILE, {"last_message_id": 0})
        id_map = {int(k): v for k, v in load_json_file(ID_MAP_FILE).items()}
        last_message_id = state.get("last_message_id", 0)

        print(f"Starting clone from message ID: {last_message_id}")
        print(f"Message delay set to: {DELAY_SECONDS} seconds.")

        source_entity = await client.get_entity(SOURCE_ID)
        destination_entity = await client.get_entity(DESTINATION_ID)

        messages_to_process = []
        # Fetch messages starting from the last known ID
        async for message in client.iter_messages(source_entity, min_id=last_message_id):
            messages_to_process.append(message)
        
        # Reverse to process from oldest to newest, ensuring correct order
        messages_to_process.reverse()
        
        print(f"Found {len(messages_to_process)} new messages to clone.")

        media_group_cache: Dict[int, List[Message]] = {}

        for message in messages_to_process:
            try:
                # FIX: Handle media groups correctly
                if message.grouped_id:
                    if message.grouped_id not in media_group_cache:
                        media_group_cache[message.grouped_id] = []
                    media_group_cache[message.grouped_id].append(message)
                    continue # Skip to the next message, we'll send the group later

                # Send any completed media groups that came before this single message
                if media_group_cache:
                    for group_id, group_messages in list(media_group_cache.items()):
                        group_messages.sort(key=lambda m: m.id)
                        print(f"Cloning media group {group_id} with {len(group_messages)} items.")
                        
                        reply_to_id = id_map.get(group_messages[0].reply_to_msg_id) if group_messages[0].reply_to else None
                        
                        sent_group = await send_with_retry(
                            client, state, id_map,
                            entity=destination_entity,
                            file=[m.media for m in group_messages],
                            caption=[m.text for m in group_messages],
                            reply_to=reply_to_id
                        )
                        
                        if sent_group and isinstance(sent_group, list):
                            for i, original_msg in enumerate(group_messages):
                                self.id_map[original_msg.id] = sent_group[i].id
                        
                        del media_group_cache[group_id]
                        await asyncio.sleep(DELAY_SECONDS) # Add delay after sending a group

                # Process the current single message
                print(f"Cloning single message ID: {message.id}")
                reply_to_id = id_map.get(message.reply_to.reply_to_msg_id) if message.reply_to else None
                
                sent_message = await send_with_retry(
                    client, state, id_map,
                    entity=destination_entity,
                    message=message,
                    reply_to=reply_to_id,
                    link_preview=False
                )

                if sent_message and isinstance(sent_message, Message):
                    id_map[message.id] = sent_message.id
                
                await asyncio.sleep(DELAY_SECONDS) # Add delay after sending a single message

            except Exception as e:
                print(f"CRITICAL ERROR processing message {message.id}: {e}")
            finally:
                # Always update the last message ID to ensure we don't re-process it
                state["last_message_id"] = max(state.get("last_message_id", 0), message.id)

        # Send any remaining media groups at the very end
        for group_id, group_messages in media_group_cache.items():
            group_messages.sort(key=lambda m: m.id)
            print(f"Cloning final media group {group_id} with {len(group_messages)} items.")
            reply_to_id = id_map.get(group_messages[0].reply_to_msg_id) if group_messages[0].reply_to else None
            sent_group = await send_with_retry(
                client, state, id_map,
                entity=destination_entity,
                file=[m.media for m in group_messages],
                caption=[m.text for m in group_messages],
                reply_to=reply_to_id
            )
            if sent_group and isinstance(sent_group, list):
                for i, original_msg in enumerate(group_messages):
                    id_map[original_msg.id] = sent_group[i].id
            state["last_message_id"] = max(state.get("last_message_id", 0), group_messages[-1].id)
            await asyncio.sleep(DELAY_SECONDS)

        # Final save of our progress
        save_json_file(STATE_FILE, state)
        save_json_file(ID_MAP_FILE, id_map)
        print("\n✅ Cloning run finished successfully.")


if __name__ == "__main__":
    asyncio.run(main())
