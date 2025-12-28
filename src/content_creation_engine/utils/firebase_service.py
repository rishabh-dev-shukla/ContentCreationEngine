"""
Firebase Service Module.
Handles all Firebase Firestore and Authentication operations.
"""

import os
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from functools import wraps

import firebase_admin
from firebase_admin import credentials, firestore, auth
from google.cloud.firestore_v1.base_query import FieldFilter

logger = logging.getLogger(__name__)

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
DATABASE_DIR = PROJECT_ROOT / "database"


class FirebaseService:
    """Singleton Firebase service for Firestore and Authentication operations."""
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize Firebase connection."""
        if FirebaseService._initialized:
            return
            
        try:
            # Try to read from environment variable first (for production deployment)
            firebase_creds_json = os.getenv('FIREBASE_SERVICE_ACCOUNT')
            
            if firebase_creds_json:
                # Use credentials from environment variable
                logger.info("Using Firebase credentials from environment variable")
                cred_dict = json.loads(firebase_creds_json)
                cred = credentials.Certificate(cred_dict)
            else:
                # Fall back to file (for local development)
                cred_files = list(DATABASE_DIR.glob("*.json"))
                if not cred_files:
                    raise FileNotFoundError(
                        f"No Firebase credentials file found in {DATABASE_DIR}"
                    )
                
                cred_path = cred_files[0]  # Use first JSON file found
                logger.info(f"Using Firebase credentials from: {cred_path}")
                cred = credentials.Certificate(str(cred_path))
            
            # Initialize Firebase Admin SDK
            firebase_admin.initialize_app(cred)
            
            # Get Firestore client
            self.db = firestore.client()
            
            FirebaseService._initialized = True
            logger.info("Firebase initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Firebase: {e}")
            raise
    
    # =========================================================================
    # Authentication Methods
    # =========================================================================
    
    def verify_id_token(self, id_token: str) -> Optional[Dict[str, Any]]:
        """
        Verify a Firebase ID token and return the decoded token.
        
        Args:
            id_token: The Firebase ID token from the client
            
        Returns:
            Decoded token dict with user info, or None if invalid
        """
        try:
            decoded_token = auth.verify_id_token(id_token)
            return decoded_token
        except Exception as e:
            logger.error(f"Token verification failed: {e}")
            return None
    
    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """
        Get a user document from Firestore by email.
        
        Args:
            email: User's email address
            
        Returns:
            User document data or None if not found
        """
        try:
            users_ref = self.db.collection('users')
            query = users_ref.where(filter=FieldFilter('email', '==', email))
            docs = query.get()
            
            for doc in docs:
                user_data = doc.to_dict()
                user_data['_id'] = doc.id
                return user_data
            
            return None
        except Exception as e:
            logger.error(f"Error getting user by email: {e}")
            return None
    
    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a user document from Firestore by document ID.
        
        Args:
            user_id: User document ID
            
        Returns:
            User document data or None if not found
        """
        try:
            doc = self.db.collection('users').document(user_id).get()
            if doc.exists:
                user_data = doc.to_dict()
                user_data['_id'] = doc.id
                return user_data
            return None
        except Exception as e:
            logger.error(f"Error getting user by ID: {e}")
            return None
    
    def create_or_update_user(self, email: str, user_data: Dict[str, Any]) -> str:
        """
        Create or update a user document.
        
        Args:
            email: User's email (used as document ID)
            user_data: User data to store
            
        Returns:
            User document ID
        """
        try:
            # Use email as document ID (replace special chars)
            doc_id = email.replace('@', '_at_').replace('.', '_dot_')
            
            user_data['email'] = email
            user_data['updated_at'] = datetime.utcnow().isoformat()
            
            if 'created_at' not in user_data:
                user_data['created_at'] = datetime.utcnow().isoformat()
            
            self.db.collection('users').document(doc_id).set(user_data, merge=True)
            logger.info(f"User created/updated: {email}")
            return doc_id
        except Exception as e:
            logger.error(f"Error creating/updating user: {e}")
            raise
    
    # =========================================================================
    # Customer Methods
    # =========================================================================
    
    def get_customer(self, customer_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a customer document.
        
        Args:
            customer_id: Customer document ID
            
        Returns:
            Customer document data or None if not found
        """
        try:
            doc = self.db.collection('customers').document(customer_id).get()
            if doc.exists:
                data = doc.to_dict()
                data['_id'] = doc.id
                return data
            return None
        except Exception as e:
            logger.error(f"Error getting customer: {e}")
            return None
    
    def create_customer(self, customer_id: str, customer_data: Dict[str, Any]) -> str:
        """
        Create a new customer document.
        
        Args:
            customer_id: Customer document ID
            customer_data: Customer data to store
            
        Returns:
            Customer document ID
        """
        try:
            customer_data['created_at'] = datetime.utcnow().isoformat()
            customer_data['updated_at'] = datetime.utcnow().isoformat()
            
            self.db.collection('customers').document(customer_id).set(customer_data)
            logger.info(f"Customer created: {customer_id}")
            return customer_id
        except Exception as e:
            logger.error(f"Error creating customer: {e}")
            raise
    
    def list_customers_for_user(self, user_email: str) -> List[Dict[str, Any]]:
        """
        List all customers a user has access to.
        
        Args:
            user_email: User's email address
            
        Returns:
            List of customer documents
        """
        try:
            user = self.get_user_by_email(user_email)
            if not user:
                return []
            
            customer_ids = user.get('customers', [])
            customers = []
            
            for cid in customer_ids:
                customer = self.get_customer(cid)
                if customer:
                    customers.append(customer)
            
            return customers
        except Exception as e:
            logger.error(f"Error listing customers for user: {e}")
            return []
    
    # =========================================================================
    # Persona Methods
    # =========================================================================
    
    def get_persona(self, customer_id: str, persona_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a persona document.
        
        Args:
            customer_id: Customer document ID
            persona_id: Persona document ID
            
        Returns:
            Persona document data or None if not found
        """
        try:
            doc = (self.db.collection('customers')
                   .document(customer_id)
                   .collection('personas')
                   .document(persona_id)
                   .get())
            
            if doc.exists:
                data = doc.to_dict()
                data['_id'] = doc.id
                data['_customer_id'] = customer_id
                return data
            return None
        except Exception as e:
            logger.error(f"Error getting persona: {e}")
            return None
    
    def list_personas(self, customer_id: str) -> List[str]:
        """
        List all persona IDs for a customer.
        
        Args:
            customer_id: Customer document ID
            
        Returns:
            List of persona IDs
        """
        try:
            personas_ref = (self.db.collection('customers')
                          .document(customer_id)
                          .collection('personas'))
            
            docs = personas_ref.get()
            return [doc.id for doc in docs]
        except Exception as e:
            logger.error(f"Error listing personas: {e}")
            return []
    
    def save_persona(self, customer_id: str, persona: Dict[str, Any]) -> str:
        """
        Save a persona document.
        
        Args:
            customer_id: Customer document ID
            persona: Persona data (must contain 'persona_id')
            
        Returns:
            Persona document ID
        """
        try:
            persona_id = persona.get('persona_id')
            if not persona_id:
                raise ValueError("Persona must have a 'persona_id' field")
            
            persona['updated_at'] = datetime.utcnow().isoformat()
            if 'created_at' not in persona:
                persona['created_at'] = datetime.utcnow().isoformat()
            
            (self.db.collection('customers')
             .document(customer_id)
             .collection('personas')
             .document(persona_id)
             .set(persona, merge=True))
            
            logger.info(f"Persona saved: {customer_id}/{persona_id}")
            return persona_id
        except Exception as e:
            logger.error(f"Error saving persona: {e}")
            raise
    
    def delete_persona(self, customer_id: str, persona_id: str) -> bool:
        """
        Delete a persona document.
        
        Args:
            customer_id: Customer document ID
            persona_id: Persona document ID
            
        Returns:
            True if deleted successfully
        """
        try:
            (self.db.collection('customers')
             .document(customer_id)
             .collection('personas')
             .document(persona_id)
             .delete())
            
            logger.info(f"Persona deleted: {customer_id}/{persona_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting persona: {e}")
            return False
    
    # =========================================================================
    # Content Output Methods
    # =========================================================================
    
    def save_content_output(
        self, 
        customer_id: str, 
        persona_id: str, 
        content: Dict[str, Any],
        output_id: Optional[str] = None
    ) -> str:
        """
        Save a content output document.
        
        Args:
            customer_id: Customer document ID
            persona_id: Persona document ID
            content: Content data to store
            output_id: Optional custom output ID (auto-generated if not provided)
            
        Returns:
            Content output document ID
        """
        try:
            if not output_id:
                timestamp = datetime.utcnow().strftime("%Y-%m-%d_%H%M%S")
                output_id = f"{timestamp}_content"
            
            content['saved_at'] = datetime.utcnow().isoformat()
            
            (self.db.collection('customers')
             .document(customer_id)
             .collection('personas')
             .document(persona_id)
             .collection('outputs')
             .document(output_id)
             .set(content, merge=True))
            
            logger.info(f"Content output saved: {customer_id}/{persona_id}/{output_id}")
            return output_id
        except Exception as e:
            logger.error(f"Error saving content output: {e}")
            raise
    
    def get_content_output(
        self, 
        customer_id: str, 
        persona_id: str, 
        output_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get a specific content output document.
        
        Args:
            customer_id: Customer document ID
            persona_id: Persona document ID
            output_id: Output document ID
            
        Returns:
            Content output data or None if not found
        """
        try:
            doc = (self.db.collection('customers')
                   .document(customer_id)
                   .collection('personas')
                   .document(persona_id)
                   .collection('outputs')
                   .document(output_id)
                   .get())
            
            if doc.exists:
                data = doc.to_dict()
                data['_id'] = doc.id
                data['_filename'] = doc.id
                return data
            return None
        except Exception as e:
            logger.error(f"Error getting content output: {e}")
            return None
    
    def list_content_outputs(
        self, 
        customer_id: str, 
        persona_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        List content outputs for a customer, optionally filtered by persona.
        
        Args:
            customer_id: Customer document ID
            persona_id: Optional persona ID to filter by
            limit: Maximum number of results
            
        Returns:
            List of content output documents
        """
        try:
            outputs = []
            
            if persona_id:
                # Get outputs for specific persona
                persona_ids = [persona_id]
            else:
                # Get outputs for all personas
                persona_ids = self.list_personas(customer_id)
            
            for pid in persona_ids:
                outputs_ref = (self.db.collection('customers')
                              .document(customer_id)
                              .collection('personas')
                              .document(pid)
                              .collection('outputs')
                              .order_by('date', direction=firestore.Query.DESCENDING)
                              .limit(limit))
                
                docs = outputs_ref.get()
                for doc in docs:
                    data = doc.to_dict()
                    data['_id'] = doc.id
                    data['_filename'] = doc.id
                    data['_persona_id'] = pid
                    outputs.append(data)
            
            # Sort by date descending
            outputs.sort(key=lambda x: x.get('date', ''), reverse=True)
            return outputs[:limit]
        except Exception as e:
            logger.error(f"Error listing content outputs: {e}")
            return []
    
    def update_script_status(
        self,
        customer_id: str,
        persona_id: str,
        output_id: str,
        script_index: int,
        status: str,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Update the status of a specific script in an output document.
        
        Args:
            customer_id: Customer document ID
            persona_id: Persona document ID
            output_id: Output document ID
            script_index: Index of the script in the scripts array
            status: New status ('approved', 'rejected', etc.)
            additional_data: Optional additional fields to update
            
        Returns:
            True if updated successfully
        """
        try:
            output = self.get_content_output(customer_id, persona_id, output_id)
            if not output:
                return False
            
            scripts = output.get('scripts', [])
            if script_index >= len(scripts):
                return False
            
            scripts[script_index]['status'] = status
            scripts[script_index]['last_edited'] = datetime.utcnow().isoformat()
            
            if additional_data:
                scripts[script_index].update(additional_data)
            
            (self.db.collection('customers')
             .document(customer_id)
             .collection('personas')
             .document(persona_id)
             .collection('outputs')
             .document(output_id)
             .update({'scripts': scripts}))
            
            return True
        except Exception as e:
            logger.error(f"Error updating script status: {e}")
            return False
    
    def add_manual_script(
        self,
        customer_id: str,
        persona_id: str,
        script_data: Dict[str, Any]
    ) -> Optional[str]:
        """
        Add a manual script to a persona's manual content collection.
        
        Args:
            customer_id: Customer document ID
            persona_id: Persona document ID
            script_data: Script data including title, content, etc.
            
        Returns:
            Output document ID if created successfully, None otherwise
        """
        try:
            # Create a manual content output document if needed
            output_id = f"manual_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
            
            # Mark the script as manual
            script = {
                **script_data,
                'is_manual': True,
                'created_at': datetime.utcnow().isoformat(),
                'last_edited': datetime.utcnow().isoformat(),
                'status': script_data.get('status', 'pending')
            }
            
            # Check if a manual content document exists for today
            today_id = f"manual_{datetime.utcnow().strftime('%Y-%m-%d')}"
            existing_output = self.get_content_output(customer_id, persona_id, today_id)
            
            if existing_output:
                # Add to existing manual output
                scripts = existing_output.get('scripts', [])
                scripts.append(script)
                
                (self.db.collection('customers')
                 .document(customer_id)
                 .collection('personas')
                 .document(persona_id)
                 .collection('outputs')
                 .document(today_id)
                 .update({'scripts': scripts}))
                
                return today_id
            else:
                # Create new manual output document
                output_data = {
                    'persona_id': persona_id,
                    'date': datetime.utcnow().strftime('%Y-%m-%d'),
                    'niche': script_data.get('niche', 'Manual Content'),
                    'is_manual': True,
                    'content_ideas': [],
                    'scripts': [script],
                    'visuals': [],
                    'created_at': datetime.utcnow().isoformat()
                }
                
                (self.db.collection('customers')
                 .document(customer_id)
                 .collection('personas')
                 .document(persona_id)
                 .collection('outputs')
                 .document(today_id)
                 .set(output_data))
                
                return today_id
        except Exception as e:
            logger.error(f"Error adding manual script: {e}")
            return None
    
    # =========================================================================
    # Research Cache Methods
    # =========================================================================
    
    def save_research(
        self, 
        customer_id: str, 
        research_data: Dict[str, Any],
        research_id: Optional[str] = None
    ) -> str:
        """
        Save research data.
        
        Args:
            customer_id: Customer document ID
            research_data: Research data to store
            research_id: Optional custom ID (auto-generated if not provided)
            
        Returns:
            Research document ID
        """
        try:
            if not research_id:
                research_id = datetime.utcnow().strftime("%Y-%m-%d_research")
            
            research_data['saved_at'] = datetime.utcnow().isoformat()
            
            (self.db.collection('customers')
             .document(customer_id)
             .collection('research')
             .document(research_id)
             .set(research_data, merge=True))
            
            logger.info(f"Research saved: {customer_id}/{research_id}")
            return research_id
        except Exception as e:
            logger.error(f"Error saving research: {e}")
            raise
    
    def get_research(self, customer_id: str, research_id: str) -> Optional[Dict[str, Any]]:
        """
        Get research data by ID.
        
        Args:
            customer_id: Customer document ID
            research_id: Research document ID
            
        Returns:
            Research data or None if not found
        """
        try:
            doc = (self.db.collection('customers')
                   .document(customer_id)
                   .collection('research')
                   .document(research_id)
                   .get())
            
            if doc.exists:
                data = doc.to_dict()
                data['_id'] = doc.id
                return data
            return None
        except Exception as e:
            logger.error(f"Error getting research: {e}")
            return None
    
    def list_research(self, customer_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        List research data for a customer.
        
        Args:
            customer_id: Customer document ID
            limit: Maximum number of results
            
        Returns:
            List of research documents
        """
        try:
            docs = (self.db.collection('customers')
                   .document(customer_id)
                   .collection('research')
                   .order_by('saved_at', direction=firestore.Query.DESCENDING)
                   .limit(limit)
                   .get())
            
            return [{'_id': doc.id, **doc.to_dict()} for doc in docs]
        except Exception as e:
            logger.error(f"Error listing research: {e}")
            return []
    
    # =========================================================================
    # Insights Methods
    # =========================================================================
    
    def save_insights(
        self, 
        customer_id: str, 
        persona_id: str,
        insights_data: Dict[str, Any],
        insights_id: Optional[str] = None
    ) -> str:
        """
        Save insights data.
        
        Args:
            customer_id: Customer document ID
            persona_id: Persona document ID
            insights_data: Insights data to store
            insights_id: Optional custom ID (auto-generated if not provided)
            
        Returns:
            Insights document ID
        """
        try:
            if not insights_id:
                timestamp = datetime.utcnow().strftime("%Y-%m-%d_%H%M%S")
                insights_id = f"{timestamp}_insights"
            
            insights_data['saved_at'] = datetime.utcnow().isoformat()
            
            (self.db.collection('customers')
             .document(customer_id)
             .collection('personas')
             .document(persona_id)
             .collection('insights')
             .document(insights_id)
             .set(insights_data, merge=True))
            
            logger.info(f"Insights saved: {customer_id}/{persona_id}/{insights_id}")
            return insights_id
        except Exception as e:
            logger.error(f"Error saving insights: {e}")
            raise
    
    def get_insights(
        self, 
        customer_id: str, 
        persona_id: str,
        insights_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get a specific insights document.
        
        Args:
            customer_id: Customer document ID
            persona_id: Persona document ID
            insights_id: Insights document ID
            
        Returns:
            Insights document data or None if not found
        """
        try:
            doc = (self.db.collection('customers')
                   .document(customer_id)
                   .collection('personas')
                   .document(persona_id)
                   .collection('insights')
                   .document(insights_id)
                   .get())
            
            if doc.exists:
                data = doc.to_dict()
                data['_id'] = doc.id
                return data
            return None
        except Exception as e:
            logger.error(f"Error getting insights: {e}")
            return None
    
    def list_insights(
        self, 
        customer_id: str, 
        persona_id: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        List insights for a customer, optionally filtered by persona.
        
        Args:
            customer_id: Customer document ID
            persona_id: Optional persona ID to filter by
            limit: Maximum number of results
            
        Returns:
            List of insights documents
        """
        try:
            insights = []
            
            if persona_id:
                persona_ids = [persona_id]
            else:
                persona_ids = self.list_personas(customer_id)
            
            for pid in persona_ids:
                docs = (self.db.collection('customers')
                       .document(customer_id)
                       .collection('personas')
                       .document(pid)
                       .collection('insights')
                       .order_by('saved_at', direction=firestore.Query.DESCENDING)
                       .limit(limit)
                       .get())
                
                for doc in docs:
                    data = doc.to_dict()
                    data['_id'] = doc.id
                    data['_persona_id'] = pid
                    insights.append(data)
            
            insights.sort(key=lambda x: x.get('saved_at', ''), reverse=True)
            return insights[:limit]
        except Exception as e:
            logger.error(f"Error listing insights: {e}")
            return []
    
    # =========================================================================
    # Video Jobs Methods
    # =========================================================================
    
    def save_video_job(
        self, 
        customer_id: str, 
        job_id: str,
        job_data: Dict[str, Any]
    ) -> str:
        """
        Save a video generation job record.
        
        Args:
            customer_id: Customer document ID
            job_id: Video job ID
            job_data: Job data to store
            
        Returns:
            Job document ID
        """
        try:
            job_data['saved_at'] = datetime.utcnow().isoformat()
            
            (self.db.collection('customers')
             .document(customer_id)
             .collection('video_jobs')
             .document(job_id)
             .set(job_data, merge=True))
            
            logger.info(f"Video job saved: {customer_id}/{job_id}")
            return job_id
        except Exception as e:
            logger.error(f"Error saving video job: {e}")
            raise
    
    def list_video_jobs(
        self, 
        customer_id: str, 
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        List video generation jobs for a customer.
        
        Args:
            customer_id: Customer document ID
            limit: Maximum number of results
            
        Returns:
            List of video job documents
        """
        try:
            docs = (self.db.collection('customers')
                   .document(customer_id)
                   .collection('video_jobs')
                   .order_by('saved_at', direction=firestore.Query.DESCENDING)
                   .limit(limit)
                   .get())
            
            jobs = []
            for doc in docs:
                data = doc.to_dict()
                data['job_id'] = doc.id
                jobs.append(data)
            
            return jobs
        except Exception as e:
            logger.error(f"Error listing video jobs: {e}")
            return []


# Global instance
_firebase_service = None


def get_firebase_service() -> FirebaseService:
    """Get the global Firebase service instance."""
    global _firebase_service
    if _firebase_service is None:
        _firebase_service = FirebaseService()
    return _firebase_service
