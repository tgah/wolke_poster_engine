"""Redis-based session manager for temporary product storage."""
import json
import redis
from typing import List, Optional, Dict, Any
from app.config import get_settings

settings = get_settings()


class SessionManager:
    """Manage session-based product storage in Redis."""
    
    def __init__(self):
        self.redis_client = redis.from_url(
            settings.CELERY_BROKER_URL,
            decode_responses=True
        )
        self.ttl = 7200  # 2 hours in seconds
    
    def _get_key(self, session_id: str) -> str:
        """Generate Redis key for session products."""
        return f"session:{session_id}:products"
    
    def store_products(self, session_id: str, products: List[Dict[str, Any]]) -> bool:
        """
        Store products in Redis with TTL.
        
        Args:
            session_id: Unique session identifier
            products: List of product dictionaries
        
        Returns:
            True if successful
        """
        key = self._get_key(session_id)
        value = json.dumps(products)
        
        # Store with 2-hour expiration
        self.redis_client.setex(key, self.ttl, value)
        
        return True
    
    def get_products(self, session_id: str) -> Optional[List[Dict[str, Any]]]:
        """
        Retrieve products from Redis.
        
        Args:
            session_id: Unique session identifier
        
        Returns:
            List of products or None if expired/not found
        """
        key = self._get_key(session_id)
        value = self.redis_client.get(key)
        
        if value is None:
            return None
        
        return json.loads(value)
    
    def get_product_by_artikel_nr(
        self, 
        session_id: str, 
        artikel_nr: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get specific product by artikel_nr from session.
        
        Args:
            session_id: Unique session identifier
            artikel_nr: Product identifier
        
        Returns:
            Product dict or None if not found
        """
        products = self.get_products(session_id)
        
        if products is None:
            return None
        
        for product in products:
            if product.get('artikel_nr') == artikel_nr:
                return product
        
        return None
    
    def delete_products(self, session_id: str) -> bool:
        """
        Delete products from Redis (on logout).
        
        Args:
            session_id: Unique session identifier
        
        Returns:
            True if deleted or didn't exist
        """
        key = self._get_key(session_id)
        self.redis_client.delete(key)
        return True
    
    def extend_ttl(self, session_id: str) -> bool:
        """
        Extend TTL by another 2 hours.
        
        Args:
            session_id: Unique session identifier
        
        Returns:
            True if extended, False if key doesn't exist
        """
        key = self._get_key(session_id)
        return self.redis_client.expire(key, self.ttl)
    
    def get_ttl(self, session_id: str) -> int:
        """
        Get remaining TTL in seconds.
        
        Args:
            session_id: Unique session identifier
        
        Returns:
            Seconds remaining, -2 if key doesn't exist, -1 if no expiry
        """
        key = self._get_key(session_id)
        return self.redis_client.ttl(key)