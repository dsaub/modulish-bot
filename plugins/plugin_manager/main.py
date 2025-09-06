import os
import asyncio
import discord
from discord.ext import commands
from discord import option

try:
    from .downloader import install_repo_as_plugin, DownloadError  # when package context exists
except Exception:
    # Fallback when loaded as loose files with sys.path tweaked by loader
    from downloader import install_repo_as_plugin, DownloadError  # type: ignore

ACTIONS = ["restart", "stop", "start"]

class PluginManager(commands.Cog):
    def __init__(self, bot: commands.Bot, config_dir: str):
        self.bot = bot
        self.config_dir = config_dir
        print("[plugin_manager] initialized")

    async def autocomplete_plugin_names(self, ctx: discord.AutocompleteContext):
        # Suggest loaded plugins first, then available folders
        partial = ctx.value.lower() if ctx.value else ""
        loaded = list(getattr(self.bot, 'plugins', {}).keys())
        all_dirs = []
        plugins_root = 'plugins'
        try:
            for entry in os.listdir(plugins_root):
                full = os.path.join(plugins_root, entry)
                if os.path.isdir(full) and os.path.isfile(os.path.join(full, 'plugin.toml')):
                    all_dirs.append(entry)
        except FileNotFoundError:
            pass
        # merge preserving order: loaded first then others
        ordered = loaded + [d for d in all_dirs if d not in loaded]
        return [name for name in ordered if partial in name.lower()][:25]

    @discord.slash_command(name="plugin", description="Manage plugins (start/stop/restart)")
    @option("plugin", description="Plugin name", autocomplete=autocomplete_plugin_names)
    @option("accion", description="Action", choices=ACTIONS)
    async def plugin_command(self, ctx: discord.ApplicationContext, plugin: str, accion: str):
        await ctx.defer(ephemeral=True)
        bot = self.bot
        # Ensure registry exists
        if not hasattr(bot, 'plugins'):
            bot.plugins = {}
        action = accion.lower()
        # Map actions
        if action == 'restart':
            ok = await bot.plugin_restart(plugin)
            if ok:
                await ctx.respond(f"🔄 Plugin '{plugin}' restarted.")
            else:
                await ctx.respond(f"⚠️ Could not restart '{plugin}'. Does it exist?")
        elif action == 'stop':
            ok = await bot.plugin_unload(plugin)
            if ok:
                await ctx.respond(f"🛑 Plugin '{plugin}' stopped.")
            else:
                await ctx.respond(f"⚠️ Could not stop '{plugin}'. Is it loaded?")
        elif action == 'start':
            ok = await bot.plugin_load(plugin)
            if ok:
                await ctx.respond(f"✅ Plugin '{plugin}' started.")
            else:
                await ctx.respond(f"⚠️ Could not start '{plugin}'. Already loaded or not found?")
        else:
            await ctx.respond("Unknown action.")

    @discord.slash_command(name="plugin_download", description="Download (and optionally load) a plugin from GitHub owner/repo[@branch]")
    @option("repo", description="Spec owner/repo or owner/repo@branch")
    @option("cargar", description="Load after download", choices=["si","no"], required=False)
    async def plugin_download(self, ctx: discord.ApplicationContext, repo: str, cargar: str = "si"):
        await ctx.defer(ephemeral=True)
        spec = repo.strip()
        await ctx.followup.send(f"⬇️ Downloading '{spec}'...", ephemeral=True)
        try:
            await asyncio.to_thread(install_repo_as_plugin, spec)
            repo_name = spec.split('@', 1)[0].split('/')[-1]
            if cargar.lower() == 'si':
                loaded = await self.bot.plugin_load(repo_name)
                if loaded:
                    await ctx.respond(f"✅ Plugin '{repo_name}' downloaded and loaded.")
                else:
                    await ctx.respond(f"⚠️ Downloaded but could not load '{repo_name}'. Already loaded?")
            else:
                await ctx.respond(f"✅ Plugin '{repo_name}' downloaded (not loaded by request)")
        except DownloadError as e:
            await ctx.respond(f"❌ Download error: {e}")
        except Exception as e:
            await ctx.respond(f"❌ Unexpected error: {e}")

# record cogs for potential auto-removal on unload
PLUGIN_COGS = ["PluginManager"]

def setup(bot: commands.Bot, config_dir: str = None):
    if config_dir is None:
        config_dir = globals().get('PLUGIN_CONFIG_DIR', '<unknown>')
    bot.add_cog(PluginManager(bot, config_dir))
    print("[plugin_manager] setup complete")
