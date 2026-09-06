
import requests
import json
import sys
from datetime import datetime

BASE_URL = "http://127.0.0.1:9000"

passed = []
failed = []
warnings = []
skipped = []


def result(method, endpoint, response, success_codes=(200, 201, 202, 204)):
    """Classify API response correctly."""

    status = response.status_code

    if status in success_codes:
        print(f"[PASS] {method:<6} {endpoint:<45} HTTP {status}")
        passed.append((method, endpoint, status))
    elif 400 <= status < 500:
        print(f"[WARN] {method:<6} {endpoint:<45} HTTP {status}")
        try:
            print(f"       Response: {response.json()}")
        except Exception:
            print(f"       Response: {response.text[:300]}")
        warnings.append((method, endpoint, status))
    elif status >= 500:
        print(f"[FAIL] {method:<6} {endpoint:<45} HTTP {status}")
        try:
            print(f"       Response: {response.json()}")
        except Exception:
            print(f"       Response: {response.text[:300]}")
        failed.append((method, endpoint, status))
    else:
        print(f"[INFO] {method:<6} {endpoint:<45} HTTP {status}")


def request(method, path, **kwargs):
    """Safe HTTP request wrapper."""

    try:
        response = requests.request(
            method,
            BASE_URL + path,
            timeout=60,
            **kwargs
        )
        result(method.upper(), path, response)
        return response

    except requests.exceptions.ConnectionError:
        print("\n[ERROR] Backend is not running.")
        print("Start it with:")
        print(
            ".\\venv\\Scripts\\python.exe "
            "-m uvicorn app.main:app --reload --port 9000"
        )
        sys.exit(1)

    except requests.exceptions.Timeout:
        print(f"[FAIL] {method.upper():<6} {path:<45} TIMEOUT")
        failed.append((method.upper(), path, "TIMEOUT"))
        return None

    except Exception as e:
        print(f"[FAIL] {method.upper():<6} {path:<45} ERROR")
        print(f"       {e}")
        failed.append((method.upper(), path, "ERROR"))
        return None


def get_json(response):
    if response is None:
        return {}

    try:
        return response.json()
    except Exception:
        return {}


print("=" * 75)
print("          SOVEREIGN AI BACKEND - API ENDPOINT TEST")
print("=" * 75)
print(f"Backend: {BASE_URL}")
print(f"Time: {datetime.now()}")
print()


# ============================================================================
# 1. BASIC / HEALTH
# ============================================================================

print("=" * 75)
print("1. BASIC / HEALTH ENDPOINTS")
print("=" * 75)

request("GET", "/")
request("GET", "/health")


# ============================================================================
# 2. AI HEALTH
# ============================================================================

print("\n" + "=" * 75)
print("2. AI HEALTH")
print("=" * 75)

request("GET", "/ai/health")


# ============================================================================
# 3. USERS
# ============================================================================

print("\n" + "=" * 75)
print("3. USER ENDPOINTS")
print("=" * 75)

users_response = request("GET", "/users/")

user_id = None

if users_response and users_response.status_code < 300:
    users_data = get_json(users_response)

    if isinstance(users_data, list) and users_data:
        user_id = users_data[0].get("id") or users_data[0].get("user_id")

    elif isinstance(users_data, dict):
        items = users_data.get("items", [])
        if items:
            user_id = items[0].get("id") or items[0].get("user_id")

if user_id is None:
    user_id = 1

print(f"Using user_id = {user_id}")

request("GET", f"/users/{user_id}")

# Test user creation
unique_email = f"endpoint_test_{datetime.now().timestamp()}@example.com"

new_user = {
    "username": f"endpoint_test_{int(datetime.now().timestamp())}",
    "name": "Endpoint Test User",
    "email": unique_email
}

create_user_response = request(
    "POST",
    "/users/",
    json=new_user
)

# Correct PATCH endpoint:
# PATCH /users/{user_id}/status?active=true
request(
    "PATCH",
    f"/users/{user_id}/status",
    params={"active": True}
)


# ============================================================================
# 4. PROJECTS
# ============================================================================

