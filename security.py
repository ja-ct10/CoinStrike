"""
security.py — Game Security & Anti-Cheat System

Provides lightweight security features for CoinStrike:
- Secure value encoding/decoding for game stats
- Anti-cheat detection for abnormal gameplay values
- File integrity verification
- Save file validation

All security measures are designed to be lightweight and offline-compatible.
"""

import hashlib
import os
import json
import random
import time


# ---------------------------------------------------------------------------
# SECURE VALUE ENCODING
# ---------------------------------------------------------------------------
class SecureValue:
    """
    Stores a numeric value using reversible mathematical transformation.
    Prevents direct memory editing and makes values harder to tamper with.

    Uses XOR encryption with a dynamic key based on a seed value.
    """

    def __init__(self, initial_value=0, seed=None):
        """
        Initialize a secure value.

        Args:
            initial_value: The starting value to store
            seed: Optional seed for key generation (uses random if None)
        """
        self._seed = seed if seed is not None else random.randint(1000, 9999)
        self._encoded = 0
        self._checksum = 0
        self.set(initial_value)

    def _generate_key(self):
        """Generate encryption key from seed (cached)."""
        # Cache key since seed never changes after init
        if not hasattr(self, "_cached_key"):
            self._cached_key = (self._seed * 7919) % 65536
        return self._cached_key

    def _calculate_checksum(self, value):
        """Calculate checksum for integrity verification."""
        return (value * 31 + self._seed) % 1000000

    def set(self, value):
        """Store a value securely."""
        if not isinstance(value, (int, float)):
            value = 0

        # Convert to int for encoding
        int_value = int(value)

        # Encode using XOR with generated key
        key = self._generate_key()
        self._encoded = int_value ^ key

        # Store checksum for integrity verification
        self._checksum = self._calculate_checksum(int_value)

    def get(self):
        """Retrieve the stored value."""
        # Decode using XOR with generated key
        key = self._generate_key()
        value = self._encoded ^ key

        # Verify integrity
        expected_checksum = self._calculate_checksum(value)
        if self._checksum != expected_checksum:
            # Value was tampered with - return 0 as safe fallback
            return 0

        return value

    def add(self, amount):
        """Add to the stored value (optimized - avoids double encode/decode)."""
        # Decode once
        key = self._generate_key()
        current = self._encoded ^ key
        # Verify integrity
        if self._checksum != self._calculate_checksum(current):
            current = 0
        # Add and re-encode
        new_value = current + amount
        self._encoded = new_value ^ key
        self._checksum = self._calculate_checksum(new_value)

    def subtract(self, amount):
        """Subtract from the stored value (optimized - avoids double encode/decode)."""
        # Decode once
        key = self._generate_key()
        current = self._encoded ^ key
        # Verify integrity
        if self._checksum != self._calculate_checksum(current):
            current = 0
        # Subtract and re-encode
        new_value = max(0, current - amount)
        self._encoded = new_value ^ key
        self._checksum = self._calculate_checksum(new_value)


