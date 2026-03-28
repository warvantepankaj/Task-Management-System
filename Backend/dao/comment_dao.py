from queries.comment_queries import add_comment, get_comments_by_task


def insert_comment(conn, task_id, user_id, content):
    return add_comment(conn, task_id, user_id, content)

def fetch_comments_by_task(conn, task_id):
    return get_comments_by_task(conn, task_id)