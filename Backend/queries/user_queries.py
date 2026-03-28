# Insert a new user and return key fields
INSERT_USER_QUERY = """
    INSERT INTO users (username, email, password_hash, role)
    VALUES (%s, %s, %s, %s)
    RETURNING id, username, email, role, is_active, created_at;
"""

# Fetch a single active user by email
FETCH_USER_BY_EMAIL_QUERY = """
    SELECT id, username, email, role, password_hash FROM users WHERE email = %s AND is_active = TRUE;
"""

# Fetch a single active user by ID
FETCH_USER_BY_ID_QUERY = """
    SELECT id, username, email, role, is_active, created_at
    FROM users
    WHERE id = %s AND is_active = TRUE;
"""

# Fetch all active users, ordered by creation date (most recent first)
SELECT_ALL_USERS_QUERY = """
    SELECT id, username, email, role, is_active, created_at
    FROM users
    WHERE is_active = TRUE
    ORDER BY created_at DESC;
"""

# Fetch all active users with pagination
SELECT_ALL_USERS_PAGINATED_QUERY = """
    SELECT id, username, email, role, is_active, created_at
    FROM users
    ORDER BY created_at DESC
    LIMIT %s OFFSET %s;
"""

COUNT_USERS_QUERY = "SELECT COUNT(*) AS total FROM users"