from pathlib import Path
from config.logger import Logger
from lifecycle.lifespan_manager import RELOADING_FLAG_PATH

logger = Logger()

def reload_with_flag_handler(self):
    def _display_path(path):
        try:
            return f"'{path.relative_to(Path.cwd())}'"
        except ValueError:
            return f"'{path}'"

    self.startup()
    
    for changes in self:
        if changes:
            logger.warning(
                "%s detected changes in %s. Reloading...",
                self.reloader_name,
                ", ".join(_display_path(path) for path in changes),
            )
            RELOADING_FLAG_PATH.touch()
            self.restart()
    
    self.shutdown()