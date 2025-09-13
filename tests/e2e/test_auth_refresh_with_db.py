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

    

    # Use local auth service

    auth_url = "http://localhost:8081"

    

    async with httpx.AsyncClient() as client:

        # First, do a dev login to get tokens

        login_response = await client.post(

            f"{auth_url}/auth/dev/login",

            json={}

        )

        

        if login_response.status_code != 200:

            pytest.skip("Dev login not available")

            

        login_data = login_response.json()

        access_token = login_data.get("access_token")

        refresh_token = login_data.get("refresh_token")

        

        assert access_token is not None

        assert refresh_token is not None

        

        # Wait a moment

        await asyncio.sleep(1)

        

        # Now try to refresh the token

        refresh_response = await client.post(

            f"{auth_url}/auth/refresh",

            json={"refresh_token": refresh_token}

        )

        

        assert refresh_response.status_code == 200, f"Refresh failed: {refresh_response.text}"

        

        refresh_data = refresh_response.json()

        new_access_token = refresh_data.get("access_token")

        new_refresh_token = refresh_data.get("refresh_token")

        

        assert new_access_token is not None

        assert new_refresh_token is not None

        assert new_access_token != access_token  # Should be different

        

        # Verify the new token works

        verify_response = await client.post(

            f"{auth_url}/auth/verify",

            headers={"Authorization": f"Bearer {new_access_token}"}

        )

        

        assert verify_response.status_code == 200

        verify_data = verify_response.json()

        assert verify_data.get("valid") == True

        assert verify_data.get("user_id") is not None





@pytest.mark.asyncio

async def test_rapid_refresh_prevention():

    """Test that rapid refresh attempts are blocked"""

    

    auth_url = "http://localhost:8081"

    

    async with httpx.AsyncClient() as client:

        # Get initial tokens

        login_response = await client.post(

            f"{auth_url}/auth/dev/login",

            json={}

        )

        

        if login_response.status_code != 200:

            pytest.skip("Dev login not available")

            

        login_data = login_response.json()

        refresh_token = login_data.get("refresh_token")

        

        # Try to refresh multiple times rapidly

        refresh_attempts = []

        for i in range(3):

            refresh_response = await client.post(

                f"{auth_url}/auth/refresh",

                json={"refresh_token": refresh_token}

            )

            refresh_attempts.append(refresh_response)

            

            # Use new refresh token if successful

            if refresh_response.status_code == 200:

                data = refresh_response.json()

                if "refresh_token" in data:

                    refresh_token = data["refresh_token"]

        

        # Check that not all attempts succeeded (some should be blocked)

        successful = [r for r in refresh_attempts if r.status_code == 200]

        failed = [r for r in refresh_attempts if r.status_code != 200]

        

        # First should succeed, subsequent rapid attempts should fail

        assert len(successful) >= 1, "At least one refresh should succeed"

        assert len(failed) >= 1, "Rapid refreshes should be blocked"





@pytest.mark.asyncio

async def test_refresh_with_expired_token():

    """Test that expired refresh tokens are handled correctly"""

    

    auth_url = "http://localhost:8081"

    

    async with httpx.AsyncClient() as client:

        # Try with an obviously expired/invalid token

        expired_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0IiwiZXhwIjoxfQ.invalid"

        

        refresh_response = await client.post(

            f"{auth_url}/auth/refresh",

            json={"refresh_token": expired_token}

        )

        

        # Should return 401 for invalid token

        assert refresh_response.status_code == 401

        assert "Invalid refresh token" in refresh_response.text





@pytest.mark.asyncio 

async def test_concurrent_refresh_handling():

    """Test that concurrent refresh requests are handled correctly"""

    

    auth_url = "http://localhost:8081"

    

    async with httpx.AsyncClient() as client:

        # Get initial tokens

        login_response = await client.post(

            f"{auth_url}/auth/dev/login",

            json={}

        )

        

        if login_response.status_code != 200:

            pytest.skip("Dev login not available")

            

        login_data = login_response.json()

        refresh_token = login_data.get("refresh_token")

        

        # Launch concurrent refresh attempts with the same token

        async def attempt_refresh():

            try:

                response = await client.post(

                    f"{auth_url}/auth/refresh",

                    json={"refresh_token": refresh_token}

                )

                return response.status_code == 200

            except Exception:

                return False

        

        # Launch 5 concurrent attempts

        results = await asyncio.gather(*[attempt_refresh() for _ in range(5)])

        

        # Only one should succeed (first one), others should fail

        successful_attempts = sum(results)

        assert successful_attempts == 1, f"Expected 1 successful refresh, got {successful_attempts}"





if __name__ == "__main__":

    # Ensure auth service is running

    print("Make sure auth service is running on http://localhost:8081")

    print("You can start it with: python scripts/docker_manual.py start --services auth")

    

    # Run the tests

    pytest.main([__file__, "-v", "--tb=short"])

