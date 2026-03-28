def add_comment(conn, task_id, user_id, comment):
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO task_comments (task_id, user_id, comment)
            VALUES (%s, %s, %s)
            RETURNING *
        """, (task_id, user_id, comment))
        result = cur.fetchone()
        conn.commit()
        return result


def get_comments_by_task(conn, task_id):
    with conn.cursor() as cur:
        cur.execute("""
            SELECT tc.*, u.username
            FROM task_comments tc
            JOIN users u ON tc.user_id = u.id
            WHERE tc.task_id = %s
            ORDER BY tc.created_at ASC
        """, (task_id,))
        return cur.fetchall()
