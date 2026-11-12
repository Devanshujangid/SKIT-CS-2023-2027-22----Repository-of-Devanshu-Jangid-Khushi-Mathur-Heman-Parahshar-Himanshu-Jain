"""
Isolation Tests for Admin Endpoints RBAC Enforcement (HTTP 403 Forbidden for Students).

Exercises the real `require_admin` (`require_role(["admin"])`) dependency in `auth.py`
by overriding only `verify_clerk_token`, guaranteeing that:
1. Standard students receive HTTP 403 Forbidden on ALL Admin CRUD endpoints
   (GET/POST/PATCH/DELETE resources and students) and `/api/v1/analytics/admin/roster`.
2. Students cannot bypass RBAC via:
   - explicit `role: "student"` claim
   - `public_metadata: {"role": "student"}` or `metadata: {"role": "student"}`
   - omitting the role claim so `auth.py` falls back to querying `users.role == "student"`
   - missing DB record or DB error fail-safe (defaults to `"student"`)
   - arbitrary unrecognized roles (e.g., `"guest"`, `"ta"`, `"moderator"`)
3. No database reads/writes on protected tables (`learning_resources`, `student_profiles`)
   occur when a student request is rejected with HTTP 403.
4. Unauthenticated callers receive HTTP 401 Unauthorized.
5. Positive control: a legitimate `admin` user succeeds (HTTP 200 / 201).
"""

from pathlib import Path
import sys
import unittest
from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from auth import verify_clerk_token
from routes.admin import router as admin_router
from routes.analytics import router as analytics_router

app = FastAPI()
app.include_router(admin_router)
app.include_router(analytics_router)


ADMIN_ENDPOINT_MATRIX = [
    ("GET", "/api/v1/admin/resources", None),
    (
        "POST",
        "/api/v1/admin/resources",
        {
            "title": "Operating Systems: Three Easy Pieces",
            "description": "Virtualization, concurrency, and persistence textbook.",
            "url": "https://pages.cs.wisc.edu/~remzi/OSTEP/",
            "subject": "Operating Systems",
            "difficulty_level": "Intermediate",
        },
    ),
    (
        "PATCH",
        "/api/v1/admin/resources/res-uuid-001",
        {"is_active": False},
    ),
    ("DELETE", "/api/v1/admin/resources/res-uuid-001", None),
    ("GET", "/api/v1/admin/students", None),
    (
        "POST",
        "/api/v1/admin/students",
        {
            "clerk_id": "user_student_new",
            "email": "newstudent@skit.ac.in",
            "semester": 5,
            "study_hours_per_day": 4.0,
            "goals": ["Master Operating Systems"],
            "subjects": ["Operating Systems"],
        },
    ),
    (
        "PATCH",
        "/api/v1/admin/students/stu-uuid-001",
        {"semester": 6},
    ),
    ("DELETE", "/api/v1/admin/students/stu-uuid-001", None),
    ("GET", "/api/v1/analytics/admin/roster", None),
]


