INSERT_REFRESH_TOKEN = """
    INSERT INTO refresh_tokens (user_id, token_hash, expires_at, user_agent, ip)
    VALUES (%s, %s, %s, %s, %s)
    RETURNING id, user_id, token_hash, expires_at, created_at;
"""

GET_REFRESH_TOKEN_BY_HASH = """
    SELECT id, user_id, token_hash, expires_at, revoked_at, created_at
    FROM refresh_tokens
    WHERE token_hash = %s;
"""

REVOKE_REFRESH_TOKEN = """
    UPDATE refresh_tokens
    SET revoked_at = NOW()
    WHERE token_hash = %s AND revoked_at IS NULL
    RETURNING id;
"""

REVOKE_ALL_FOR_USER = """
    UPDATE refresh_tokens
    SET revoked_at = NOW()
    WHERE user_id = %s AND revoked_at IS NULL;
"""
