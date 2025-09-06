import discord
import toml
import os
import sys
import importlib.util
from types import ModuleType
from discord.ext import commands

PLUGINS_DIR = "plugins"
CONFIG_ROOT = "config"  # Root directory for per-plugin configs / local data

def ensure_root_dirs():
    """Ensure the main directories used by the bot exist (plugins, config)."""
    if not os.path.exists(PLUGINS_DIR):
        os.makedirs(PLUGINS_DIR, exist_ok=True)
        print(f"[init] Created '{PLUGINS_DIR}' directory.")
    if not os.path.exists(CONFIG_ROOT):
        os.makedirs(CONFIG_ROOT, exist_ok=True)
        print(f"[init] Created '{CONFIG_ROOT}' directory for plugin data.")

def discover_plugin_paths():
    """Return list of plugin directory paths containing a plugin.toml file."""
    paths = []
    if not os.path.isdir(PLUGINS_DIR):
        return paths
    for entry in os.listdir(PLUGINS_DIR):
        full = os.path.join(PLUGINS_DIR, entry)
        if os.path.isdir(full):
            plugin_toml = os.path.join(full, "plugin.toml")
            if os.path.isfile(plugin_toml):
                paths.append(full)
    return paths

def load_plugin_metadata(plugin_dir):
    """Load and validate plugin.toml metadata."""
    plugin_toml = os.path.join(plugin_dir, "plugin.toml")
    try:
        with open(plugin_toml, 'r') as f:
            data = toml.load(f)
    except Exception as e:
        print(f"[plugins] Failed to read {plugin_toml}: {e}")
        return None

    meta = data.get('plugin', {})
    name = meta.get('name') or os.path.basename(plugin_dir)
    main_file = meta.get('main')  # expected relative path e.g. main.py
    enabled = meta.get('enabled', True)
    if not main_file:
        print(f"[plugins] Plugin '{name}' missing 'plugin.main' in plugin.toml, skipping.")
        return None
    return {
        'name': name,
        'main': main_file,
        'enabled': enabled,
        'dir': plugin_dir,
        'raw': data,
    }

def import_plugin_module(plugin_meta) -> ModuleType | None:
    """Dynamically import a plugin's main module given metadata."""
    main_rel = plugin_meta['main']
    plugin_dir = plugin_meta['dir']
    main_path = os.path.join(plugin_dir, main_rel)
    if not os.path.isfile(main_path):
        print(f"[plugins] Main file '{main_rel}' not found for plugin '{plugin_meta['name']}'.")
        return None
    module_name = f"plugin_{plugin_meta['name']}"
    try:
        spec = importlib.util.spec_from_file_location(module_name, main_path)
        if spec is None or spec.loader is None:
            print(f"[plugins] Could not create spec for '{main_path}'.")
            return None
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)  # type: ignore[attr-defined]
        return module
    except Exception as e:
        print(f"[plugins] Error importing plugin '{plugin_meta['name']}': {e}")
        return None

async def unload_plugin(bot: commands.Bot, name: str) -> bool:
    """Unload a loaded plugin by name. Returns True if unloaded."""
    registry = getattr(bot, 'plugins', {})
    entry = registry.get(name)
    if not entry:
        return False
    module: ModuleType = entry['module']
    meta = entry['meta']
    teardown_fn = getattr(module, 'teardown', None)
    if teardown_fn:
        try:
            result = teardown_fn(bot)
            if hasattr(result, '__await__'):
                await result
        except Exception as e:
            print(f"[plugins] Error in teardown() for '{name}': {e}")
    # Attempt to remove cogs automatically if the plugin declared a list PLUGIN_COGS
    for cog_name in list(getattr(module, 'PLUGIN_COGS', [])):
        if cog_name in bot.cogs:
            try:
                bot.remove_cog(cog_name)
            except Exception:
                pass
    # Remove from registry
    registry.pop(name, None)
    # Remove imported module
    module_mod_name = None
    for mod_name, mod in list(sys.modules.items()):
        if mod is module:
            module_mod_name = mod_name
            break
    if module_mod_name:
        sys.modules.pop(module_mod_name, None)
    print(f"[plugins] Unloaded plugin '{name}'.")
    return True

async def load_plugin(bot: commands.Bot, name: str) -> bool:
    """Load a plugin by folder name if not already loaded. Returns True if loaded."""
    registry = getattr(bot, 'plugins', {})
    if name in registry:
        return False
    plugin_dir = os.path.join(PLUGINS_DIR, name)
    if not os.path.isdir(plugin_dir):
        print(f"[plugins] Cannot load '{name}': directory not found.")
        return False
    meta = load_plugin_metadata(plugin_dir)
    if not meta:
        return False
    module = import_plugin_module(meta)
    if not module:
        return False
    await initialize_plugin(module, bot, meta)
    registry[name] = {'module': module, 'meta': meta}
    return True

async def restart_plugin(bot: commands.Bot, name: str) -> bool:
    """Restart (unload then load) a plugin."""
    unloaded = await unload_plugin(bot, name)
    loaded = await load_plugin(bot, name)
    return unloaded and loaded

async def initialize_plugin(module: ModuleType, bot: commands.Bot, plugin_meta: dict):
    """Call setup(bot, config_dir?) if present; create per-plugin config directory."""
    # Prepare per-plugin config directory
    plugin_name = plugin_meta['name']
    config_dir = os.path.join(CONFIG_ROOT, plugin_name)
    os.makedirs(config_dir, exist_ok=True)
    plugin_meta['config_dir'] = config_dir
    # Expose to module namespace for convenience
    setattr(module, 'PLUGIN_CONFIG_DIR', config_dir)

    setup_fn = getattr(module, 'setup', None)
    if setup_fn is None:
        print(f"[plugins] Plugin '{plugin_name}' has no setup() function. Loaded module only.")
        return
    try:
        # Support optional second parameter for config path
        if setup_fn.__code__.co_argcount >= 2:  # type: ignore[attr-defined]
            result = setup_fn(bot, config_dir)
        else:
            result = setup_fn(bot)
        if hasattr(result, '__await__'):
            await result  # support async setup
        print(f"[plugins] Plugin '{plugin_name}' setup complete (config at {config_dir}).")
    except Exception as e:
        print(f"[plugins] Error running setup() for '{plugin_name}': {e}")

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
    # Ensure plugins directory exists as early as possible
    ensure_root_dirs()

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

        # Discover and load plugins after bot is ready (so bot is usable inside setup)
        plugin_dirs = discover_plugin_paths()
        if not plugin_dirs:
            print("[plugins] No plugins found.")
            return
        print(f"[plugins] Found {len(plugin_dirs)} plugin candidate(s). Loading...")
        bot.plugins = {}  # simple registry
        # Expose management helpers
        bot.plugin_unload = lambda n: unload_plugin(bot, n)
        bot.plugin_load = lambda n: load_plugin(bot, n)
        bot.plugin_restart = lambda n: restart_plugin(bot, n)
        for pdir in plugin_dirs:
            meta = load_plugin_metadata(pdir)
            if not meta:
                continue
            if not meta['enabled']:
                print(f"[plugins] Plugin '{meta['name']}' disabled (enabled=false). Skipping.")
                continue
            module = import_plugin_module(meta)
            if module:
                await initialize_plugin(module, bot, meta)
                bot.plugins[meta['name']] = {'module': module, 'meta': meta}
    
    # Run the bot
    try:
        bot.run(token)
    except discord.LoginFailure:
        print("Error: Invalid bot token. Please check your config.toml file.")
    except Exception as e:
        print(f"Error running bot: {e}")

if __name__ == "__main__":
    main()