print("\n" + "=" * 75)
print("4. PROJECT ENDPOINTS")
print("=" * 75)

projects_response = request("GET", "/projects/")

project_id = None

if projects_response and projects_response.status_code < 300:
    projects_data = get_json(projects_response)

    if isinstance(projects_data, list) and projects_data:
        project_id = (
            projects_data[0].get("id")
            or projects_data[0].get("project_id")
        )

    elif isinstance(projects_data, dict):
        items = projects_data.get("items", [])
        if items:
            project_id = (
                items[0].get("id")
                or items[0].get("project_id")
            )

# Create a project if necessary
if project_id is None:
    project_payload = {
        "name": "API Endpoint Test Project",
        "description": "Temporary project created during API testing"
    }

    create_project = request(
        "POST",
        "/projects/",
        json=project_payload
    )

    data = get_json(create_project)

    project_id = (
        data.get("id")
        or data.get("project_id")
        if isinstance(data, dict)
        else None
    )

print(f"Using project_id = {project_id}")

if project_id is not None:

    request("GET", f"/projects/{project_id}")

    # Only perform PUT with a generic payload if project exists.
    request(
        "PUT",
        f"/projects/{project_id}",
        json={
            "name": "API Endpoint Test Project Updated",
            "description": "Updated during endpoint verification"
        }
    )

    request(
        "GET",
        f"/projects/{project_id}/summary"
    )


# ============================================================================
# 5. DOCUMENTS
# ============================================================================

print("\n" + "=" * 75)
print("5. DOCUMENT ENDPOINTS")
print("=" * 75)

documents_response = request("GET", "/documents/")

document_id = None

if documents_response and documents_response.status_code < 300:
    documents_data = get_json(documents_response)

    if isinstance(documents_data, list) and documents_data:
        document_id = (
            documents_data[0].get("id")
            or documents_data[0].get("document_id")
        )

    elif isinstance(documents_data, dict):
        items = documents_data.get("items", [])
        if items:
            document_id = (
                items[0].get("id")
                or items[0].get("document_id")
            )

if document_id is not None:

    print(f"Using document_id = {document_id}")

    request(
        "GET",
        f"/documents/{document_id}"
    )

    # CORRECT METHOD:
    # PATCH /documents/{document_id}/status?status=...
    request(
        "PATCH",
        f"/documents/{document_id}/status",
        params={"status": "processed"}
    )

else:
    print("[SKIP] No document available for document-specific tests.")
    skipped.append("document-specific endpoints")


# ============================================================================
# 6. DOCUMENT PROJECT ENDPOINT
# ============================================================================

print("\n" + "=" * 75)
print("6. DOCUMENT PROJECT ENDPOINT")
print("=" * 75)

if project_id is not None:
    request(
        "GET",
        f"/documents/project/{project_id}"
    )
else:
    print("[SKIP] No project_id available.")
    skipped.append("/documents/project/{project_id}")


# ============================================================================
# 7. DOCUMENT INTELLIGENCE
# ============================================================================

print("\n" + "=" * 75)
print("7. DOCUMENT INTELLIGENCE")
print("=" * 75)

if document_id is not None:

    # Correct route is:
    # POST /document-intelligence/process
    request(
        "POST",
        "/document-intelligence/process",
        json={
            "document_id": document_id
        }
    )

    # Correct route is:
    # POST /document-intelligence/search
    request(
        "POST",
        "/document-intelligence/search",
        json={
            "query": "research methodology",
            "limit": 5
        }
    )

    # Correct route is:
    # POST /document-intelligence/rag-context
    request(
        "POST",
        "/document-intelligence/rag-context",
        json={
            "query": "research methodology",
            "limit": 5
        }
    )

else:
    print("[SKIP] Document Intelligence tests - no document ID.")
    skipped.append("Document Intelligence")


# ============================================================================
# 8. TASKS
# ============================================================================

print("\n" + "=" * 75)
print("8. TASK ENDPOINTS")
print("=" * 75)

tasks_response = request("GET", "/tasks/")

task_id = None

