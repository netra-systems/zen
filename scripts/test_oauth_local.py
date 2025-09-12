from shared.isolated_environment import get_env
from shared.isolated_environment import IsolatedEnvironment
#!/usr/bin/env python3
"""
Local OAuth Testing Script with Enhanced Debugging
Tests the complete OAuth flow locally with detailed logging

This script:
1. Tests OAuth configuration
2. Simulates OAuth login flow
3. Validates token generation
4. Checks auth service communication
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from typing import Dict, Optional

# Fix Windows Unicode issues
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

import httpx
import click
from rich import print as rprint
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# Add parent directory to path

console = Console(force_terminal=True if sys.platform == 'win32' else None)


class OAuthLocalTester:
    """Test OAuth flow locally with debugging"""
    
    def __init__(self, backend_url: str = "http://localhost:8000", 
                 auth_url: str = "http://localhost:8081"):
        self.backend_url = backend_url
        self.auth_url = auth_url
        self.session = httpx.AsyncClient(timeout=30.0, follow_redirects=False)
        self.test_results = {
            'config_check': None,
            'auth_service_health': None,
            'backend_health': None,
            'oauth_initiation': None,
            'token_generation': None,
            'token_validation': None
        }
        
    async def check_environment(self) -> Dict:
        """Check environment configuration"""
        console.print("\n[bold cyan]1. Checking Environment Configuration[/bold cyan]")
        
        env_vars = {
            'OAUTH_GOOGLE_CLIENT_ID_ENV': get_env().get('OAUTH_GOOGLE_CLIENT_ID_ENV'),
            'OAUTH_GOOGLE_CLIENT_SECRET_ENV': get_env().get('OAUTH_GOOGLE_CLIENT_SECRET_ENV'),
            'JWT_SECRET_KEY': get_env().get('JWT_SECRET_KEY'),
            'AUTH_SERVICE_URL': get_env().get('AUTH_SERVICE_URL'),
            'FRONTEND_URL': get_env().get('FRONTEND_URL')
        }
        
        config_table = Table(show_header=True, header_style="bold magenta")
        config_table.add_column("Variable", style="cyan")
        config_table.add_column("Status", justify="center")
        config_table.add_column("Value", style="dim")
        
        all_set = True
        for var, value in env_vars.items():
            if value:
                status = "[green][U+2713][/green]"
                # Mask sensitive values
                if 'SECRET' in var or 'KEY' in var:
                    display_value = value[:10] + '...' if len(value) > 10 else '***'
                else:
                    display_value = value[:50] if len(value) > 50 else value
            else:
                status = "[red][U+2717][/red]"
                display_value = "Not Set"
                all_set = False
            
            config_table.add_row(var, status, display_value)
        
        console.print(config_table)
        
        self.test_results['config_check'] = {
            'passed': all_set,
            'env_vars': env_vars
        }
        
        return env_vars
    
    async def check_service_health(self) -> Dict:
        """Check health of backend and auth services"""
        console.print("\n[bold cyan]2. Checking Service Health[/bold cyan]")
        
        results = {}
        
        # Check backend
        try:
            response = await self.session.get(f"{self.backend_url}/health")
            backend_healthy = response.status_code == 200
            results['backend'] = {
                'healthy': backend_healthy,
                'status_code': response.status_code,
                'response': response.json() if backend_healthy else None
            }
            console.print(f"  Backend Service: [green][U+2713] Healthy[/green]" if backend_healthy 
                         else f"  Backend Service: [red][U+2717] Unhealthy ({response.status_code})[/red]")
        except Exception as e:
            results['backend'] = {'healthy': False, 'error': str(e)}
            console.print(f"  Backend Service: [red][U+2717] Not reachable - {e}[/red]")
        
        # Check auth service
        try:
            response = await self.session.get(f"{self.auth_url}/health")
            auth_healthy = response.status_code == 200
            results['auth'] = {
                'healthy': auth_healthy,
                'status_code': response.status_code,
                'response': response.json() if auth_healthy else None
            }
            console.print(f"  Auth Service: [green][U+2713] Healthy[/green]" if auth_healthy 
                         else f"  Auth Service: [red][U+2717] Unhealthy ({response.status_code})[/red]")
        except Exception as e:
            results['auth'] = {'healthy': False, 'error': str(e)}
            console.print(f"  Auth Service: [red][U+2717] Not reachable - {e}[/red]")
        
        self.test_results['auth_service_health'] = results.get('auth')
        self.test_results['backend_health'] = results.get('backend')
        
        return results
    
    async def test_oauth_config_endpoint(self) -> Dict:
        """Test OAuth configuration endpoint"""
        console.print("\n[bold cyan]3. Testing OAuth Config Endpoint[/bold cyan]")
        
        try:
            response = await self.session.get(f"{self.backend_url}/auth/config")
            
            if response.status_code == 200:
                config = response.json()
                console.print(f"  [green][U+2713][/green] Config endpoint returned successfully")
                
                # Display config
                config_info = Panel(
                    f"[bold]Provider:[/bold] {config.get('provider', 'N/A')}\n"
                    f"[bold]Auth URL:[/bold] {config.get('authUrl', 'N/A')}\n"
                    f"[bold]Client ID:[/bold] {config.get('clientId', 'N/A')[:20]}...\n"
                    f"[bold]Redirect URI:[/bold] {config.get('redirectUri', 'N/A')}",
                    title="OAuth Configuration",
                    border_style="green"
                )
                console.print(config_info)
                
                return {
                    'success': True,
                    'config': config
                }
            else:
                console.print(f"  [red][U+2717][/red] Config endpoint failed: {response.status_code}")
                console.print(f"  Response: {response.text[:200]}")
                return {
                    'success': False,
                    'status_code': response.status_code,
                    'error': response.text
                }
        except Exception as e:
            console.print(f"  [red][U+2717][/red] Error fetching config: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def test_oauth_login_flow(self) -> Dict:
        """Test OAuth login initiation"""
        console.print("\n[bold cyan]4. Testing OAuth Login Initiation[/bold cyan]")
        
        try:
            # Test login endpoint
            response = await self.session.get(
                f"{self.backend_url}/auth/login?provider=google",
                follow_redirects=False
            )
            
            if response.status_code in [302, 303, 307]:
                location = response.headers.get('location', '')
                console.print(f"  [green][U+2713][/green] Login endpoint redirects correctly")
                console.print(f"  Redirect to: [cyan]{location[:100]}...[/cyan]")
                
                # Check if it's redirecting to auth service
                if self.auth_url in location or 'auth.staging' in location:
                    console.print(f"  [green][U+2713][/green] Correctly redirecting to auth service")
                else:
                    console.print(f"  [yellow] WARNING: [/yellow] Unexpected redirect location")
                
                self.test_results['oauth_initiation'] = {
                    'success': True,
                    'redirect_url': location
                }
                
                return {
                    'success': True,
                    'redirect_url': location
                }
            else:
                console.print(f"  [red][U+2717][/red] Login endpoint didn't redirect: {response.status_code}")
                console.print(f"  Response: {response.text[:200]}")
                
                self.test_results['oauth_initiation'] = {
                    'success': False,
                    'status_code': response.status_code
                }
                
                return {
                    'success': False,
                    'status_code': response.status_code,
                    'response': response.text
                }
        except Exception as e:
            console.print(f"  [red][U+2717][/red] Error testing login flow: {e}")
            self.test_results['oauth_initiation'] = {
                'success': False,
                'error': str(e)
            }
            return {
                'success': False,
                'error': str(e)
            }
    
    async def test_token_generation(self) -> Dict:
        """Test token generation with mock user"""
        console.print("\n[bold cyan]5. Testing Token Generation[/bold cyan]")
        
        # Try dev login if available
        if get_env().get('ALLOW_DEV_LOGIN') == 'true':
            try:
                response = await self.session.post(
                    f"{self.backend_url}/auth/dev_login",
                    json={
                        "email": "test@example.com",
                        "provider": "dev"
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if 'access_token' in data:
                        console.print(f"  [green][U+2713][/green] Token generated successfully")
                        console.print(f"  Token (first 20 chars): [cyan]{data['access_token'][:20]}...[/cyan]")
                        
                        self.test_results['token_generation'] = {
                            'success': True,
                            'token': data['access_token']
                        }
                        
                        # Test token validation
                        await self.test_token_validation(data['access_token'])
                        
                        return {
                            'success': True,
                            'token': data['access_token']
                        }
                    else:
                        console.print(f"  [red][U+2717][/red] No token in response")
                        console.print(f"  Response: {data}")
                else:
                    console.print(f"  [red][U+2717][/red] Dev login failed: {response.status_code}")
                    console.print(f"  Response: {response.text[:200]}")
                
                self.test_results['token_generation'] = {
                    'success': False,
                    'status_code': response.status_code
                }
                
            except Exception as e:
                console.print(f"  [red][U+2717][/red] Error testing token generation: {e}")
                self.test_results['token_generation'] = {
                    'success': False,
                    'error': str(e)
                }
        else:
            console.print("  [yellow] WARNING: [/yellow] Dev login not enabled - skipping token generation test")
            self.test_results['token_generation'] = {
                'success': False,
                'reason': 'Dev login not enabled'
            }
        
        return {'success': False}
    
    async def test_token_validation(self, token: str) -> Dict:
        """Test token validation"""
        console.print("\n[bold cyan]6. Testing Token Validation[/bold cyan]")
        
        try:
            # Test with backend /me endpoint
            response = await self.session.get(
                f"{self.backend_url}/auth/me",
                headers={"Authorization": f"Bearer {token}"}
            )
            
            if response.status_code == 200:
                user_data = response.json()
                console.print(f"  [green][U+2713][/green] Token validated successfully")
                console.print(f"  User: [cyan]{user_data.get('email', 'N/A')}[/cyan]")
                
                self.test_results['token_validation'] = {
                    'success': True,
                    'user': user_data
                }
                
                return {
                    'success': True,
                    'user': user_data
                }
            else:
                console.print(f"  [red][U+2717][/red] Token validation failed: {response.status_code}")
                console.print(f"  Response: {response.text[:200]}")
                
                self.test_results['token_validation'] = {
                    'success': False,
                    'status_code': response.status_code
                }
                
                return {
                    'success': False,
                    'status_code': response.status_code
                }
        except Exception as e:
            console.print(f"  [red][U+2717][/red] Error validating token: {e}")
            self.test_results['token_validation'] = {
                'success': False,
                'error': str(e)
            }
            return {
                'success': False,
                'error': str(e)
            }
    
    def generate_report(self) -> None:
        """Generate test report"""
        console.print("\n[bold cyan][U+2550][U+2550][U+2550] OAuth Local Test Report [U+2550][U+2550][U+2550][/bold cyan]\n")
        
        # Create summary table
        summary_table = Table(show_header=True, header_style="bold magenta")
        summary_table.add_column("Test", style="cyan")
        summary_table.add_column("Result", justify="center")
        summary_table.add_column("Details")
        
        for test_name, result in self.test_results.items():
            if result is None:
                status = "[yellow][U+2298][/yellow]"
                details = "Not tested"
            elif isinstance(result, dict) and result.get('success'):
                status = "[green][U+2713][/green]"
                details = "Passed"
            elif isinstance(result, dict) and result.get('healthy'):
                status = "[green][U+2713][/green]"
                details = "Healthy"
            elif isinstance(result, dict) and result.get('passed'):
                status = "[green][U+2713][/green]"
                details = "All configured"
            else:
                status = "[red][U+2717][/red]"
                if isinstance(result, dict):
                    if 'error' in result:
                        details = f"Error: {result['error'][:50]}"
                    elif 'status_code' in result:
                        details = f"Status: {result['status_code']}"
                    elif 'reason' in result:
                        details = result['reason']
                    else:
                        details = "Failed"
                else:
                    details = "Failed"
            
            test_display = test_name.replace('_', ' ').title()
            summary_table.add_row(test_display, status, details)
        
        console.print(summary_table)
        
        # Print recommendations
        self._print_recommendations()
    
    def _print_recommendations(self) -> None:
        """Print recommendations based on test results"""
        console.print("\n[bold green][U+1F4CB] Recommendations:[/bold green]")
        
        recommendations = []
        
        # Check config
        if self.test_results.get('config_check') and not self.test_results['config_check'].get('passed'):
            env_vars = self.test_results['config_check'].get('env_vars', {})
            if not env_vars.get('GOOGLE_CLIENT_ID'):
                recommendations.append("1. Set GOOGLE_CLIENT_ID in .env file")
            if not env_vars.get('GOOGLE_CLIENT_SECRET'):
                recommendations.append("2. Set GOOGLE_CLIENT_SECRET in .env file")
            if not env_vars.get('JWT_SECRET_KEY'):
                recommendations.append("3. Set JWT_SECRET_KEY in .env file (must match auth service)")
        
        # Check services
        if self.test_results.get('auth_service_health') and not self.test_results['auth_service_health'].get('healthy'):
            recommendations.append("4. Start auth service: python -m auth_service.auth_core.main")
        
        if self.test_results.get('backend_health') and not self.test_results['backend_health'].get('healthy'):
            recommendations.append("5. Start backend service: python scripts/dev_launcher.py")
        
        # Check OAuth flow
        if self.test_results.get('oauth_initiation') and not self.test_results['oauth_initiation'].get('success'):
            recommendations.append("6. Check OAuth redirect configuration in backend")
        
        if self.test_results.get('token_generation') and not self.test_results['token_generation'].get('success'):
            if self.test_results['token_generation'].get('reason') == 'Dev login not enabled':
                recommendations.append("7. Enable dev login: Set ALLOW_DEV_LOGIN=true in .env")
            else:
                recommendations.append("7. Check token generation in auth service")
        
        if recommendations:
            for rec in recommendations:
                console.print(f"  [green][U+2713][/green] {rec}")
        else:
            console.print("  [green][U+2713][/green] All tests passed! OAuth is properly configured.")
    
    async def cleanup(self):
        """Clean up resources"""
        await self.session.aclose()


async def async_main(backend_url: str, auth_url: str, export: Optional[str]):
    """Test OAuth flow locally with enhanced debugging"""
    
    console.print("[bold blue]Starting Local OAuth Testing[/bold blue]")
    console.print(f"Backend URL: [cyan]{backend_url}[/cyan]")
    console.print(f"Auth URL: [cyan]{auth_url}[/cyan]")
    
    tester = OAuthLocalTester(backend_url, auth_url)
    
    try:
        # Run tests
        await tester.check_environment()
        await tester.check_service_health()
        await tester.test_oauth_config_endpoint()
        await tester.test_oauth_login_flow()
        await tester.test_token_generation()
        
        # Generate report
        tester.generate_report()
        
        # Export if requested
        if export:
            with open(export, 'w') as f:
                json.dump({
                    'timestamp': datetime.now().isoformat(),
                    'backend_url': backend_url,
                    'auth_url': auth_url,
                    'results': tester.test_results
                }, f, indent=2)
            console.print(f"\n[green][U+2713] Results exported to {export}[/green]")
        
    except Exception as e:
        console.print(f"\n[red]Error during testing: {e}[/red]")
        raise
    finally:
        await tester.cleanup()


@click.command()
@click.option('--backend-url', default='http://localhost:8000', help='Backend service URL')
@click.option('--auth-url', default='http://localhost:8081', help='Auth service URL')
@click.option('--export', '-e', help='Export results to JSON file')
def main(backend_url: str, auth_url: str, export: Optional[str]):
    """Test OAuth flow locally with enhanced debugging"""
    asyncio.run(async_main(backend_url, auth_url, export))


if __name__ == '__main__':
    main()
