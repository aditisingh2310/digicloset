from locust import HttpUser, task, between
import os


class DigiclosetUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        self.shop = os.getenv("SHOP_DOMAIN", "loadtest.myshopify.com")
        self.token = os.getenv("ACCESS_TOKEN", "test-token")
        self.headers = {
            "x-shopify-shop-domain": self.shop,
            "authorization": f"Bearer {self.token}",
        }

    @task(3)
    def dashboard(self):
        self.client.get("/api/merchant/dashboard", headers=self.headers)

    @task(2)
    def update_widget_setting(self):
        self.client.post(
            "/api/merchant/settings",
            json={"widget_enabled": True},
            headers=self.headers,
        )

    @task(1)
    def ai_infer(self):
        self.client.post(
            "/ai/infer",
            json={"prompt": "Suggest an outfit", "max_tokens": 64},
            headers=self.headers,
        )
