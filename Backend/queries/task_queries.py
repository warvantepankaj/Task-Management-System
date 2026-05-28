CREATE_TASK_QUERY = """
INSERT INTO tasks (
    title,
    description,
    status,
    due_date,
    assigned_to,
    assigned_by
)
VALUES (%s, %s, %s, %s, %s, %s)
RETURNING id;
"""


GET_ALL_TASKS_ADMIN_QUERY = """
SELECT 
    t.id,
    t.title,
    t.description,
    t.status,
    t.due_date,
    t.assigned_to,
    u1.username AS assigned_to_username,
    t.assigned_by,
    u2.username AS assigned_by_username,
    t.created_at
FROM tasks t
LEFT JOIN users u1 ON t.assigned_to = u1.id
LEFT JOIN users u2 ON t.assigned_by = u2.id
ORDER BY t.created_at DESC;

"""

GET_TASKS_FOR_USER_QUERY = """
SELECT id, title, description, status, due_date, created_at
FROM tasks
WHERE assigned_to = %s
ORDER BY created_at DESC;
"""

UPDATE_TASK_QUERY = """
    UPDATE tasks
    SET {set_clause}
    WHERE id = %s
    RETURNING id, title, description, status, due_date,
    assigned_to, assigned_by, created_at;
"""


UPDATE_TASK_STATUS_QUERY = """
UPDATE tasks
SET status = %s
WHERE id = %s AND assigned_to = %s
RETURNING id;
"""

GET_TASKS_PAGINATED = """
SELECT id, title, description, status, due_date,
       assigned_to, assigned_by, created_at
FROM tasks
ORDER BY created_at DESC
LIMIT %s OFFSET %s;
"""

COUNT_TASKS = """
SELECT COUNT(*) AS total
FROM tasks
WHERE status = %s;
"""

GET_TASKS_BASE = """
SELECT id, title, description, status, due_date,
       assigned_to, assigned_by, created_at
FROM tasks
"""

DELETE_TASK_QUERY = """
DELETE FROM tasks
WHERE id = %s
RETURNING id;
"""

# Parameterised base templates for the filtered/sorted/paginated list endpoint.
# {where_clause} is built from a whitelist of conditions, each backed by %s
# placeholders. {order_clause} is filled from a whitelist (never user input).
GET_TASKS_FILTERED_BASE = """
    SELECT id, title, description, status, due_date,
           assigned_to, assigned_by, created_at
    FROM tasks
    {where_clause}
    ORDER BY {order_clause}
    LIMIT %s OFFSET %s
"""

COUNT_TASKS_FILTERED_BASE = """
    SELECT COUNT(*) AS total
    FROM tasks
    {where_clause}
"""