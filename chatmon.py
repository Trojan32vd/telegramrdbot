from telethon import TelegramClient, events, errors
import asyncio
import re
from dataclasses import dataclass
from typing import List
from datetime import datetime
import os
import keyboard
import threading
from asyncio import create_task

# Your API credentials
api_id = 25103058  # Changed to int
api_hash = '527090194b3e9c5ea0a7ce111080f707'
phone_number = '+393202858868'
CHANNEL_ID = 'trading1001off'
SESSION_FILE = 'session_name.session'

# Global flag for shutdown
shutdown_flag = False

@dataclass
class Signal:
    symbol: str
    buy_threshold: float
    targets: List[float]
    base_asset: str
    quote_asset: str
    timestamp: datetime

# Global list to store signals
signals = []

def clean_and_translate_message(arabic_text: str) -> str:
    """Translates and cleans the message format from Arabic to English."""
    translations = {
        "تنبيه بإشارة جديدة": "New Signal Alert",
        "معرف الإشارة الجديد": "Signal ID",
        "الرمز": "Symbol",
        "الشراء عند": "Buy at",
        "هدف": "Target",
        "وقف الخسارة": "Stop Loss",
        "مدة الصفقة": "Duration",
        "الحكم": "Status",
        "تم النشر بواسطة": "Published by",
        "أو أقل": "or lower",
        "ساعات تحت": "hours below",
        "أيام": "days",
        "حلال": "Halal"
    }
    
    # First translate the text
    translated_text = arabic_text
    for ar, en in translations.items():
        translated_text = translated_text.replace(ar, en)
    
    # Remove asterisks
    translated_text = translated_text.replace('*', '')
    
    # Clean up the text (remove emojis and extra whitespace)
    emoji_pattern = re.compile("["
                             u"\U0001F600-\U0001F64F"  # emoticons
                             u"\U0001F300-\U0001F5FF"  # symbols & pictographs
                             u"\U0001F680-\U0001F6FF"  # transport & map symbols
                             u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
                             u"\U00002702-\U000027B0"
                             u"\U000024C2-\U0001F251"
                             "]+", flags=re.UNICODE)
    
    translated_text = emoji_pattern.sub('', translated_text)
    
    # Clean up newlines and spaces
    lines = [line.strip() for line in translated_text.split('\n') if line.strip()]
    translated_text = '\n'.join(lines)
    
    return translated_text

def extract_signal_info(message: str) -> Signal:
    """Extracts signal information from the message text."""
    # First clean and translate the message
    cleaned_text = clean_and_translate_message(message)
    print("\nCleaned and Translated Message:")
    print(cleaned_text)
    
    try:
        # Extract Symbol (e.g., "LTO/USDT")
        symbol_match = re.search(r"Symbol: ([A-Z]+)/([A-Z]+)", cleaned_text)
        if symbol_match:
            base_asset = symbol_match.group(1)
            quote_asset = symbol_match.group(2)
            symbol = f"{base_asset}{quote_asset}"
            
            # Extract Buy Price
            buy_match = re.search(r"Buy at: ([\d.]+)", cleaned_text)
            buy_threshold = float(buy_match.group(1)) if buy_match else 0.0
            
            # Extract Targets
            targets = []
            target_pattern = r"Target \d+: ([\d.]+)"
            target_matches = re.findall(target_pattern, cleaned_text)
            targets = [float(price) for price in target_matches]
            
            # Create signal object
            signal = Signal(
                symbol=symbol,
                buy_threshold=buy_threshold,
                targets=targets,
                base_asset=base_asset,
                quote_asset=quote_asset,
                timestamp=datetime.now()
            )
            
            # Format output
            output = (
                f'symbol="{symbol}" '
                f'buy_threshold={buy_threshold} '
                f'target1={targets[0] if len(targets) > 0 else 0.0} '
                f'target2={targets[1] if len(targets) > 1 else 0.0} '
                f'target3={targets[2] if len(targets) > 2 else 0.0} '
                f'target4={targets[3] if len(targets) > 3 else 0.0} '
                f'target5={targets[4] if len(targets) > 4 else 0.0} '
                f'target6={targets[5] if len(targets) > 5 else 0.0} '
                f'base_asset="{base_asset}" '
                f'quote_asset="{quote_asset}"'
            )
            
            print("\nFormatted Output:")
            print(output)
            
            return signal
            
        else:
            print("Failed to match symbol pattern")
            return None
            
    except Exception as e:
        print(f"Error in extraction: {str(e)}")
        return None

