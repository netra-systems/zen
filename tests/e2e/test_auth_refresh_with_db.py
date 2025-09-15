"""
Test auth refresh with database session
Ensures refresh endpoint has access to database
"""
import asyncio
import json
import httpx
import pytest
from datetime import datetime
from shared.isolated_environment import IsolatedEnvironment

@pytest.mark.asyncio
async def test_auth_refresh_with_database():
    """Test that refresh endpoint has database session"""
    auth_url = 'http://localhost:8081'
    async with httpx.AsyncClient() as client:
        login_response = await client.post(f'{auth_url}/auth/dev/login', json={})
        if login_response.status_code != 200:
            pytest.skip('Dev login not available')
        login_data = login_response.json()
        access_token = login_data.get('access_token')
        refresh_token = login_data.get('refresh_token')
        assert access_token is not None
        assert refresh_token is not None
        await asyncio.sleep(1)
        refresh_response = await client.post(f'{auth_url}/auth/refresh', json={'refresh_token': refresh_token})
        assert refresh_response.status_code == 200, f'Refresh failed: {refresh_response.text}'
        refresh_data = refresh_response.json()
        new_access_token = refresh_data.get('access_token')
        new_refresh_token = refresh_data.get('refresh_token')
        assert new_access_token is not None
        assert new_refresh_token is not None
        assert new_access_token != access_token
        verify_response = await client.post(f'{auth_url}/auth/verify', headers={'Authorization': f'Bearer {new_access_token}'})
        assert verify_response.status_code == 200
        verify_data = verify_response.json()
        assert verify_data.get('valid') == True
        assert verify_data.get('user_id') is not None

@pytest.mark.asyncio
async def test_rapid_refresh_prevention():
    """Test that rapid refresh attempts are blocked"""
    auth_url = 'http://localhost:8081'
    async with httpx.AsyncClient() as client:
        login_response = await client.post(f'{auth_url}/auth/dev/login', json={})
        if login_response.status_code != 200:
            pytest.skip('Dev login not available')
        login_data = login_response.json()
        refresh_token = login_data.get('refresh_token')
        refresh_attempts = []
        for i in range(3):
            refresh_response = await client.post(f'{auth_url}/auth/refresh', json={'refresh_token': refresh_token})
            refresh_attempts.append(refresh_response)
            if refresh_response.status_code == 200:
                data = refresh_response.json()
                if 'refresh_token' in data:
                    refresh_token = data['refresh_token']
        successful = [r for r in refresh_attempts if r.status_code == 200]
        failed = [r for r in refresh_attempts if r.status_code != 200]
        assert len(successful) >= 1, 'At least one refresh should succeed'
        assert len(failed) >= 1, 'Rapid refreshes should be blocked'

@pytest.mark.asyncio
async def test_refresh_with_expired_token():
    """Test that expired refresh tokens are handled correctly"""
    auth_url = 'http://localhost:8081'
    async with httpx.AsyncClient() as client:
        expired_token = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0IiwiZXhwIjoxfQ.invalid'
        refresh_response = await client.post(f'{auth_url}/auth/refresh', json={'refresh_token': expired_token})
        assert refresh_response.status_code == 401
        assert 'Invalid refresh token' in refresh_response.text

@pytest.mark.asyncio
async def test_concurrent_refresh_handling():
    """Test that concurrent refresh requests are handled correctly"""
    auth_url = 'http://localhost:8081'
    async with httpx.AsyncClient() as client:
        login_response = await client.post(f'{auth_url}/auth/dev/login', json={})
        if login_response.status_code != 200:
            pytest.skip('Dev login not available')
        login_data = login_response.json()
        refresh_token = login_data.get('refresh_token')

        async def attempt_refresh():
            try:
                response = await client.post(f'{auth_url}/auth/refresh', json={'refresh_token': refresh_token})
                return response.status_code == 200
            except Exception:
                return False
        results = await asyncio.gather(*[attempt_refresh() for _ in range(5)])
        successful_attempts = sum(results)
        assert successful_attempts == 1, f'Expected 1 successful refresh, got {successful_attempts}'
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')