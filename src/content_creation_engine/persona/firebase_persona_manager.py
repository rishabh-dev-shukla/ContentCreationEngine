"""
Firebase-aware Persona Manager.
Extends PersonaManager to support Firebase Firestore as a backend while
maintaining backward compatibility with local file storage.
"""

import logging
from typing import Dict, List, Any, Optional
from pathlib import Path

from .persona_manager import PersonaManager
from config.settings import settings

logger = logging.getLogger(__name__)


class FirebasePersonaManager(PersonaManager):
    """
    PersonaManager that can use Firebase Firestore as the backend.
    Falls back to local file storage if Firebase is not configured.
    """
    
    def __init__(
        self, 
        customer_id: Optional[str] = None,
        use_firebase: bool = True,
        personas_dir: Optional[Path] = None
    ):
        """
        Initialize the FirebasePersonaManager.
        
        Args:
            customer_id: Customer ID for Firebase (required if use_firebase=True)
            use_firebase: Whether to use Firebase as backend
            personas_dir: Directory for local file storage (fallback)
        """
        super().__init__(personas_dir)
        
        self.customer_id = customer_id
        self.use_firebase = use_firebase
        self._firebase = None
        
        if use_firebase:
            try:
                from src.content_creation_engine.utils.firebase_service import get_firebase_service
                self._firebase = get_firebase_service()
                logger.info(f"Firebase initialized for customer: {customer_id}")
            except Exception as e:
                logger.warning(f"Firebase not available, falling back to local files: {e}")
                self.use_firebase = False
    
    def list_personas(self) -> List[str]:
        """
        List all available persona IDs.
        
        Returns:
            List of persona IDs
        """
        if self.use_firebase and self._firebase and self.customer_id:
            try:
                return self._firebase.list_personas(self.customer_id)
            except Exception as e:
                logger.error(f"Firebase list_personas failed, falling back to local: {e}")
        
        return super().list_personas()
    
    def load_persona(self, persona_id: str, use_cache: bool = True) -> Dict[str, Any]:
        """
        Load a persona by ID.
        
        Args:
            persona_id: The persona identifier
            use_cache: Whether to use cached version if available
            
        Returns:
            Persona dictionary
        """
        # Check cache first
        if use_cache and persona_id in self._personas_cache:
            return self._personas_cache[persona_id]
        
        if self.use_firebase and self._firebase and self.customer_id:
            try:
                persona = self._firebase.get_persona(self.customer_id, persona_id)
                if persona:
                    # Remove Firebase metadata fields
                    persona.pop('_id', None)
                    persona.pop('_customer_id', None)
                    
                    # Cache the persona
                    self._personas_cache[persona_id] = persona
                    logger.info(f"Loaded persona from Firebase: {persona_id}")
                    return persona
            except Exception as e:
                logger.error(f"Firebase load_persona failed, falling back to local: {e}")
        
        return super().load_persona(persona_id, use_cache)
    
    def save_persona(self, persona: Dict[str, Any]) -> str:
        """
        Save a persona.
        
        Args:
            persona: Persona dictionary (must contain 'persona_id')
            
        Returns:
            The persona_id of the saved persona
        """
        persona_id = persona.get('persona_id')
        if not persona_id:
            raise ValueError("Persona must have a 'persona_id' field")
        
        if self.use_firebase and self._firebase and self.customer_id:
            try:
                # Remove any cached metadata before saving
                persona_to_save = {k: v for k, v in persona.items() 
                                  if not k.startswith('_')}
                
                self._firebase.save_persona(self.customer_id, persona_to_save)
                
                # Update cache
                self._personas_cache[persona_id] = persona
                logger.info(f"Saved persona to Firebase: {persona_id}")
                return persona_id
            except Exception as e:
                logger.error(f"Firebase save_persona failed, falling back to local: {e}")
        
        return super().save_persona(persona)
    
    def delete_persona(self, persona_id: str) -> bool:
        """
        Delete a persona.
        
        Args:
            persona_id: The persona identifier
            
        Returns:
            True if deleted successfully
        """
        if self.use_firebase and self._firebase and self.customer_id:
            try:
                result = self._firebase.delete_persona(self.customer_id, persona_id)
                if result:
                    self._personas_cache.pop(persona_id, None)
                    logger.info(f"Deleted persona from Firebase: {persona_id}")
                    return True
            except Exception as e:
                logger.error(f"Firebase delete_persona failed, falling back to local: {e}")
        
        # Fall back to local file deletion
        file_path = self.personas_dir / f"{persona_id}.json"
        if file_path.exists():
            try:
                file_path.unlink()
                self._personas_cache.pop(persona_id, None)
                logger.info(f"Deleted persona from local: {persona_id}")
                return True
            except Exception as e:
                logger.error(f"Failed to delete local persona file: {e}")
        
        return False


def get_persona_manager(customer_id: Optional[str] = None, use_firebase: bool = True) -> PersonaManager:
    """
    Get a PersonaManager instance with Firebase support.
    
    Args:
        customer_id: Customer ID for Firebase
        use_firebase: Whether to use Firebase backend
        
    Returns:
        PersonaManager or FirebasePersonaManager instance
    """
    if use_firebase and customer_id:
        return FirebasePersonaManager(customer_id=customer_id, use_firebase=True)
    
    return PersonaManager()
