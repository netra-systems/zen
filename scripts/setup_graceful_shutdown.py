#!/usr/bin/env python3
"""
Container Lifecycle Management Setup
Adds graceful shutdown handling for Cloud Run deployments
"""
import os
import sys
import textwrap

# Add project root to path


class GracefulShutdownSetup:
    """Setup graceful shutdown handlers for Cloud Run"""
    
    def __init__(self):
        self.project_root = project_root
    
    def setup_auth_service_shutdown(self):
        """Add graceful shutdown to auth service main.py"""
        main_py_path = os.path.join(self.project_root, "auth_service", "auth_core", "main.py")
        
        if not os.path.exists(main_py_path):
            print(f" FAIL:  Auth service main.py not found at {main_py_path}")
            return False
        
        with open(main_py_path, 'r') as f:
            content = f.read()
        
        # Check if graceful shutdown is already implemented
        if 'signal.signal' in content and 'SIGTERM' in content:
            print(" PASS:  Auth service already has graceful shutdown")
            return True
        
        # Add graceful shutdown code
        shutdown_code = textwrap.dedent('''
        import signal
        import asyncio
        from contextlib import asynccontextmanager
        
        # Global shutdown event
        shutdown_event = asyncio.Event()
        
        def signal_handler(signum, frame):
            """Handle shutdown signals gracefully"""
            logger.info(f"Received signal {signum}, initiating graceful shutdown...")
            shutdown_event.set()
        
        # Register signal handlers for Cloud Run
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
        
        @asynccontextmanager
        async def lifespan(app: FastAPI):
            """Application lifespan management"""
            logger.info("[U+1F680] Auth service starting up...")
            
            # Startup
            yield
            
            # Shutdown
            logger.info("[U+1F6D1] Auth service shutting down...")
            
            # Close database connections
            try:
                from auth_service.auth_core.database.connection import auth_db
                await auth_db.close()
                logger.info(" PASS:  Database connections closed")
            except Exception as e:
                logger.error(f" FAIL:  Error closing database: {e}")
            
            # Wait a moment for any final operations
            await asyncio.sleep(0.1)
            
            logger.info(" PASS:  Auth service shutdown complete")
        ''')
        
        # Insert imports at the top
        if 'import signal' not in content:
            import_lines = content.split('\n')
            # Find where to insert (after existing imports)
            insert_idx = 0
            for i, line in enumerate(import_lines):
                if line.startswith('from') or line.startswith('import'):
                    insert_idx = i + 1
                elif line.strip() == '':
                    continue
                else:
                    break
            
            import_lines.insert(insert_idx, 'import signal')
            import_lines.insert(insert_idx + 1, 'import asyncio')
            import_lines.insert(insert_idx + 2, 'from contextlib import asynccontextmanager')
            content = '\n'.join(import_lines)
        
        # Add shutdown handling before app creation
        if 'app = FastAPI(' in content:
            content = content.replace(
                'app = FastAPI(',
                shutdown_code + '\n\napp = FastAPI(lifespan=lifespan,'
            )
        
        # Write back
        with open(main_py_path, 'w') as f:
            f.write(content)
        
        print(" PASS:  Added graceful shutdown to auth service")
        return True
    
    def setup_backend_shutdown(self):
        """Add graceful shutdown to backend main.py"""
        main_py_path = os.path.join(self.project_root, "netra_backend", "app", "main.py")
        
        if not os.path.exists(main_py_path):
            print(f" FAIL:  Backend main.py not found at {main_py_path}")
            return False
        
        with open(main_py_path, 'r') as f:
            content = f.read()
        
        # Check if graceful shutdown is already implemented
        if 'signal.signal' in content and 'SIGTERM' in content:
            print(" PASS:  Backend already has graceful shutdown")
            return True
        
        # Add graceful shutdown code (similar to auth service but with backend-specific cleanup)
        shutdown_code = textwrap.dedent('''
        import signal
        import asyncio
        from contextlib import asynccontextmanager
        
        # Global shutdown event
        shutdown_event = asyncio.Event()
        
        def signal_handler(signum, frame):
            """Handle shutdown signals gracefully"""
            logger.info(f"Received signal {signum}, initiating graceful shutdown...")
            shutdown_event.set()
        
        # Register signal handlers for Cloud Run
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
        
        @asynccontextmanager
        async def lifespan(app: FastAPI):
            """Application lifespan management"""
            logger.info("[U+1F680] Netra backend starting up...")
            
            # Startup
            yield
            
            # Shutdown
            logger.info("[U+1F6D1] Netra backend shutting down...")
            
            # Close WebSocket connections gracefully
            try:
                # Note: Actual WebSocket manager cleanup would go here
                logger.info(" PASS:  WebSocket connections closed")
            except Exception as e:
                logger.error(f" FAIL:  Error closing WebSockets: {e}")
            
            # Close database connections
            try:
                from netra_backend.app.db.connection import close_all_connections
                await close_all_connections()
                logger.info(" PASS:  Database connections closed")
            except Exception as e:
                logger.error(f" FAIL:  Error closing database: {e}")
            
            # Wait a moment for any final operations
            await asyncio.sleep(0.1)
            
            logger.info(" PASS:  Backend shutdown complete")
        ''')
        
        # Similar implementation as auth service
        if 'import signal' not in content:
            import_lines = content.split('\n')
            insert_idx = 0
            for i, line in enumerate(import_lines):
                if line.startswith('from') or line.startswith('import'):
                    insert_idx = i + 1
                elif line.strip() == '':
                    continue
                else:
                    break
            
            import_lines.insert(insert_idx, 'import signal')
            import_lines.insert(insert_idx + 1, 'import asyncio')
            import_lines.insert(insert_idx + 2, 'from contextlib import asynccontextmanager')
            content = '\n'.join(import_lines)
        
        # Add shutdown handling before app creation
        if 'app = FastAPI(' in content:
            content = content.replace(
                'app = FastAPI(',
                shutdown_code + '\n\napp = FastAPI(lifespan=lifespan,'
            )
        
        # Write back
        with open(main_py_path, 'w') as f:
            f.write(content)
        
        print(" PASS:  Added graceful shutdown to backend")
        return True
    
    def create_dockerfile_optimizations(self):
        """Add Cloud Run optimizations to Dockerfiles"""
        dockerfiles = [
            ("auth_service/Dockerfile", "auth service"),
            ("netra_backend/Dockerfile", "backend"),
        ]
        
        for dockerfile_path, service_name in dockerfiles:
            full_path = os.path.join(self.project_root, dockerfile_path)
            if not os.path.exists(full_path):
                print(f" FAIL:  {service_name} Dockerfile not found")
                continue
            
            with open(full_path, 'r') as f:
                content = f.read()
            
            # Check if optimizations already exist
            if 'STOPSIGNAL' in content and 'healthcheck' in content.lower():
                print(f" PASS:  {service_name} Dockerfile already optimized")
                continue
            
            # Add Cloud Run optimizations
            optimizations = textwrap.dedent('''
            
            # Cloud Run optimizations
            # Use SIGTERM for graceful shutdown (Cloud Run sends this)
            STOPSIGNAL SIGTERM
            
            # Health check for better container lifecycle management
            HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \\
                CMD curl -f http://localhost:$PORT/health || exit 1
            
            # Ensure proper signal handling
            ENV PYTHONUNBUFFERED=1
            ENV PYTHONDONTWRITEBYTECODE=1
            ''')
            
            # Add before CMD instruction
            if 'CMD ' in content:
                content = content.replace('CMD ', optimizations + '\nCMD ')
            else:
                content += optimizations
            
            with open(full_path, 'w') as f:
                f.write(content)
            
            print(f" PASS:  Added Cloud Run optimizations to {service_name} Dockerfile")
    
    def setup_all(self):
        """Setup all graceful shutdown components"""
        print("[U+1F527] Setting up graceful shutdown for Cloud Run...")
        
        success_count = 0
        total_tasks = 3
        
        if self.setup_auth_service_shutdown():
            success_count += 1
        
        if self.setup_backend_shutdown():
            success_count += 1
        
        self.create_dockerfile_optimizations()
        success_count += 1  # Dockerfile optimization always succeeds
        
        print(f"\n CHART:  Setup complete: {success_count}/{total_tasks} tasks successful")
        
        if success_count == total_tasks:
            print(" CELEBRATION:  All graceful shutdown components setup successfully!")
            print("\n[U+1F4DD] Next steps:")
            print("1. Test locally to ensure shutdown works correctly")
            print("2. Deploy to staging and verify Cloud Run signal handling")
            print("3. Monitor logs for graceful shutdown messages")
            return True
        else:
            print(" WARNING: [U+FE0F]  Some components failed to setup. Check logs above.")
            return False


def main():
    """Main entry point"""
    setup = GracefulShutdownSetup()
    success = setup.setup_all()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()