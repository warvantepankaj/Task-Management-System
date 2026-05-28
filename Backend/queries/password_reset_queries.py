INSERT_RESET_TOKEN = """
    INSERT INTO password_reset_tokens (user_id, token_hash, expires_at)
    VALUES (%s, %s, %s)
    RETURNING id, user_id, token_hash, expires_at, created_at;
"""

GET_RESET_TOKEN_BY_HASH = """
    SELECT id, user_id, token_hash, expires_at, used_at, created_at
    FROM password_reset_tokens
    WHERE token_hash = %s;
"""

MARK_RESET_TOKEN_USED = """
    UPDATE password_reset_tokens
    SET used_at = NOW()
    WHERE token_hash = %s AND used_at IS NULL
    RETURNING id;
"""

# When a reset succeeds, kill any other outstanding links for the same user.
INVALIDATE_USER_RESET_TOKENS = """
    UPDATE password_reset_tokens
    SET used_at = NOW()
    WHERE user_id = %s AND used_at IS NULL;
"""

UPDATE_USER_PASSWORD = """
    UPDATE users
    SET password_hash = %s
    WHERE id = %s
    RETURNING id;
"""
