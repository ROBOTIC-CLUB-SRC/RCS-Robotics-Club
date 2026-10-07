"""Comprehensive local run test suite for RCS Robotics Club."""
import sys
from app import app

def run_all_tests():
    client = app.test_client()

    print("=" * 65)
    print("STARTING LOCAL RUN TESTS FOR RCS ROBOTICS CLUB")
    print("=" * 65)

    # 1. Health check
    res = client.get('/health')
    assert res.status_code == 200, f"Health check failed with {res.status_code}"
    print("[PASS] 1. Health check: /health ->", res.get_json())

    # 2. Public API all
    res = client.get('/api/public/all')
    assert res.status_code == 200, f"/api/public/all failed with {res.status_code}"
    data = res.get_json()
    assert 'goals' in data and 'club' in data, "Missing goals or club in /api/public/all"
    assert len(data['members']) > 0, "No members found"
    assert len(data['projects']) > 0, "No projects found"
    assert len(data['events']) > 0, "No events found"
    assert len(data['learning']) > 0, "No learning resources found"
    print(f"[PASS] 2. Public API: /api/public/all (Found {len(data['members'])} members, {len(data['projects'])} projects, {len(data['events'])} events, {len(data['learning'])} resources)")

    # 3. Homepage HTML & visual design requirements
    res = client.get('/')
    assert res.status_code == 200, f"GET / failed with {res.status_code}"
    html = res.data.decode('utf-8')
    assert 'RCS ROBOTICS' in html, "Missing 'RCS ROBOTICS' title"
    assert 'BUILD. LEARN. INNOVATE.' in html, "Missing 'BUILD. LEARN. INNOVATE.' tagline"
    assert 'robot-mascot.svg' in html, "Missing mascot reference in HTML"
    assert 'donutRingMembers' in html, "Missing stat donut rings in HTML"
    assert 'Tell us what you think...' in html, "Missing mini-form input in HTML"
    assert 'style.css' in html, "Missing style.css link in HTML"
    assert 'app.js' in html, "Missing app.js script in HTML"
    print("[PASS] 3. Homepage: GET / -> 200 OK (Contains 3-column hero, mascot, conic rings, mini-form)")

    # 4. Static assets
    assets = [
        '/static/style.css',
        '/static/app.js',
        '/static/admin.js',
        '/static/images/robot-mascot.svg',
        '/static/assets/rcs-logo.png'
    ]
    for asset in assets:
        res = client.get(asset)
        assert res.status_code == 200, f"Asset {asset} failed with {res.status_code}"
        print(f"[PASS] 4. Static asset loaded: {asset} ({len(res.data)} bytes)")

    # 5. Feedback redirect flow
    res = client.get('/feedback?message=Autonomous%20Rover')
    assert res.status_code == 302, f"Feedback redirect failed with {res.status_code}"
    loc = res.headers.get('Location')
    assert '/?message=Autonomous%20Rover#feedback' in loc, f"Redirect mismatch: {loc}"
    print(f"[PASS] 5. Feedback prefill redirect: /feedback?message=... -> {loc}")

    # 6. Feedback API submission
    res = client.post('/api/feedback', json={
        'name': 'Test Bot',
        'email': 'tester@sastra.edu',
        'type': 'project',
        'title': 'Swarm Robotics Build',
        'message': 'Testing local feedback pipeline with swarm robot idea.'
    })
    assert res.status_code == 200, f"POST /api/feedback failed with {res.status_code}"
    print("[PASS] 6. Feedback submission: POST /api/feedback ->", res.get_json())

    # 7. Authentication Flow (Admin)
    res = client.post('/api/auth/login', json={
        'email': 'faculty@rcs-sastra.org',
        'password': 'RCS@2026'
    })
    assert res.status_code == 200, f"Login failed: {res.status_code}"
    user = res.get_json()
    assert user['role'] == 'faculty', f"Unexpected role: {user['role']}"
    print(f"[PASS] 7. Auth Login: POST /api/auth/login -> Signed in as {user['name']} ({user['role']})")

    # 8. Check auth session
    res = client.get('/api/auth/me')
    assert res.status_code == 200
    me = res.get_json()
    assert me.get('authenticated') is True, "Session did not persist authentication"
    print(f"[PASS] 8. Auth Session: GET /api/auth/me -> Authenticated: {me['name']}")

    # 9. Admin view feedback and update status
    res = client.get('/api/admin/feedback')
    assert res.status_code == 200
    feedbacks = res.get_json()
    test_fb = next((f for f in feedbacks if f['title'] == 'Swarm Robotics Build'), None)
    assert test_fb is not None, "Submitted feedback not found in admin table"
    print(f"[PASS] 9. Admin Feedback List: Found test entry ID {test_fb['id']} with status '{test_fb['status']}'")

    res = client.put(f"/api/admin/feedback/{test_fb['id']}", json={'status': 'reviewed'})
    assert res.status_code == 200
    print(f"[PASS] 10. Admin Status Update: Feedback ID {test_fb['id']} marked as 'reviewed'")

    # 11. Admin view projects
    res = client.get('/api/admin/projects')
    assert res.status_code == 200
    projects = res.get_json()
    assert len(projects) >= 3
    print(f"[PASS] 11. Admin Projects List: Retrieved {len(projects)} projects")

    # 12. Logout
    res = client.post('/api/auth/logout')
    assert res.status_code == 200
    res = client.get('/api/auth/me')
    assert res.get_json().get('authenticated') is False, "Session was not cleared"
    print("[PASS] 12. Auth Logout: Logged out successfully")

    # 13. Admin portal HTML
    res = client.get('/app')
    assert res.status_code == 200
    admin_html = res.data.decode('utf-8')
    assert 'CONTROL ROOM' in admin_html, "Missing 'CONTROL ROOM' in admin HTML"
    assert 'admin.js' in admin_html, "Missing admin.js link in admin HTML"
    print("[PASS] 13. Admin Portal: GET /app -> 200 OK (Contains Control Room layout & script)")

    print("=" * 65)
    print("ALL 13 LOCAL TEST SUITES PASSED PERFECTLY!")
    print("=" * 65)

if __name__ == '__main__':
    run_all_tests()