# ---------------------------------------------------------------------------
# ANTI-CHEAT SYSTEM
# ---------------------------------------------------------------------------
class AntiCheat:
    """
    Monitors gameplay values and detects abnormal patterns that indicate cheating.

    Checks for:
    - Impossible coin counts
    - Excessive combo streaks
    - Invalid ammo values
    - Suspicious stat changes
    """

    # Thresholds for cheat detection (class-level constants)
    MAX_REASONABLE_COINS = 10000  # Maximum coins achievable in normal gameplay
    MAX_REASONABLE_COMBO = 100  # Maximum combo streak
    MAX_REASONABLE_HP = 150  # Maximum HP (with buffs)

    # Violation tracking
    VIOLATION_THRESHOLD = 3  # Number of violations before action

    # Pre-computed max ammo dict (shared across all instances)
    _MAX_AMMO = {"gun": 35, "grenade": 15, "spear": 10}

    def __init__(self):
        self.violations = 0
        self.last_check_time = time.time()
        self.previous_values = {}
        self.suspicious_changes = 0

    def check_player_stats(self, player, health, weapon_manager):
        """
        Check player statistics for abnormal values.

        Returns:
            tuple: (is_valid, violation_message)
        """
        # Pre-fetch attributes once to avoid repeated getattr calls
        coins = getattr(player, "coins_collected", 0)
        hp = getattr(health, "hp", 0)
        combo = getattr(player, "combo_count", 0)
        game_over = getattr(health, "game_over", False)

        # Early exit checks (most common case - no violations)
        has_violation = False

        # Check coins (inline to avoid list allocation)
        if coins > self.MAX_REASONABLE_COINS or coins < 0:
            has_violation = True

        # Check HP
        if hp > self.MAX_REASONABLE_HP or (hp < 0 and not game_over):
            has_violation = True

        # Check combo
        if combo > self.MAX_REASONABLE_COMBO or combo < 0:
            has_violation = True

        # Check ammo values (only if weapon_manager exists)
        if weapon_manager and weapon_manager.ammo:
            for weapon, ammo in weapon_manager.ammo.items():
                max_ammo = self._MAX_AMMO.get(weapon, 50)
                if ammo > max_ammo * 2 or ammo < 0:
                    has_violation = True
                    break

        # Check for suspicious rapid changes
        current_time = time.time()
        if current_time - self.last_check_time < 0.1:
            self.suspicious_changes += 1
            if self.suspicious_changes > 50:
                has_violation = True
        else:
            self.suspicious_changes = max(0, self.suspicious_changes - 1)

        self.last_check_time = current_time

        # Only build detailed violation message if violations detected
        if has_violation:
            violations = []
            if coins > self.MAX_REASONABLE_COINS:
                violations.append(f"Excessive coins: {coins}")
            if coins < 0:
                violations.append("Negative coins detected")
            if hp > self.MAX_REASONABLE_HP:
                violations.append(f"Excessive HP: {hp}")
            if hp < 0 and not game_over:
                violations.append("Negative HP detected")
            if combo > self.MAX_REASONABLE_COMBO:
                violations.append(f"Impossible combo: {combo}")
            if combo < 0:
                violations.append("Negative combo detected")

            if weapon_manager and weapon_manager.ammo:
                for weapon, ammo in weapon_manager.ammo.items():
                    max_ammo = self._MAX_AMMO.get(weapon, 50)
                    if ammo > max_ammo * 2:
                        violations.append(f"Excessive {weapon} ammo: {ammo}")
                    if ammo < 0:
                        violations.append(f"Negative {weapon} ammo")

            if self.suspicious_changes > 50:
                violations.append("Suspicious memory access pattern")

            self.violations += len(violations)
            return False, "; ".join(violations)

        return True, None

    def should_trigger_penalty(self):
        """Check if violations exceed threshold."""
        return self.violations >= self.VIOLATION_THRESHOLD

    def reset_violations(self):
        """Reset violation counter."""
        self.violations = 0
        self.suspicious_changes = 0

    def apply_penalty(self, player, health, weapon_manager):
        """
        Apply penalty for detected cheating.
        Resets suspicious values to safe defaults.
        """
        # Reset coins to reasonable value
        if hasattr(player, "coins_collected"):
            if player.coins_collected > self.MAX_REASONABLE_COINS:
                player.coins_collected = 100

        # Reset combo
        if hasattr(player, "combo_count"):
            if player.combo_count > self.MAX_REASONABLE_COMBO:
                player.combo_count = 0

        # Reset HP to safe value
        if health.hp > self.MAX_REASONABLE_HP:
            health.hp = 100

        # Reset ammo to reasonable values (use cached dict)
        if weapon_manager and weapon_manager.ammo:
            for weapon in weapon_manager.ammo:
                max_ammo = self._MAX_AMMO.get(weapon, 10)
                if weapon_manager.ammo[weapon] > max_ammo:
                    weapon_manager.ammo[weapon] = max_ammo // 2

        self.reset_violations()


