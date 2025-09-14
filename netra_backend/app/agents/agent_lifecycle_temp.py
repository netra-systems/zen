    def _increment_execution_step(self) -> None:
        """Increment execution step counter in agent's internal state."""
        # Store step count in the agent instance, not in UserExecutionContext
        if not hasattr(self, '_execution_steps'):
            self._execution_steps = 0
        self._execution_steps += 1