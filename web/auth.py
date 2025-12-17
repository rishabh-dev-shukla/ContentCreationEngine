"""
Authentication module for Flask web application.
Handles Firebase Authentication integration with Google Sign-In.
"""

import logging
from functools import wraps
from typing import Optional, Dict, Any

from flask import session, redirect, url_for, request, g, jsonify

from src.content_creation_engine.utils.firebase_service import get_firebase_service

logger = logging.getLogger(__name__)


def get_current_user() -> Optional[Dict[str, Any]]:
    """
    Get the current authenticated user from session.
    
    Returns:
        User data dict or None if not authenticated
    """
    if 'user' in session:
        return session['user']
    return None


def get_current_customer_id() -> Optional[str]:
    """
    Get the current selected customer ID from session.
    
    Returns:
        Customer ID or None if not selected
    """
    return session.get('customer_id')


def set_current_customer(customer_id: str):
    """
    Set the current customer ID in session.
    
    Args:
        customer_id: Customer ID to set as current
    """
    session['customer_id'] = customer_id


def login_required(f):
    """
    Decorator to require authentication for a route.
    Redirects to login page if not authenticated.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            # For API routes, return JSON error
            if request.path.startswith('/api/'):
                return jsonify({'error': 'Authentication required'}), 401
            # For page routes, redirect to login
            return redirect(url_for('login_page'))
        
        # Add user and customer to g for easy access
        g.user = session['user']
        g.customer_id = session.get('customer_id')
        
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """
    Decorator to require admin role for a route.
    Must be used after @login_required.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if not user or user.get('role') != 'admin':
            if request.path.startswith('/api/'):
                return jsonify({'error': 'Admin access required'}), 403
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function


def verify_firebase_token(id_token: str) -> Optional[Dict[str, Any]]:
    """
    Verify Firebase ID token and get user data from Firestore.
    
    Args:
        id_token: Firebase ID token from client
        
    Returns:
        User data dict or None if invalid
    """
    try:
        firebase = get_firebase_service()
        
        # Verify the token with Firebase Auth
        decoded_token = firebase.verify_id_token(id_token)
        if not decoded_token:
            return None
        
        email = decoded_token.get('email')
        if not email:
            logger.error("Token does not contain email")
            return None
        
        # Get user from Firestore
        user_data = firebase.get_user_by_email(email)
        
        if not user_data:
            logger.warning(f"User not found in Firestore: {email}")
            return None
        
        # Add token info to user data
        user_data['firebase_uid'] = decoded_token.get('uid')
        user_data['email'] = email
        user_data['name'] = decoded_token.get('name', email.split('@')[0])
        user_data['picture'] = decoded_token.get('picture')
        
        return user_data
        
    except Exception as e:
        logger.error(f"Token verification error: {e}")
        return None


def login_user(user_data: Dict[str, Any], customer_id: Optional[str] = None):
    """
    Log in a user by storing their data in session.
    
    Args:
        user_data: User data to store in session
        customer_id: Optional customer ID to set as current
    """
    session['user'] = user_data
    session.permanent = True
    
    # Set default customer if not provided
    if customer_id:
        session['customer_id'] = customer_id
    elif 'customers' in user_data and user_data['customers']:
        session['customer_id'] = user_data['customers'][0]
    
    logger.info(f"User logged in: {user_data.get('email')}")


def logout_user():
    """Log out the current user by clearing session."""
    email = session.get('user', {}).get('email', 'unknown')
    session.clear()
    logger.info(f"User logged out: {email}")


def get_user_customers() -> list:
    """
    Get list of customers the current user has access to.
    
    Returns:
        List of customer data dicts
    """
    user = get_current_user()
    if not user:
        return []
    
    try:
        firebase = get_firebase_service()
        return firebase.list_customers_for_user(user.get('email'))
    except Exception as e:
        logger.error(f"Error getting user customers: {e}")
        return []
