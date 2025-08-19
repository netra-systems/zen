import asyncio
import httpx

async def check_services():
    services = [
        ("Auth", "http://localhost:8081"),
        ("Backend", "http://localhost:54323"),  # From dev launcher output
    ]
    
    for name, url in services:
        try:
            async with httpx.AsyncClient(timeout=3) as client:
                resp = await client.get(f"{url}/health")
                print(f"{name} ({url}): {resp.status_code}")
        except Exception as e:
            print(f"{name} ({url}): ERROR - {e}")

if __name__ == "__main__":
    asyncio.run(check_services())