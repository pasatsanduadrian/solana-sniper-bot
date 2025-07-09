# config.py - Configurare îmbunătățită
import os
import json
from solders.keypair import Keypair
from dataclasses import dataclass

@dataclass
class Settings:
    """Application settings with wallet support."""
    
    helius_key: str = os.getenv("HELIUS_KEY", "demo")
    moralis_key: str | None = os.getenv("MORALIS_KEY")
    sol_secret: str | None = os.getenv("SOL_SECRET")
    
    @property
    def keypair(self) -> Keypair | None:
        """Create Keypair from secret."""
        if not self.sol_secret:
            return None
        try:
            secret_list = json.loads(self.sol_secret)
            return Keypair.from_bytes(bytes(secret_list))
        except:
            return None
    
    @property
    def public_key(self) -> str | None:
        """Get public key as string."""
        kp = self.keypair
        return str(kp.pubkey()) if kp else None

settings = Settings()
