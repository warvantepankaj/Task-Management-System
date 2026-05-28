from dao.user_dao import (
    create_user,
    get_all_users,
    get_user_by_email,
    get_user_by_id,
    get_all_users_paginated,
)


class UserService:
    def fetch_all_users(self, conn):
        return get_all_users(conn)

    def create_user_endpoint(self, conn, username, email, password_hash, role):
        return create_user(conn, username, email, password_hash, role)

    def get_user_by_email_endpoint(self, conn, email):
        return get_user_by_email(conn, email)

    def get_user_by_id_endpoint(self, conn, id):
        return get_user_by_id(conn, id)

    @staticmethod
    def fetch_all_users_paginated(
        conn,
        page: int,
        page_size: int,
        *,
        role: str | None = None,
        is_active: bool | None = None,
        search: str | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ):
        users, total = get_all_users_paginated(
            conn,
            page,
            page_size,
            role=role,
            is_active=is_active,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        total_pages = (total + page_size - 1) // page_size if page_size else 0
        return {
            "page": page,
            "page_size": page_size,
            "total": int(total),
            "total_pages": int(total_pages),
            "data": users,
        }
