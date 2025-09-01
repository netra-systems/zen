"""
Startup Optimizer for Development Launcher.

Provides optimized startup sequences for development services.
"""

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Callable, Any
import logging
import time

logger = logging.getLogger(__name__)


class StartupPhase(Enum):
    """Phases of service startup"""
    PRE_INIT = "pre_init"
    INIT = "init"
    POST_INIT = "post_init"
    READY = "ready"


@dataclass
class StartupStep:
    """Individual step in startup sequence"""
    name: str
    phase: StartupPhase
    action: Optional[Callable] = None
    timeout: int = 30
    required: bool = True
    dependencies: List[str] = None
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []


class StartupOptimizer:
    """
    Optimizes service startup sequences for faster development cycles.
    """
    
    def __init__(self, cache_manager=None):
        self.steps: List[StartupStep] = []
        self.completed_steps: List[str] = []
        self.cache_manager = cache_manager
        self.start_time = None
        
    def add_step(self, step: StartupStep):
        """Add a startup step to the sequence"""
        self.steps.append(step)
        
    def optimize_sequence(self) -> List[StartupStep]:
        """
        Optimize the startup sequence based on dependencies.
        
        Returns:
            Optimized list of startup steps
        """
        # Simple implementation - just return steps in order
        # In production, this would do topological sorting based on dependencies
        return self.steps
        
    def execute_step(self, step: StartupStep) -> bool:
        """
        Execute a single startup step.
        
        Args:
            step: The step to execute
            
        Returns:
            Success status
        """
        try:
            logger.info(f"Executing startup step: {step.name}")
            
            if step.action:
                result = step.action()
                if result is False:
                    logger.error(f"Step {step.name} failed")
                    return False
                    
            self.completed_steps.append(step.name)
            logger.info(f"Completed startup step: {step.name}")
            return True
            
        except Exception as e:
            logger.error(f"Error in startup step {step.name}: {e}")
            if step.required:
                raise
            return False
            
    def reset(self):
        """Reset the optimizer state"""
        self.completed_steps.clear()
        
    def is_complete(self) -> bool:
        """Check if all required steps are complete"""
        required_steps = {s.name for s in self.steps if s.required}
        return required_steps.issubset(set(self.completed_steps))
    
    def start_timing(self):
        """Start timing the optimization process"""
        self.start_time = time.time()
        logger.info("StartupOptimizer timing started")
    
    def get_elapsed_time(self) -> float:
        """Get elapsed time since timing started"""
        if self.start_time is None:
            return 0.0
        return time.time() - self.start_time