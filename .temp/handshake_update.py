    async def _perform_handshake(self) -> bool:
        """
        Wait for proactive handshake from server (as of 2025-10-09).

        Server Phase Alignment:
        - INITIALIZING: WebSocket connection accepted
        - AUTHENTICATING: User validation (happens during connect())
        - HANDSHAKING: Server proactively sends handshake_response (we wait here)
        - READY: Services initialized
        - PROCESSING: Message handling begins

        The client waits during server's HANDSHAKING phase to receive the
        proactive handshake_response without sending any request.
        """
        try:
            import asyncio

            self.debug.debug_print(
                "Waiting for server to enter HANDSHAKING phase and send handshake...",
                DebugLevel.VERBOSE,
                style="cyan"
            )

            # Server enters HANDSHAKING phase after authentication
            # and proactively sends handshake_response
            handshake_timeout = 10.0  # Wait up to 10 seconds
            start_time = asyncio.get_event_loop().time()

            try:
                while (asyncio.get_event_loop().time() - start_time) < handshake_timeout:
                    remaining_time = handshake_timeout - (asyncio.get_event_loop().time() - start_time)

                    # Be ready to receive messages during server's HANDSHAKING phase
                    self.debug.debug_print(
                        f"Listening for handshake (remaining: {remaining_time:.1f}s)...",
                        DebugLevel.VERBOSE,
                        style="dim"
                    )

                    response_msg = await asyncio.wait_for(
                        self.ws.recv(),
                        timeout=min(remaining_time, 1.0)  # Check every second
                    )
                    response = json.loads(response_msg)

                    msg_type = response.get('type', 'unknown')
                    self.debug.debug_print(
                        f"Received: {msg_type}",
                        DebugLevel.VERBOSE,
                        style="cyan"
                    )

                    # Check for the proactive handshake_response
                    if msg_type == 'handshake_response':
                        # Server is in HANDSHAKING phase and sent the handshake
                        self.debug.debug_print(
                            "✅ Server sent proactive handshake (HANDSHAKING phase)",
                            DebugLevel.VERBOSE,
                            style="green"
                        )

                        # Process the handshake
                        result = await self._process_handshake_response(response)

                        if result:
                            self.debug.debug_print(
                                f"Handshake complete - Thread ID: {self.current_thread_id}",
                                DebugLevel.BASIC,
                                style="green"
                            )
                            self.debug.debug_print(
                                "Server phases: AUTH ✓ → HANDSHAKING ✓ → READY",
                                DebugLevel.VERBOSE,
                                style="green"
                            )

                        return result

                    # Handle other message types while waiting
                    elif msg_type == 'connection_established':
                        # This is from AUTHENTICATING phase completion
                        self.debug.debug_print(
                            "Connection established (AUTH phase) - waiting for HANDSHAKING phase",
                            DebugLevel.VERBOSE,
                            style="yellow"
                        )
                        # Store the event but continue waiting
                        if hasattr(self, 'events'):
                            self.events.append(WebSocketEvent.from_dict(response))

                    else:
                        # Other event types - store but keep waiting for handshake
                        self.debug.debug_print(
                            f"Storing {msg_type} event - still waiting for handshake",
                            DebugLevel.VERBOSE,
                            style="dim"
                        )
                        if hasattr(self, 'events'):
                            self.events.append(WebSocketEvent.from_dict(response))

                # Timeout - server didn't send handshake
                self.debug.debug_print(
                    "ERROR: Server did not send handshake within 10 seconds",
                    DebugLevel.BASIC,
                    style="red"
                )
                self.debug.debug_print(
                    "Server may not have HANDSHAKING phase (pre-2025-10-09 version)",
                    DebugLevel.BASIC,
                    style="yellow"
                )
                return False

            except asyncio.TimeoutError:
                # This shouldn't happen with our loop structure, but handle it
                self.debug.debug_print(
                    "ERROR: Timeout waiting for server handshake",
                    DebugLevel.BASIC,
                    style="red"
                )
                return False

        except Exception as e:
            # Handshake error
            error_msg = f"WARNING: Handshake error: {e}"
            self.debug.log_error(e, "handshake protocol")
            self.debug.debug_print(error_msg, DebugLevel.BASIC, style="yellow")
            safe_console_print(error_msg, style="yellow")
            return False