import discord
import toml
import os
import sys
from discord.ext import commands

def load_config():
    """Load configuration from config.toml file"""
    config_path = "config.toml"
    
    if not os.path.exists(config_path):
        print(f"Error: Configuration file '{config_path}' not found!")
        print("Please create a config.toml file with your bot token.")
        sys.exit(1)
    
    try:
        with open(config_path, 'r') as f:
            config = toml.load(f)
        return config
    except Exception as e:
        print(f"Error loading configuration: {e}")
        sys.exit(1)

def main():
    """Main function to initialize and run the bot"""
    # Load configuration
    config = load_config()
    
    # Get token from config
    token = config.get('bot', {}).get('token')
    if not token or token == "YOUR_BOT_TOKEN":
        print("Error: Please set a valid bot token in config.toml")
        sys.exit(1)
    
    # Get bot prefix from config (default to '!')
    prefix = config.get('bot', {}).get('prefix', '!')
    
    # Set up bot intents
    intents = discord.Intents.default()
    intents.message_content = True
    
    # Create bot instance
    bot = commands.Bot(command_prefix=prefix, intents=intents)
    
    @bot.event
    async def on_ready():
        """Event fired when bot is ready"""
        print(f'{bot.user} has connected to Discord!')
        print(f'Bot is ready and using prefix: {prefix}')
    
    @bot.command(name='ping')
    async def ping(ctx):
        """Simple ping command to test bot functionality"""
        await ctx.send('Pong!')
    
    @bot.command(name='hello')
    async def hello(ctx):
        """Hello command"""
        await ctx.send(f'Hello {ctx.author.mention}! I am {bot.user.name}.')
    
    # Run the bot
    try:
        bot.run(token)
    except discord.LoginFailure:
        print("Error: Invalid bot token. Please check your config.toml file.")
    except Exception as e:
        print(f"Error running bot: {e}")

if __name__ == "__main__":
    main()