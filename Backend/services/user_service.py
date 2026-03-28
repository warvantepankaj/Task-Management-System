from dao.user_dao import create_user, get_all_users, get_user_by_email, get_user_by_id, get_all_users_paginated

class UserService:
    def fetch_all_users(self, conn):
        return get_all_users(conn)

    def create_user_endpoint(self,conn, username, email, password_hash, role):
        return create_user(conn, username, email, password_hash, role)

    def get_user_by_email_endpoint(self,conn, email):
        return get_user_by_email(conn, email)
    
    def get_user_by_id_endpoint(self,conn, id):
        return get_user_by_id(conn, id)

    # Optional: Fetch users with pagination
    @staticmethod
    def fetch_all_users_paginated(conn, page: int, page_size: int):
        users, total = get_all_users_paginated(conn, page, page_size)
        return users, total