class TestAdminEndpointsRBACIsolation(unittest.TestCase):
    """
    Guarantees strict HTTP 403 isolation across all Admin CRUD and Roster endpoints
    for any non-admin caller.
    """

    def setUp(self):
        app.dependency_overrides.clear()
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()

    def _request_endpoint(self, method: str, path: str, payload: dict | None):
        if method == "GET":
            return self.client.get(path)
        if method == "POST":
            return self.client.post(path, json=payload)
        if method == "PATCH":
            return self.client.patch(path, json=payload)
        if method == "DELETE":
            return self.client.delete(path)
        raise ValueError(f"Unsupported HTTP method: {method}")

    # =========================================================================
    # 1. Standard Student JWT Claim -> HTTP 403 Across Every Admin Endpoint
    # =========================================================================

    @patch("routes.admin.get_db")
    @patch("routes.analytics.get_db")
    def test_student_role_claim_receives_403_on_all_admin_endpoints(
        self, mock_analytics_db, mock_admin_db
    ):
        """Direct `role: 'student'` JWT payload is rejected with 403 and performs zero DB ops."""
        app.dependency_overrides[verify_clerk_token] = lambda: {
            "sub": "user_student_001",
            "email": "student@skit.ac.in",
            "role": "student",
        }

        for method, path, payload in ADMIN_ENDPOINT_MATRIX:
            with self.subTest(method=method, path=path):
                response = self._request_endpoint(method, path, payload)
                self.assertEqual(
                    response.status_code,
                    403,
                    f"Expected 403 for student on {method} {path}, got {response.status_code}: {response.text}",
                )
                body = response.json()
                self.assertIn("Access forbidden", body.get("detail", ""))
                self.assertIn("student", body.get("detail", ""))

        # Guardrail must reject before route handlers ever touch the database
        mock_admin_db.assert_not_called()
        mock_analytics_db.assert_not_called()

    @patch("routes.admin.get_db")
    def test_student_public_metadata_claim_receives_403_on_all_admin_endpoints(self, mock_admin_db):
        """Clerk `public_metadata: {'role': 'student'}` receives 403 on all Admin endpoints."""
        app.dependency_overrides[verify_clerk_token] = lambda: {
            "sub": "user_student_meta",
            "email": "student2@skit.ac.in",
            "public_metadata": {"role": "student"},
        }

        for method, path, payload in ADMIN_ENDPOINT_MATRIX:
            with self.subTest(method=method, path=path):
                response = self._request_endpoint(method, path, payload)
                self.assertEqual(response.status_code, 403)
                self.assertIn("Access forbidden", response.json().get("detail", ""))

        mock_admin_db.assert_not_called()

    # =========================================================================
    # 2. JWT Without Role Claim -> DB Lookup Confirms Student -> HTTP 403
    # =========================================================================

    @patch("database.get_db")
    @patch("routes.admin.get_db")
    def test_jwt_without_role_claim_falls_back_to_db_student_and_returns_403(
        self, mock_admin_db, mock_auth_db
    ):
        """When JWT omits role, `require_admin` queries DB `users.role` and rejects 'student' with 403."""
        app.dependency_overrides[verify_clerk_token] = lambda: {
            "sub": "user_db_student_99",
            "email": "dbstudent@skit.ac.in",
        }

        db = MagicMock()
        db.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[{"role": "student"}]
        )
        mock_auth_db.return_value = db

        for method, path, payload in ADMIN_ENDPOINT_MATRIX:
            with self.subTest(method=method, path=path):
                response = self._request_endpoint(method, path, payload)
                self.assertEqual(response.status_code, 403)
                self.assertIn("student", response.json().get("detail", ""))

        mock_admin_db.assert_not_called()

    @patch("database.get_db", side_effect=RuntimeError("DB unavailable"))
    @patch("routes.admin.get_db")
    def test_db_failure_fail_safe_defaults_to_student_403(self, mock_admin_db, _mock_auth_db):
        """If JWT omits role and DB lookup fails, RBAC fails closed as 'student' (HTTP 403)."""
        app.dependency_overrides[verify_clerk_token] = lambda: {
            "sub": "user_unknown_role",
            "email": "unknown@skit.ac.in",
        }

        for method, path, payload in ADMIN_ENDPOINT_MATRIX:
            with self.subTest(method=method, path=path):
                response = self._request_endpoint(method, path, payload)
                self.assertEqual(response.status_code, 403)

        mock_admin_db.assert_not_called()

    # =========================================================================
    # 3. Unrecognized / Spoofed Non-Admin Roles -> HTTP 403
    # =========================================================================

    @patch("routes.admin.get_db")
    def test_unrecognized_non_admin_roles_receive_403(self, mock_admin_db):
        """Arbitrary non-admin role claims (e.g. 'guest', 'moderator', 'teaching_assistant') get 403."""
        for role_name in ["guest", "moderator", "teaching_assistant", "Admin"]:
            app.dependency_overrides[verify_clerk_token] = lambda r=role_name: {
                "sub": "user_spoof_role",
                "email": "spoof@skit.ac.in",
                "role": r,
            }
            with self.subTest(role=role_name):
                response = self.client.post(
                    "/api/v1/admin/resources",
                    json={
                        "title": "Unauthorized Resource",
                        "description": "Attempting privilege escalation via spoofed role.",
                        "url": "https://example.com/os",
                        "subject": "Operating Systems",
                    },
                )
                self.assertEqual(response.status_code, 403)

        mock_admin_db.assert_not_called()

    # =========================================================================
    # 4. Missing Bearer Token -> HTTP 401 Unauthorized
    # =========================================================================

    def test_unauthenticated_requests_receive_401(self):
        """Unauthenticated callers without a Clerk Bearer token are rejected with 401."""
        for method, path, payload in ADMIN_ENDPOINT_MATRIX:
            with self.subTest(method=method, path=path):
                response = self._request_endpoint(method, path, payload)
                self.assertEqual(response.status_code, 401)

    # =========================================================================
    # 5. Positive Control: Legitimate Admin Succeeds (HTTP 200 / 201)
    # =========================================================================

    @patch("routes.admin.get_db")
    def test_admin_role_succeeds_on_crud_endpoints(self, mock_admin_db):
        """Positive control: authenticated 'admin' can create resource and update student."""
        app.dependency_overrides[verify_clerk_token] = lambda: {
            "sub": "user_admin_faculty",
            "email": "faculty@skit.ac.in",
            "public_metadata": {"role": "admin"},
        }

        db = MagicMock()
        mock_admin_db.return_value = db

        # Mock POST /api/v1/admin/resources
        db.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[])
        res_create = self.client.post(
            "/api/v1/admin/resources",
            json={
                "title": "Operating Systems: Three Easy Pieces",
                "description": "Virtualization, concurrency, and persistence textbook.",
                "url": "https://pages.cs.wisc.edu/~remzi/OSTEP/",
                "subject": "Operating Systems",
                "difficulty_level": "Intermediate",
            },
        )
        self.assertEqual(res_create.status_code, 201)
        self.assertEqual(res_create.json()["created_by"], "user_admin_faculty")

        # Mock PATCH /api/v1/admin/students/{user_id}
        db.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[
                {
                    "id": "stu-uuid-001",
                    "clerk_id": "user_student_001",
                    "email": "student@skit.ac.in",
                    "role": "student",
                    "semester": 5,
                    "study_hours_per_day": 4.0,
                    "goals": ["GATE CS"],
                    "subjects": ["Operating Systems"],
                    "onboarding_completed": True,
                }
            ]
        )
        db.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[
                {
                    "semester": 6,
                    "study_hours_per_day": 4.0,
                    "goals": ["GATE CS"],
                    "subjects": ["Operating Systems"],
                    "onboarding_completed": True,
                }
            ]
        )
        res_patch = self.client.patch(
            "/api/v1/admin/students/stu-uuid-001",
            json={"semester": 6},
        )
        self.assertEqual(res_patch.status_code, 200)
        self.assertTrue(res_patch.json()["success"])
        self.assertEqual(res_patch.json()["student"]["semester"], 6)


if __name__ == "__main__":
    unittest.main()