if tasks_response and tasks_response.status_code < 300:

    tasks_data = get_json(tasks_response)

    if isinstance(tasks_data, list) and tasks_data:
        task_id = (
            tasks_data[0].get("id")
            or tasks_data[0].get("task_id")
        )

    elif isinstance(tasks_data, dict):
        items = tasks_data.get("items", [])
        if items:
            task_id = (
                items[0].get("id")
                or items[0].get("task_id")
            )

print(f"Using task_id = {task_id}")

if project_id is not None:
    request(
        "GET",
        f"/tasks/project/{project_id}"
    )

if task_id is not None:

    request(
        "GET",
        f"/tasks/{task_id}"
    )

    request(
        "POST",
        f"/tasks/{task_id}/start"
    )

else:
    print("[SKIP] Task-specific endpoints - no task ID.")
    skipped.append("task-specific endpoints")


# ============================================================================
# 9. AI ASK
# ============================================================================

print("\n" + "=" * 75)
print("9. AI / RAG")
print("=" * 75)

# The actual /ai/ask schema is discovered from OpenAPI.
# This common payload is attempted first.

ai_response = request(
    "POST",
    "/ai/ask",
   json={
    "query": "What is artificial intelligence?"
}
)


# ============================================================================
# 10. AI TASK EXECUTION
# ============================================================================

print("\n" + "=" * 75)
print("10. AI TASK EXECUTION")
print("=" * 75)

if task_id is not None:

    # Correct route:
    # POST /ai/tasks/{task_id}/run
    request(
        "POST",
        f"/ai/tasks/{task_id}/run",
        json={}
    )

else:
    print("[SKIP] AI task execution - no task ID.")
    skipped.append("AI task execution")


# ============================================================================
# 11. REPORTS
# ============================================================================

print("\n" + "=" * 75)
print("11. REPORT ENDPOINTS")
print("=" * 75)

reports_response = request("GET", "/reports/")

report_id = None

if reports_response and reports_response.status_code < 300:

    reports_data = get_json(reports_response)

    if isinstance(reports_data, list) and reports_data:
        report_id = (
            reports_data[0].get("id")
            or reports_data[0].get("report_id")
        )

    elif isinstance(reports_data, dict):
        items = reports_data.get("items", [])
        if items:
            report_id = (
                items[0].get("id")
                or items[0].get("report_id")
            )

if project_id is not None:
    request(
        "GET",
        f"/reports/project/{project_id}"
    )

if report_id is not None:
    request(
        "GET",
        f"/reports/{report_id}"
    )


# ============================================================================
# FINAL SUMMARY
# ============================================================================

print("\n" + "=" * 75)
print("FINAL TEST SUMMARY")
print("=" * 75)

total = len(passed) + len(failed) + len(warnings)

print(f"TOTAL REQUESTS : {total}")
print(f"PASSED (2xx)   : {len(passed)}")
print(f"WARNINGS (4xx) : {len(warnings)}")
print(f"FAILED (5xx)   : {len(failed)}")
print(f"SKIPPED        : {len(skipped)}")

print("\n" + "-" * 75)

if passed:
    print("\nWORKING ENDPOINTS:")
    for method, endpoint, status in passed:
        print(f"  [PASS] {method:<6} {endpoint:<45} {status}")

if warnings:
    print("\n4xx / REQUEST ISSUES:")
    for method, endpoint, status in warnings:
        print(f"  [WARN] {method:<6} {endpoint:<45} {status}")

if failed:
    print("\nSERVER ERRORS:")
    for method, endpoint, status in failed:
        print(f"  [FAIL] {method:<6} {endpoint:<45} {status}")

if skipped:
    print("\nSKIPPED:")
    for item in skipped:
        print(f"  [SKIP] {item}")

print("\n" + "=" * 75)

if failed:
    print("RESULT: BACKEND HAS SERVER-SIDE ERRORS")
elif warnings:
    print("RESULT: BACKEND RESPONDS, BUT SOME REQUESTS NEED SCHEMA/PAYLOAD REVIEW")
else:
    print("RESULT: ALL TESTED REQUESTS RETURNED SUCCESS STATUS CODES")

print("=" * 75)

