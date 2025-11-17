import os
import discord
from discord.ext import commands, tasks
import openai
import requests
from dotenv import load_dotenv
import asyncio

load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PERSONALITY_URL = os.getenv("PROMPT_URL")  # URL for personality prompt
YOUR_USERNAME = os.getenv("USERNAME")  # Username to use for console messages

openai.api_key = OPENAI_API_KEY

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Load personality prompt
def load_prompt():
    try:
        response = requests.get(PERSONALITY_URL)
        response.raise_for_status()
        return response.text
    except:
        return "You are a helpful assistant."

# Conversation history per channel
# {channel_id: [{"role": "user"/"assistant", "content": "..."}, ...]}
conversation_history = {}

# Limit the number of messages stored to avoid hitting token limits
MAX_HISTORY = 20

@bot.event
async def on_ready():
    print(f"{bot.user.name} is online!")
    # Start the console input loop

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    # Check if the bot is mentioned
    if bot.user in message.mentions:
        await handle_message(message.channel, f"{message.author.name}: {message.content}")

    await bot.process_commands(message)

async def handle_message(channel, user_message):
    """Send a message to OpenAI and post the response in the channel."""
    system_prompt = load_prompt()

    # Initialize conversation history for this channel
    if channel.id not in conversation_history:
        conversation_history[channel.id] = [{"role": "system", "content": system_prompt}]

    # Append user message
    conversation_history[channel.id].append({"role": "user", "content": user_message})

    # Keep history within MAX_HISTORY
    if len(conversation_history[channel.id]) > MAX_HISTORY:
        # Keep system prompt + last MAX_HISTORY messages
        conversation_history[channel.id] = [conversation_history[channel.id][0]] + conversation_history[channel.id][-MAX_HISTORY:]

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=conversation_history[channel.id],
            max_tokens=250,
            temperature=0.7
        )
        reply = response.choices[0].message["content"]

        # Append assistant response to history
        conversation_history[channel.id].append({"role": "assistant", "content": reply})

        # Send response to Discord
        await channel.send(reply)

    except Exception as e:
        await channel.send(f"⚠ Error: {e}")

bot.run(DISCORD_TOKEN)
