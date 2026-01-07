"""Database connection and operations module."""

import os
from typing import Optional, Tuple
from datetime import datetime
from psycopg2 import pool
import psycopg2.extras


# Global connection pool
connection_pool: Optional[pool.SimpleConnectionPool] = None


def get_connection_pool() -> pool.SimpleConnectionPool:
    """
    Initialize and return connection pool singleton.

    Returns:
        SimpleConnectionPool: Database connection pool

    Raises:
        ValueError: If required environment variables are missing
        Exception: If connection pool creation fails
    """
    global connection_pool

    if connection_pool is not None:
        return connection_pool

    # Get database configuration from environment
    db_host = os.getenv("DATABASE_HOST")
    db_port = os.getenv("DATABASE_PORT")
    db_name = os.getenv("DATABASE_NAME")
    db_user = os.getenv("DATABASE_USER")
    db_password = os.getenv("DATABASE_PASSWORD")
    db_sslmode = os.getenv("DATABASE_SSLMODE", "prefer")

    # Validate required environment variables
    required_vars = {
        "DATABASE_HOST": db_host,
        "DATABASE_PORT": db_port,
        "DATABASE_NAME": db_name,
        "DATABASE_USER": db_user,
        "DATABASE_PASSWORD": db_password,
    }

    missing_vars = [var for var, value in required_vars.items() if not value]
    if missing_vars:
        raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

    try:
        # Create connection pool with minimum 1, maximum 3 connections
        connection_pool = pool.SimpleConnectionPool(
            minconn=1,
            maxconn=3,
            host=db_host,
            port=db_port,
            database=db_name,
            user=db_user,
            password=db_password,
            sslmode=db_sslmode,
        )

        print(f"Database connection pool created successfully (host: {db_host}, database: {db_name})")
        return connection_pool

    except Exception as e:
        print(f"Failed to create database connection pool: {e}")
        raise


def test_connection() -> bool:
    """
    Verify database connectivity on startup.

    Returns:
        bool: True if connection successful, False otherwise
    """
    try:
        pool_instance = get_connection_pool()
        conn = pool_instance.getconn()

        try:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            cursor.close()
            print("Database connection test successful")
            return True
        finally:
            pool_instance.putconn(conn)

    except Exception as e:
        print(f"Database connection test failed: {e}")
        return False


def save_message(
    session_uuid: str,
    message_type: str,
    contents: str,
    timestamp: Optional[datetime] = None
) -> bool:
    """
    Save chat message to database.

    Args:
        session_uuid: UUID of the current session
        message_type: Type of message ('system', 'user', or 'assistant')
        contents: Message content
        timestamp: Optional timestamp (defaults to current time)

    Returns:
        bool: True if save successful, False otherwise
    """
    if timestamp is None:
        timestamp = datetime.now()

    try:
        pool_instance = get_connection_pool()
        conn = pool_instance.getconn()

        try:
            cursor = conn.cursor()

            # Use parameterized query to prevent SQL injection
            query = """
                INSERT INTO chats (session_uuid, message_type, contents, timestamp)
                VALUES (%s, %s, %s, %s)
            """

            cursor.execute(query, (session_uuid, message_type, contents, timestamp))
            conn.commit()
            cursor.close()

            return True

        finally:
            pool_instance.putconn(conn)

    except Exception as e:
        print(f"Error saving message to database: {e}")
        return False


def get_session_history(session_uuid: str) -> Optional[list]:
    """
    Retrieve chat history for current session.

    Args:
        session_uuid: UUID of the current session

    Returns:
        List of message tuples (id, timestamp, session_uuid, message_type, contents, created_at)
        or None if error occurs
    """
    try:
        pool_instance = get_connection_pool()
        conn = pool_instance.getconn()

        try:
            cursor = conn.cursor()

            # Use parameterized query to prevent SQL injection
            query = """
                SELECT id, timestamp, session_uuid, message_type, contents, created_at
                FROM chats
                WHERE session_uuid = %s
                ORDER BY timestamp ASC, created_at ASC
            """

            cursor.execute(query, (session_uuid,))
            messages = cursor.fetchall()
            cursor.close()

            return messages

        finally:
            pool_instance.putconn(conn)

    except Exception as e:
        print(f"Error retrieving session history: {e}")
        return None


def get_document_by_name(name: str) -> Optional[Tuple[str, str]]:
    """
    Retrieve resume and jd from documents table where name matches.

    Args:
        name: Document name to search for

    Returns:
        Tuple of (resume, jd) if found, None otherwise
    """
    try:
        pool_instance = get_connection_pool()
        conn = pool_instance.getconn()

        try:
            cursor = conn.cursor()

            # Use parameterized query to prevent SQL injection
            query = """
                SELECT resume, jd
                FROM documents
                WHERE name = %s
            """

            cursor.execute(query, (name,))
            result = cursor.fetchone()
            cursor.close()

            if result:
                return result  # Returns (resume, jd) tuple
            else:
                return None

        finally:
            pool_instance.putconn(conn)

    except Exception as e:
        print(f"Error retrieving document by name '{name}': {e}")
        return None


def close_pool() -> None:
    """Clean shutdown of connection pool."""
    global connection_pool

    if connection_pool is not None:
        try:
            connection_pool.closeall()
            print("Database connection pool closed successfully")
        except Exception as e:
            print(f"Error closing connection pool: {e}")
        finally:
            connection_pool = None
