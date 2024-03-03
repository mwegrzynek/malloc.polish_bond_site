import datetime as dt
import json
from pathlib import Path
import shutil
import logging


import requests
from dateutil.relativedelta import relativedelta
from pydantic_settings import BaseSettings


from malloc.polish_bond import BondMaker, DatasetInfo



_logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    cache_path: Path = ".cache"
    log_level: str = "DEBUG"


class SiteBondMaker:

    def __init__(self, settings: Settings) -> None:
        _logger.debug(f"Creating SiteBondMaker")
        self.settings = settings
        
        # Try to create directory if it doesn't exist.
        if not self.settings.cache_path.exists():
            _logger.debug(f"Creating cache directory {self.settings.cache_path}")
            self.settings.cache_path.mkdir(exist_ok=True, parents=True)
                
        self._ds_info = None
        self._bond_maker = None

        self._ds_file_cache_path = self.settings.cache_path / "ds.xls"                
        self._ds_info_cache_path = self.settings.cache_path / "ds.json"
        
        self.refresh()
            
    def refresh(self) -> None:
        """Refresh the bond maker."""
        fetch_dataset = False

        if self._ds_info_cache_path.exists():
            _logger.debug(f"Loading dataset info from {self._ds_info_cache_path}")
            
            self._ds_info = DatasetInfo(**json.load(self._ds_info_cache_path.open()))

            if self._ds_info.data_date + relativedelta(months=2) < dt.date.today():
                # Data is older than a month, ignore cache
                self._ds_info = None
                fetch_dataset = True

        if self._ds_info is None:            
            self._ds_info = DatasetInfo.get_dataset_info()

            with open(self._ds_info_cache_path, "w") as f:
                f.write(self._ds_info.model_dump_json())
            
            fetch_dataset = True
                        
        # We have the dataset info, now we need to get the dataset.                
        if fetch_dataset or not self._ds_file_cache_path.exists():
            # Get the dataset if it doesn't exist or is older than a month.

            # Stolen from: https://stackoverflow.com/questions/16694907/download-large-file-in-python-with-requests
            with requests.get(self._ds_info.file_url, stream=True) as r:
                with open(self._ds_file_cache_path, "wb") as f:
                    shutil.copyfileobj(r.raw, f)

        self._bond_maker = BondMaker(self._ds_file_cache_path)

    def __call__(self) -> BondMaker:
        """Return a bond maker. """
        return self._bond_maker
