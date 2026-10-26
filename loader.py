import importlib
import inspect
from pathlib import Path

PLUGINS_DIR = Path(__file__).resolve().parent / "plugins"


def load_all_plugins(client):
    """
    Dynamically loads all plugins in the plugins directory
    and registers their event handlers with the Telethon client.
    """
    loaded_count = 0

    for file_path in PLUGINS_DIR.glob("*.py"):
        if file_path.name == "__init__.py":
            continue

        module_name = f"plugins.{file_path.stem}"
        try:
            module = importlib.import_module(module_name)

            # Register standard command handlers decorated with @register_cmd
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if callable(attr) and hasattr(attr, "__userbot_event__"):
                    client.add_event_handler(attr, attr.__userbot_event__)

            # Special case for plugin-level listener setups (e.g. AFK watcher, mention logger, forwarder, keyword watcher)
            if hasattr(module, "register_afk_listeners"):
                module.register_afk_listeners(client)
            if hasattr(module, "register_tag_logger"):
                module.register_tag_logger(client)
            if hasattr(module, "register_forwarder_listeners"):
                module.register_forwarder_listeners(client)
            if hasattr(module, "register_watcher_listeners"):
                module.register_watcher_listeners(client)
            if hasattr(module, "setup_listeners"):
                module.setup_listeners(client)


            loaded_count += 1
            print(f"  [+] Loaded module: {file_path.stem}")
        except Exception as e:
            print(f"  [-] Failed to load {module_name}: {e}")

    return loaded_count
