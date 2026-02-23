"""Commission Rate Manager.

Provides version control and management for commission rates.
Supports importing from files, URLs, and manual editing.
Tracks change history with timestamps.
"""

import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
import yaml
import requests


class RateManager:
    """Manages commission rates with version control."""
    
    def __init__(self, config_dir: Optional[Path] = None):
        """Initialize rate manager.
        
        Args:
            config_dir: Path to config directory. Auto-detected if None.
        """
        if config_dir is None:
            config_dir = self._find_config_dir()
        
        self.config_dir = Path(config_dir)
        self.rates_file = self.config_dir / "commission_rates.yaml"
        self.history_file = self.config_dir / "rate_history.json"
        self.sources_file = self.config_dir / "rate_sources.yaml"
        
        # Ensure files exist
        self._ensure_history_file()
        self._ensure_sources_file()
    
    def _find_config_dir(self) -> Path:
        """Find the config directory."""
        possible_paths = [
            Path(__file__).parent.parent.parent / "config",
            Path("config"),
            Path(__file__).parent.parent / "config",
        ]
        for path in possible_paths:
            if path.exists():
                return path
        raise FileNotFoundError("Config directory not found")
    
    def _ensure_history_file(self):
        """Create history file if it doesn't exist."""
        if not self.history_file.exists():
            self.history_file.write_text(json.dumps({
                "version": 1,
                "created": datetime.now().isoformat(),
                "changes": []
            }, indent=2, ensure_ascii=False))
    
    def _ensure_sources_file(self):
        """Create sources file if it doesn't exist."""
        if not self.sources_file.exists():
            default_sources = {
                "sources": {
                    "manual": {
                        "name": "Manual Entry",
                        "type": "manual",
                        "description": "Rates entered manually in dashboard"
                    }
                },
                "last_check": None
            }
            with open(self.sources_file, 'w', encoding='utf-8') as f:
                yaml.dump(default_sources, f, allow_unicode=True, default_flow_style=False)
    
    def get_current_rates(self) -> Dict[str, Any]:
        """Load current commission rates."""
        if not self.rates_file.exists():
            return {}
        
        with open(self.rates_file, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    
    def get_rate_version_info(self) -> Dict[str, Any]:
        """Get version information about current rates."""
        if not self.rates_file.exists():
            return {"version": None, "last_updated": None, "checksum": None}
        
        content = self.rates_file.read_text(encoding='utf-8')
        checksum = hashlib.md5(content.encode()).hexdigest()[:8]
        
        # Get last updated from file
        config = self.get_current_rates()
        
        # Try to get last_updated from file comment or mtime
        mtime = datetime.fromtimestamp(self.rates_file.stat().st_mtime)
        
        return {
            "version": checksum,
            "last_updated": mtime.isoformat(),
            "file_path": str(self.rates_file),
            "bank_count": len(config.get("banks", {})),
            "anomaly_threshold": config.get("anomaly", {}).get("threshold", 0.005)
        }
    
    def get_change_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent change history.
        
        Args:
            limit: Maximum number of changes to return.
            
        Returns:
            List of change records.
        """
        if not self.history_file.exists():
            return []
        
        with open(self.history_file, 'r', encoding='utf-8') as f:
            history = json.load(f)
        
        return history.get("changes", [])[-limit:]
    
    def _add_to_history(self, change_type: str, details: Dict[str, Any], user: str = "system"):
        """Add a change to history.
        
        Args:
            change_type: Type of change (update, import, manual_edit)
            details: Change details
            user: User who made the change
        """
        history = {"version": 1, "created": datetime.now().isoformat(), "changes": []}
        
        if self.history_file.exists():
            with open(self.history_file, 'r', encoding='utf-8') as f:
                history = json.load(f)
        
        change_record = {
            "timestamp": datetime.now().isoformat(),
            "type": change_type,
            "user": user,
            "details": details
        }
        
        history["changes"].append(change_record)
        
        # Keep only last 100 changes
        history["changes"] = history["changes"][-100:]
        
        with open(self.history_file, 'w', encoding='utf-8') as f:
            json.dump(history, f, indent=2, ensure_ascii=False)
    
    def update_bank_rate(self, bank_key: str, installment: int, new_rate: float, 
                         user: str = "dashboard") -> bool:
        """Update a single rate for a bank.
        
        Args:
            bank_key: Bank identifier (e.g., 'vakifbank', 'ziraat')
            installment: Installment count (1 = Peşin)
            new_rate: New commission rate as decimal
            user: User making the change
            
        Returns:
            True if successful
        """
        config = self.get_current_rates()
        
        if "banks" not in config:
            config["banks"] = {}
        
        if bank_key not in config["banks"]:
            return False
        
        old_rate = config["banks"][bank_key].get("rates", {}).get(installment)
        config["banks"][bank_key]["rates"][installment] = new_rate
        
        # Save updated config
        with open(self.rates_file, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
        
        # Log change
        self._add_to_history("rate_update", {
            "bank": bank_key,
            "installment": installment,
            "old_rate": old_rate,
            "new_rate": new_rate
        }, user)
        
        # Clear cache
        self._clear_rates_cache()
        
        return True
    
    def update_all_bank_rates(self, bank_key: str, rates: Dict[int, float], 
                              user: str = "dashboard") -> bool:
        """Update all rates for a bank.
        
        Args:
            bank_key: Bank identifier
            rates: Dict of installment -> rate
            user: User making the change
            
        Returns:
            True if successful
        """
        config = self.get_current_rates()
        
        if "banks" not in config or bank_key not in config["banks"]:
            return False
        
        old_rates = config["banks"][bank_key].get("rates", {}).copy()
        config["banks"][bank_key]["rates"] = rates
        
        # Save updated config
        with open(self.rates_file, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
        
        # Log change
        changes = []
        for inst, new_rate in rates.items():
            old_rate = old_rates.get(inst)
            if old_rate != new_rate:
                changes.append({
                    "installment": inst,
                    "old_rate": old_rate,
                    "new_rate": new_rate
                })
        
        if changes:
            self._add_to_history("bulk_rate_update", {
                "bank": bank_key,
                "changes": changes,
                "change_count": len(changes)
            }, user)
        
        # Clear cache
        self._clear_rates_cache()
        
        return True
    
    def import_from_file(self, file_path: str, user: str = "dashboard") -> Dict[str, Any]:
        """Import rates from a YAML or CSV file.
        
        Args:
            file_path: Path to the file
            user: User performing import
            
        Returns:
            Import result with status and details
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            return {"success": False, "error": f"File not found: {file_path}"}
        
        try:
            if file_path.suffix in ['.yaml', '.yml']:
                return self._import_yaml(file_path, user)
            elif file_path.suffix == '.csv':
                return self._import_csv(file_path, user)
            else:
                return {"success": False, "error": f"Unsupported file type: {file_path.suffix}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _import_yaml(self, file_path: Path, user: str) -> Dict[str, Any]:
        """Import rates from YAML file."""
        with open(file_path, 'r', encoding='utf-8') as f:
            new_config = yaml.safe_load(f)
        
        if not new_config or "banks" not in new_config:
            return {"success": False, "error": "Invalid YAML structure - missing 'banks' key"}
        
        # Validate rates
        validation_errors = self._validate_rates_config(new_config)
        if validation_errors:
            return {"success": False, "error": f"Validation errors: {validation_errors}"}
        
        # Backup current config
        old_config = self.get_current_rates()
        backup_path = self.config_dir / f"commission_rates.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}.yaml"
        with open(backup_path, 'w', encoding='utf-8') as f:
            yaml.dump(old_config, f, allow_unicode=True, default_flow_style=False)
        
        # Save new config
        with open(self.rates_file, 'w', encoding='utf-8') as f:
            yaml.dump(new_config, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
        
        # Log change
        self._add_to_history("file_import", {
            "source_file": str(file_path),
            "backup_file": str(backup_path),
            "bank_count": len(new_config.get("banks", {}))
        }, user)
        
        # Clear cache
        self._clear_rates_cache()
        
        return {
            "success": True,
            "message": f"Imported rates from {file_path.name}",
            "bank_count": len(new_config.get("banks", {})),
            "backup_created": str(backup_path)
        }
    
    def _import_csv(self, file_path: Path, user: str) -> Dict[str, Any]:
        """Import rates from CSV file.
        
        Expected CSV format:
        bank_key,installment,rate
        vakifbank,1,0.0336
        vakifbank,2,0.0499
        ...
        """
        import csv
        
        updates = {}
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                bank_key = row.get('bank_key', row.get('bank', '')).strip().lower()
                installment = int(row.get('installment', row.get('taksit', 1)))
                rate = float(row.get('rate', row.get('oran', 0)))
                
                if bank_key not in updates:
                    updates[bank_key] = {}
                updates[bank_key][installment] = rate
        
        if not updates:
            return {"success": False, "error": "No valid rows found in CSV"}
        
        # Apply updates
        config = self.get_current_rates()
        updated_banks = []
        
        for bank_key, rates in updates.items():
            if bank_key in config.get("banks", {}):
                config["banks"][bank_key]["rates"].update(rates)
                updated_banks.append(bank_key)
        
        # Save updated config
        with open(self.rates_file, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
        
        # Log change
        self._add_to_history("csv_import", {
            "source_file": str(file_path),
            "updated_banks": updated_banks,
            "row_count": sum(len(r) for r in updates.values())
        }, user)
        
        # Clear cache
        self._clear_rates_cache()
        
        return {
            "success": True,
            "message": f"Imported {sum(len(r) for r in updates.values())} rates from CSV",
            "updated_banks": updated_banks
        }
    
    def import_from_url(self, url: str, user: str = "dashboard") -> Dict[str, Any]:
        """Import rates from a URL.
        
        Args:
            url: URL to fetch rates from (YAML or JSON format)
            user: User performing import
            
        Returns:
            Import result
        """
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            content_type = response.headers.get('content-type', '')
            content = response.text
            
            # Try to parse as YAML (which also handles JSON)
            try:
                new_config = yaml.safe_load(content)
            except yaml.YAMLError as e:
                return {"success": False, "error": f"Failed to parse response: {e}"}
            
            if not new_config or "banks" not in new_config:
                return {"success": False, "error": "Invalid format - missing 'banks' key"}
            
            # Validate rates
            validation_errors = self._validate_rates_config(new_config)
            if validation_errors:
                return {"success": False, "error": f"Validation errors: {validation_errors}"}
            
            # Backup current config
            old_config = self.get_current_rates()
            backup_path = self.config_dir / f"commission_rates.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}.yaml"
            with open(backup_path, 'w', encoding='utf-8') as f:
                yaml.dump(old_config, f, allow_unicode=True, default_flow_style=False)
            
            # Save new config
            with open(self.rates_file, 'w', encoding='utf-8') as f:
                yaml.dump(new_config, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
            
            # Log change
            self._add_to_history("url_import", {
                "source_url": url,
                "backup_file": str(backup_path),
                "bank_count": len(new_config.get("banks", {}))
            }, user)
            
            # Clear cache
            self._clear_rates_cache()
            
            return {
                "success": True,
                "message": f"Imported rates from URL",
                "bank_count": len(new_config.get("banks", {})),
                "backup_created": str(backup_path)
            }
            
        except requests.RequestException as e:
            return {"success": False, "error": f"Failed to fetch URL: {e}"}
    
    def _validate_rates_config(self, config: Dict[str, Any]) -> List[str]:
        """Validate a rates configuration.
        
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        banks = config.get("banks", {})
        if not banks:
            errors.append("No banks defined")
            return errors
        
        for bank_key, bank_data in banks.items():
            if not isinstance(bank_data, dict):
                errors.append(f"{bank_key}: Invalid bank data format")
                continue
            
            if "rates" not in bank_data:
                errors.append(f"{bank_key}: Missing 'rates' key")
                continue
            
            rates = bank_data.get("rates", {})
            for inst, rate in rates.items():
                # Validate installment is a positive integer
                if not isinstance(inst, int) or inst < 1:
                    errors.append(f"{bank_key}: Invalid installment '{inst}'")
                
                # Validate rate is a valid decimal
                if not isinstance(rate, (int, float)) or rate < 0 or rate > 1:
                    errors.append(f"{bank_key} taksit {inst}: Invalid rate {rate} (should be 0-1)")
        
        return errors
    
    def _clear_rates_cache(self):
        """Clear the commission rates cache."""
        from processing.commission_control import _COMMISSION_RATES_CACHE
        import processing.commission_control as cc
        cc._COMMISSION_RATES_CACHE = None
    
    def export_current_rates(self, format: str = "yaml") -> str:
        """Export current rates as string.
        
        Args:
            format: Export format ('yaml' or 'csv')
            
        Returns:
            Rates as string in requested format
        """
        config = self.get_current_rates()
        
        if format == "yaml":
            return yaml.dump(config, allow_unicode=True, default_flow_style=False, sort_keys=False)
        
        elif format == "csv":
            lines = ["bank_key,bank_name,installment,rate"]
            for bank_key, bank_data in config.get("banks", {}).items():
                bank_name = bank_data.get("aliases", [bank_key])[0] if bank_data.get("aliases") else bank_key
                for inst, rate in sorted(bank_data.get("rates", {}).items()):
                    lines.append(f"{bank_key},{bank_name},{inst},{rate}")
            return "\n".join(lines)
        
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def compare_with_source(self, source_url: str) -> Dict[str, Any]:
        """Compare current rates with a remote source.
        
        Args:
            source_url: URL to fetch comparison rates from
            
        Returns:
            Comparison result with differences
        """
        try:
            response = requests.get(source_url, timeout=30)
            response.raise_for_status()
            
            source_config = yaml.safe_load(response.text)
            current_config = self.get_current_rates()
            
            differences = []
            
            source_banks = source_config.get("banks", {})
            current_banks = current_config.get("banks", {})
            
            # Compare each bank
            for bank_key, source_data in source_banks.items():
                current_data = current_banks.get(bank_key, {})
                source_rates = source_data.get("rates", {})
                current_rates = current_data.get("rates", {})
                
                for inst, source_rate in source_rates.items():
                    current_rate = current_rates.get(inst)
                    if current_rate != source_rate:
                        differences.append({
                            "bank": bank_key,
                            "installment": inst,
                            "current_rate": current_rate,
                            "source_rate": source_rate,
                            "diff": round(source_rate - (current_rate or 0), 6)
                        })
            
            return {
                "success": True,
                "has_differences": len(differences) > 0,
                "difference_count": len(differences),
                "differences": differences,
                "source_url": source_url,
                "checked_at": datetime.now().isoformat()
            }
            
        except requests.RequestException as e:
            return {"success": False, "error": f"Failed to fetch source: {e}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_sources(self) -> Dict[str, Any]:
        """Get configured rate sources."""
        if not self.sources_file.exists():
            return {"sources": {}}
        
        with open(self.sources_file, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {"sources": {}}
    
    def add_source(self, source_id: str, name: str, url: Optional[str] = None, 
                   source_type: str = "url", description: str = "") -> bool:
        """Add a new rate source.
        
        Args:
            source_id: Unique identifier for the source
            name: Display name
            url: URL for remote sources
            source_type: Type of source ('url', 'file', 'manual')
            description: Description of the source
            
        Returns:
            True if successful
        """
        sources = self.get_sources()
        
        sources["sources"][source_id] = {
            "name": name,
            "type": source_type,
            "url": url,
            "description": description,
            "added": datetime.now().isoformat()
        }
        
        with open(self.sources_file, 'w', encoding='utf-8') as f:
            yaml.dump(sources, f, allow_unicode=True, default_flow_style=False)
        
        return True


def get_rate_manager() -> RateManager:
    """Get singleton RateManager instance."""
    return RateManager()