# ---------------------------------------------------------------------------
# FILE INTEGRITY CHECKER
# ---------------------------------------------------------------------------
class FileIntegrityChecker:
    """
    Verifies integrity of critical game files using SHA-256 hashing.
    Detects tampering with assets and configuration files.
    """

    def __init__(self, manifest_file="file_manifest.json"):
        self.manifest_file = manifest_file
        self.manifest = {}
        self.critical_files = []

    def generate_manifest(self, file_paths):
        """
        Generate hash manifest for critical files.

        Args:
            file_paths: List of file paths to include in manifest
        """
        self.manifest = {}
        self.critical_files = file_paths

        for filepath in file_paths:
            if os.path.exists(filepath):
                file_hash = self._hash_file(filepath)
                self.manifest[filepath] = file_hash

        # Save manifest
        self._save_manifest()

    def _hash_file(self, filepath):
        """Calculate SHA-256 hash of a file."""
        sha256 = hashlib.sha256()

        try:
            with open(filepath, "rb") as f:
                # Read in chunks to handle large files
                for chunk in iter(lambda: f.read(4096), b""):
                    sha256.update(chunk)
            return sha256.hexdigest()
        except Exception:
            return None

    def _save_manifest(self):
        """Save manifest to file."""
        try:
            with open(self.manifest_file, "w") as f:
                json.dump(self.manifest, f, indent=2)
        except Exception:
            pass

    def _load_manifest(self):
        """Load manifest from file."""
        try:
            if os.path.exists(self.manifest_file):
                with open(self.manifest_file, "r") as f:
                    self.manifest = json.load(f)
                return True
        except Exception:
            pass
        return False

    def verify_integrity(self):
        """
        Verify integrity of all files in manifest.

        Returns:
            tuple: (is_valid, list of tampered files)
        """
        if not self._load_manifest():
            # No manifest - skip verification (first run)
            return True, []

        tampered_files = []

        for filepath, expected_hash in self.manifest.items():
            if not os.path.exists(filepath):
                tampered_files.append(f"{filepath} (missing)")
                continue

            current_hash = self._hash_file(filepath)
            if current_hash != expected_hash:
                tampered_files.append(f"{filepath} (modified)")

        is_valid = len(tampered_files) == 0
        return is_valid, tampered_files


# ---------------------------------------------------------------------------
# SECURE SAVE SYSTEM
# ---------------------------------------------------------------------------
class SecureSaveSystem:
    """
    Handles secure saving and loading of game data.
    Includes encoding and checksum validation to prevent tampering.
    """

    def __init__(self, save_file="coinstrike_save.dat"):
        self.save_file = save_file
        self._key = 0x5A7E  # XOR key for encoding

    def _encode_data(self, data_str):
        """Encode save data using XOR (optimized)."""
        # Pre-allocate bytearray with known size for better performance
        data_bytes = data_str.encode("utf-8")
        encoded = bytearray(len(data_bytes))

        # Use direct indexing instead of enumerate + append
        for i in range(len(data_bytes)):
            encoded[i] = data_bytes[i] ^ (self._key >> (i % 8))

        return encoded

    def _decode_data(self, encoded_data):
        """Decode save data using XOR (optimized)."""
        # Pre-allocate bytearray with known size
        decoded = bytearray(len(encoded_data))

        # Use direct indexing instead of enumerate + append
        for i in range(len(encoded_data)):
            decoded[i] = encoded_data[i] ^ (self._key >> (i % 8))

        return decoded.decode("utf-8")

    def _calculate_checksum(self, data_str):
        """Calculate checksum for save data."""
        return hashlib.sha256(data_str.encode("utf-8")).hexdigest()

    def save_game(self, game_data):
        """
        Save game data securely.

        Args:
            game_data: Dictionary containing game state

        Returns:
            bool: True if save successful
        """
        try:
            # Convert to JSON
            json_str = json.dumps(game_data)

            # Calculate checksum
            checksum = self._calculate_checksum(json_str)

            # Create save package
            save_package = {"data": json_str, "checksum": checksum, "version": "1.0"}

            # Encode entire package
            package_str = json.dumps(save_package)
            encoded = self._encode_data(package_str)

            # Write to file
            with open(self.save_file, "wb") as f:
                f.write(encoded)

            return True
        except Exception:
            return False

    def load_game(self):
        """
        Load game data securely.

        Returns:
            tuple: (success, game_data or error_message)
        """
        try:
            if not os.path.exists(self.save_file):
                return False, "No save file found"

            # Read encoded data
            with open(self.save_file, "rb") as f:
                encoded = f.read()

            # Decode package
            package_str = self._decode_data(encoded)
            save_package = json.loads(package_str)

            # Verify checksum
            data_str = save_package["data"]
            expected_checksum = save_package["checksum"]
            actual_checksum = self._calculate_checksum(data_str)

            if actual_checksum != expected_checksum:
                return False, "Save file corrupted or tampered"

            # Parse game data
            game_data = json.loads(data_str)

            return True, game_data
        except Exception as e:
            return False, f"Failed to load save: {str(e)}"

    def delete_save(self):
        """Delete save file."""
        try:
            if os.path.exists(self.save_file):
                os.remove(self.save_file)
            return True
        except Exception:
            return False


