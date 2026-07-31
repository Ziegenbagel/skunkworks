"""Forum capabilities exposed by the game UI."""


class CommunityGateway:
    def __init__(self, client):
        self.client = client

    def categories(self):
        return self.client.request(
            "GET",
            "/api/forum/categories",
        )

    def create_category(self, payload):
        return self.client.request(
            "POST",
            "/api/forum/categories",
            json=payload,
        )

    def category(self, category_id):
        return self.client.request(
            "GET",
            f"/api/forum/categories/{category_id}",
        )

    def update_category(self, category_id, payload):
        return self.client.request(
            "PATCH",
            f"/api/forum/categories/{category_id}",
            json=payload,
        )

    def delete_category(self, category_id):
        return self.client.request(
            "DELETE",
            f"/api/forum/categories/{category_id}",
        )

    def posts(self):
        return self.client.request(
            "GET",
            "/api/forum/posts",
        )

    def create_post(self, payload):
        return self.client.request(
            "POST",
            "/api/forum/posts",
            json=payload,
        )

    def post(self, post_id):
        return self.client.request(
            "GET",
            f"/api/forum/posts/{post_id}",
        )

    def update_post(self, post_id, payload):
        return self.client.request(
            "PATCH",
            f"/api/forum/posts/{post_id}",
            json=payload,
        )

    def delete_post(self, post_id):
        return self.client.request(
            "DELETE",
            f"/api/forum/posts/{post_id}",
        )

    def messages(self, post_id):
        return self.client.request(
            "GET",
            f"/api/forum/posts/{post_id}/messages",
        )

    def create_message(self, post_id, payload):
        return self.client.request(
            "POST",
            f"/api/forum/posts/{post_id}/messages",
            json=payload,
        )

    def update_message(self, message_id, payload):
        return self.client.request(
            "PATCH",
            f"/api/forum/messages/{message_id}",
            json=payload,
        )

    def delete_message(self, message_id):
        return self.client.request(
            "DELETE",
            f"/api/forum/messages/{message_id}",
        )
