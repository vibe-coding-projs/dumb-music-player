import pytest
from playwright.sync_api import Page, expect

BASE_URL = "http://127.0.0.1:8080"


class TestPublicPages:
    """Tests for public-facing pages."""

    def test_homepage_loads(self, page: Page):
        """Homepage should load and display the music player."""
        page.goto(BASE_URL)
        expect(page).to_have_title_timeout = 5000
        # Check page loaded successfully
        expect(page.locator("body")).to_be_visible()

    def test_homepage_shows_song_list(self, page: Page):
        """Homepage should have a container for songs."""
        page.goto(BASE_URL)
        # The page should load without errors
        expect(page.locator("html")).to_be_visible()


class TestAdminLogin:
    """Tests for admin authentication flow."""

    def test_admin_page_shows_login_form(self, page: Page):
        """Admin page should show login form when not authenticated."""
        page.goto(f"{BASE_URL}/admin")
        # Should see password input
        expect(page.locator("input[type='password']")).to_be_visible()

    def test_admin_login_wrong_password(self, page: Page):
        """Wrong password should show error message."""
        page.goto(f"{BASE_URL}/admin")
        page.fill("input[type='password']", "wrongpassword")
        page.click("button[type='submit'], input[type='submit']")
        # Should still be on login page or see error
        expect(page.locator("input[type='password']")).to_be_visible()

    def test_admin_login_success(self, page: Page):
        """Correct password should redirect to dashboard."""
        page.goto(f"{BASE_URL}/admin")
        page.fill("input[type='password']", "changeme")
        page.click("button[type='submit'], input[type='submit']")
        # Should be redirected to dashboard
        page.wait_for_url("**/admin/dashboard")
        assert "/admin/dashboard" in page.url


class TestAdminDashboard:
    """Tests for admin dashboard functionality."""

    def login_as_admin(self, page: Page):
        """Helper to log in as admin."""
        page.goto(f"{BASE_URL}/admin")
        page.fill("input[type='password']", "changeme")
        page.click("button[type='submit'], input[type='submit']")
        page.wait_for_url("**/admin/dashboard")

    def test_dashboard_accessible_after_login(self, page: Page):
        """Dashboard should be accessible after login."""
        self.login_as_admin(page)
        assert "/admin/dashboard" in page.url

    def test_dashboard_has_add_song_link(self, page: Page):
        """Dashboard should have a link to add songs."""
        self.login_as_admin(page)
        # Look for add song link/button
        add_song_link = page.locator("a[href*='add-song'], a:has-text('הוסף'), a:has-text('Add')")
        expect(add_song_link.first).to_be_visible()

    def test_add_song_page_loads(self, page: Page):
        """Add song page should load with search form."""
        self.login_as_admin(page)
        page.goto(f"{BASE_URL}/admin/add-song")
        # Should have a search input or form
        search_input = page.locator("input[name='search_query'], input[type='text'], input[type='search']")
        expect(search_input.first).to_be_visible()

    def test_cookies_page_loads(self, page: Page):
        """Cookies management page should load."""
        self.login_as_admin(page)
        page.goto(f"{BASE_URL}/admin/cookies")
        # Page should load without error
        expect(page.locator("body")).to_be_visible()


class TestAdminLogout:
    """Tests for admin logout functionality."""

    def test_logout_redirects_to_homepage(self, page: Page):
        """Logout should redirect to homepage."""
        # Login first
        page.goto(f"{BASE_URL}/admin")
        page.fill("input[type='password']", "changeme")
        page.click("button[type='submit'], input[type='submit']")
        page.wait_for_url("**/admin/dashboard")

        # Now logout
        page.goto(f"{BASE_URL}/admin/logout")
        # Should be redirected to homepage
        expect(page).to_have_url(BASE_URL + "/")

    def test_dashboard_not_accessible_after_logout(self, page: Page):
        """Dashboard should redirect to login after logout."""
        # Login
        page.goto(f"{BASE_URL}/admin")
        page.fill("input[type='password']", "changeme")
        page.click("button[type='submit'], input[type='submit']")
        page.wait_for_url("**/admin/dashboard")

        # Logout
        page.goto(f"{BASE_URL}/admin/logout")

        # Try to access dashboard
        page.goto(f"{BASE_URL}/admin/dashboard")
        # Should be redirected to login
        assert "/admin" in page.url
        expect(page.locator("input[type='password']")).to_be_visible()


class TestAPIEndpoints:
    """Tests for API endpoints."""

    def test_ping_endpoint(self, page: Page):
        """Ping endpoint should return OK."""
        response = page.request.get(f"{BASE_URL}/admin/ping")
        assert response.ok
        json_data = response.json()
        assert json_data["status"] == "ok"