# ---------------------------------------------------------------------------
# SECURITY MANAGER (Main Interface)
# ---------------------------------------------------------------------------
class SecurityManager:
    """
    Main security manager that coordinates all security features.
    Integrates into the game loop for continuous monitoring.
    """

    def __init__(self):
        self.anti_cheat = AntiCheat()
        self.file_checker = FileIntegrityChecker()
        self.save_system = SecureSaveSystem()
        self.enabled = True
        self.check_interval = 60  # Check every 60 frames (~1 second at 60 FPS)
        self.frame_counter = 0

    def initialize(self, critical_files=None):
        """
        Initialize security systems.

        Args:
            critical_files: List of critical file paths to monitor
        """
        # Generate file manifest if critical files provided
        if critical_files:
            self.file_checker.generate_manifest(critical_files)

    def verify_game_files(self):
        """
        Verify integrity of game files.

        Returns:
            tuple: (is_valid, error_message)
        """
        is_valid, tampered = self.file_checker.verify_integrity()

        if not is_valid:
            error_msg = "Game files have been modified:\n" + "\n".join(tampered)
            return False, error_msg

        return True, None

    def update(self, player, health, weapon_manager):
        """
        Update security checks (call every frame).

        Args:
            player: Player object
            health: Health object
            weapon_manager: WeaponManager object

        Returns:
            bool: True if all checks pass, False if cheating detected
        """
        if not self.enabled:
            return True

        self.frame_counter += 1

        # Perform checks at intervals to reduce performance impact
        if self.frame_counter >= self.check_interval:
            self.frame_counter = 0

            # Run anti-cheat checks
            is_valid, violation_msg = self.anti_cheat.check_player_stats(
                player, health, weapon_manager
            )

            if not is_valid:
                # Cheating detected
                if self.anti_cheat.should_trigger_penalty():
                    # Apply penalty
                    self.anti_cheat.apply_penalty(player, health, weapon_manager)
                    return False

        return True

    def save_game_state(self, player, health, weapon_manager, mission, elapsed_time):
        """
        Save current game state securely.

        Returns:
            bool: True if save successful
        """
        # Pre-fetch attributes once to avoid repeated getattr calls
        game_data = {
            "player": {
                "coins": getattr(player, "coins_collected", 0),
                "kills": getattr(player, "kills", 0),
                "distance": int(getattr(player, "world_x", 0)),
            },
            "health": {
                "hp": health.hp,
            },
            "weapons": {
                "owned": list(weapon_manager.owned),
                "ammo": weapon_manager.ammo.copy(),
            },
            "mission": {
                # Use list comprehension instead of generator for better performance
                "completed": [m.get("completed", False) for m in mission.missions],
            },
            "time": elapsed_time,
            "timestamp": time.time(),
        }

        return self.save_system.save_game(game_data)

    def load_game_state(self):
        """
        Load saved game state.

        Returns:
            tuple: (success, game_data or error_message)
        """
        return self.save_system.load_game()
