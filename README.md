# hybicraft-bot

A Discord bot built with pycord that loads configuration from a TOML file.

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Create your configuration file:
   ```bash
   cp config.example.toml config.toml
   ```

3. Edit `config.toml` and replace `YOUR_BOT_TOKEN_HERE` with your actual Discord bot token.

4. Run the bot:
   ```bash
   python main.py
   ```

## Configuration

The bot loads its configuration from `config.toml`. The structure is:

```toml
[bot]
token = "YOUR_BOT_TOKEN_HERE"
prefix = "!"

[settings]
debug = false
```

## Commands

- `!ping` - Responds with "Pong!"
- `!hello` - Greets the user