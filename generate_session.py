import os
from telethon.sync import TelegramClient
from telethon.sessions import StringSession

print("--- Telethon Session String Generator ---")
print("You will be asked for your API ID, API Hash, and phone number.")
print("This script will NOT save them. It only prints a session string.")

API_ID = input("Enter your API ID: ")
API_HASH = input("Enter your API Hash: ")

with TelegramClient(StringSession(), int(API_ID), API_HASH) as client:
    session_string = client.session.save()
    print("\n✅ Your session string has been generated successfully!")
    print("--- COPY THE STRING BELOW ---")
    print(session_string)
    print("\n⚠️ Keep this string safe and store it in your GitHub repository's secrets as SESSION_STRING.")
