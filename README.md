# hybicraft-bot

A Discord bot built with pycord that loads configuration from a TOML file.

## Setup

1. Install dependencies:
   ```bash
   uv sync
   ```

2. Create your configuration file:
   ```bash
   cp config.example.toml config.toml
   ```

3. Edit `config.toml` and replace `YOUR_BOT_TOKEN_HERE` with your actual Discord bot token.

4. Run the bot:
   ```bash
   uv run python main.py
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

## Plugins

On startup the bot ensures a `plugins/` directory exists. Each plugin lives in its own subfolder:

```
plugins/
   my_plugin/
      plugin.toml
      main.py        # entry point referenced by plugin.toml

config/
   my_plugin/       # auto-created per-plugin data/config folder
      (plugin-specific files)
```

`plugin.toml` format (minimal):

```toml
[plugin]
name = "my_plugin"      # Optional (defaults to folder name)
main = "main.py"         # Required: relative path to the plugin entry file
enabled = true           # Optional (default true)

[about]
description = "My awesome plugin"
version = "0.1.0"
author = "me"
```

Entry module (`main.py`) can optionally expose:

```
def setup(bot, config_dir: str):
   # Register cogs/commands here using config_dir for persistence
   ...
```

Example provided in `plugins/example_plugin` adding a simple `ping` command.

Future ideas (not yet implemented):
* Dependency enforcement using `[requires]` table
* Hot reload commands
* Version & compatibility checks
* Slash command auto-registration
* Descarga de plugins remotos (slash `/plugin_download repo:<owner/repo>`)