async def verify_channel(client, channel_id):
    try:
        channel = await client.get_entity(channel_id)
        print(f"Successfully connected to channel: {getattr(channel, 'title', channel_id)}")
        return channel
    except Exception as e:
        print(f"Error accessing channel: {str(e)}")
        return None

async def search_previous_signals(client, channel):
    print("\nSearching for previous signal messages...")
    
    if not channel:
        print("Error: No valid channel provided for searching messages.")
        return
    
    try:
        messages = await client.get_messages(channel, limit=100)
        
        signal_found = False
        for message in messages:
            if not message or not message.text:
                continue
                
            if "تنبيه بإشارة جديدة" in message.text:
                signal_found = True
                print("\nFound signal message:")
                print("-" * 50)
                print(f"Message:\n{message.text}")
                print("-" * 50)
                
                signal = extract_signal_info(message.text)
                if signal:
                    signals.append(signal)
                    break
        
        if not signal_found:
            print("No signal messages found in the recent messages")
            
    except Exception as e:
        print(f"Error searching messages: {str(e)}")

async def logout_and_cleanup():
    """Logout and clean up session files."""
    try:
        print("\nLogging out and cleaning up...")
        
        # Disconnect the main client
        await client.disconnect()
        
        # If there's an existing session file, remove it
        if os.path.exists(SESSION_FILE):
            try:
                os.remove(SESSION_FILE)
                print(f"Removed session file: {SESSION_FILE}")
            except Exception as e:
                print(f"Error removing session file: {str(e)}")
        
        print("Cleanup completed successfully.")
        
    except Exception as e:
        print(f"Error during logout and cleanup: {str(e)}")

def check_f10():
    """Monitor F10 key press."""
    global shutdown_flag
    while True:
        if keyboard.is_pressed('f10'):
            print("\nF10 pressed - initiating shutdown...")
            shutdown_flag = True
            break
        asyncio.sleep(0.1)

# Create the Telegram client
client = TelegramClient('session_name', api_id, api_hash)

@client.on(events.NewMessage(chats=CHANNEL_ID))
async def handle_new_message(event):
    if "تنبيه بإشارة جديدة" in event.message.text:
        signal = extract_signal_info(event.message.text)
        if signal:
            signals.append(signal)

async def main():
    global shutdown_flag
    try:
        # Start F10 monitoring in a separate thread
        keyboard_thread = threading.Thread(target=check_f10, daemon=True)
        keyboard_thread.start()
        
        print("Connecting to Telegram...")
        await client.start(phone=phone_number)
        print("Connected!")
        print("\nPress F10 to logout and exit.")
        
        channel = await verify_channel(client, CHANNEL_ID)
        if not channel:
            print("Could not verify channel. Please check the channel ID/username and your access.")
            return
            
        await search_previous_signals(client, channel)
        
        print("\nNow listening for new signals...")
        
        # Main loop
        while not shutdown_flag:
            await asyncio.sleep(1)
            
        # If shutdown flag is set, perform cleanup
        await logout_and_cleanup()
        
    except Exception as e:
        print(f"Main loop error: {str(e)}")
    finally:
        # Ensure we're disconnected
        if client.is_connected():
            await client.disconnect()

if __name__ == '__main__':
    try:
        with client:
            client.loop.run_until_complete(main())
    except KeyboardInterrupt:
        print("\nBot stopped by user")
    finally:
        print("Bot shutdown complete")