SPEC:  WS Websockets

1:0: Primary Spec: WS Websockets Specification.
1:1:0: Goal: WS working as a complete end to end system.
1:1:1: CRITICAL: The Coherence of the system working in harmony front and backend together.
1:1:1:0: Cohernece: Coherence with User Auth using WS
1:1:1:1: Coherence: Agent communications using WS

Careful:
1:0:1:0: Careful: Lanchain stream to JSON parsing
1:0:1:1: Careful: WS use JSON not string
1:0:1:2: Careful: Protect against multiple functions or processing double or triple wrapping JSON badly

1:0:1:3: Module imports: Check module imports and add tests for validating modules import

1:0:2:0: Frontend: WebSocket connection concepts.
1:0:2:1: WebSocket connection is established statefully on application state load (BEFORE the first message is sent.) It is an ERROR if WS can’t be established.
1:0:2:2: WebSocket connection is persistent.
1:0:2:3: Important: WebSocket connection resilient to component re-renders and lifecycle changes.
Websockets works with regular JSON etc. when the user sends chat messages or free text or clicking examples etc.
1:0::2:4: WS messages are passed properly and use types.

1:0:2: Backend:
1:0:2:0: WS Startup profile: When application starts up or reloads, WS are available.
1:0:2:1: If the front end sends a socket but the backend rejects, it must be logged clearly. 
1:0:2:2: Backend sends responses using a single source of truth to manage WS.
1:0:2:4: Backend: Always complete JSON objects.

Remember: 0:7.  Remember: 0:1 to 0:7 to 1 including all sub items 1:0:0 through 1:2: etc.
