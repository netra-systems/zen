# LLM Token Optimization Data Helper
## AI-Specific Cost & Performance Optimization

---

## Example 1: OpenAI API Costs Too High
**User says:** "Our OpenAI API bills are out of control"

### 🎯 GET YOUR TOKEN USAGE (4 Steps)

```
Let's check your OpenAI usage:

1. Go to: https://platform.openai.com/usage
2. Set date to "Last 30 days"
3. Screenshot the usage graph
4. Reply with screenshot

That's it!
```

**If no access:** "Check your last invoice email from OpenAI and forward it"

**After receiving data:**
```
You're spending $12k/month, mostly on GPT-4!
Quick fix: Want to see which prompts waste the most tokens? (Type 'yes')
```

**Follow-up (3 steps):**
```
Find your expensive prompts:

1. Run: grep "gpt-4" app.log | grep "tokens" | sort -nrk5 | head -10
2. Copy the top 3 lines
3. Send them to me

Or check your logging dashboard for "completion_tokens" metric
```

---

## Example 2: Claude API Optimization
**User says:** "Need to optimize Anthropic Claude usage"

### 🎯 MEASURE TOKEN PATTERNS (4 Steps)

```
Quick Claude metrics check:

1. Open Anthropic Console: https://console.anthropic.com
2. Click "Usage" → Export CSV
3. Open CSV, find "Total Tokens" column
4. Tell me: Average tokens/request: ____

No console access? Run: curl -H "x-api-key: $KEY" https://api.anthropic.com/v1/usage
```

**After response:** "8,000 tokens average"

```
8k tokens/request is HIGH! (Claude costs $0.024/1k output tokens)
Let's find why. Check one thing:
- Average prompt length vs response length?
```

---

## Example 3: LangChain Token Waste
**User says:** "LangChain is using too many tokens"

### 🎯 FIND TOKEN LEAKS (4 Steps)

```
LangChain token audit:

1. Add this to your code temporarily:
   ```python
   from langchain.callbacks import get_openai_callback
   with get_openai_callback() as cb:
       # your chain.run() here
       print(f"Tokens: {cb.total_tokens}")
   ```
2. Run your top 3 workflows
3. Copy the token counts
4. Send me those 3 numbers

Quick alternative: Check LangSmith dashboard → "Token Usage" tab
```

---

## Example 4: RAG System Token Explosion
**User says:** "Our RAG system uses massive tokens"

### 🎯 CHECK CONTEXT SIZE (4 Steps)

```
RAG context check:

1. Log your retrieval: print(len(retrieved_docs))
2. Check chunk size: print(len(retrieved_docs[0]))
3. Run a typical query
4. Reply with: "Retrieved ___ docs of ~___ tokens each"

Or in your vector DB:
- Pinecone: Check index.describe_index_stats()
- Weaviate: Check client.query.aggregate()
```

**After response:** "Retrieved 20 docs of ~800 tokens each"

```
16,000 tokens just for context! That's $0.38 per query on GPT-4.
Want to optimize? I'll show you how to reduce to 5 docs intelligently.
```

---

## Example 5: Prompt Template Bloat
**User says:** "Every API call seems expensive"

### 🎯 AUDIT YOUR PROMPTS (4 Steps)

```
Find prompt waste:

1. Print your system prompt: print(len(SYSTEM_PROMPT.split()))
2. Print a typical user message: print(len(user_input.split()))  
3. Count words (words ≈ tokens × 0.75)
4. Reply: System: ___ words, User: ___ words

Or paste your main prompt template and I'll analyze it
```

---

## Example 6: Multi-Agent Token Multiplication
**User says:** "Agent workflow costs are crazy"

### 🎯 TRACE AGENT TOKENS (4 Steps)

```
Agent token tracking:

1. For each agent, add: print(f"{agent_name}: {response.usage.total_tokens}")
2. Run one complete workflow
3. Copy all the printed lines
4. Send me the list

Using AutoGen? Check: agent.client.total_usage_summary
Using CrewAI? Check: crew.usage_metrics
```

---

# LLM Cost Imagination Agent
## Helping Users Discover AI Optimization Opportunities

---

## 🧠 AI Cost Discovery Flow

### Entry Patterns - User Says:
- "AI is expensive but don't know why"
- "LLM costs keep growing"
- "Not sure which model to use"
- "Tokens are confusing"
- "Is GPT-4 worth it?"
- "Should we fine-tune?"

---

## Discovery Conversations

### Pattern A: Model Selection Discovery
```
AGENT: "Let's optimize your AI costs! What's your main concern?"
        
        💰 Spending too much per request
        ⚡ Responses too slow
        📊 Quality not good enough
        🔄 Using AI for everything
        🤷 Just want it cheaper

USER: "Spending too much per request"

AGENT: "What are you using AI for mainly?"
        
        💬 Chatbot/Support
        ✍️ Content Generation  
        🔍 Data Extraction
        💻 Code Generation
        🎨 Creative Work

USER: "Chatbot/Support"

AGENT: "How complex are the conversations?"
        
        Simple FAQ → Try GPT-3.5 Turbo ($0.0015/1k vs $0.03/1k)
        Technical support → Try Claude Instant
        Complex reasoning → Optimize GPT-4 prompts
        
        Your optimization: "Migrate customer support from GPT-4 to GPT-3.5 Turbo"
```

### Pattern B: Token Waste Discovery
```
AGENT: "Let's find hidden token costs! Pick your biggest AI expense:"
        
        🤖 OpenAI (GPT-3.5/4)
        🧠 Anthropic (Claude)
        🔷 Azure OpenAI
        🦜 Google (PaLM/Gemini)
        🏗️ Multiple providers

USER: "OpenAI"

AGENT: "How do you typically use it?"
        
        API: Direct API calls
        LangChain: Chain/Agent framework
        RAG: With vector search
        Fine-tuned: Custom model
        Playground: Manual testing

USER: "RAG"

AGENT: "Aha! RAG often wastes tokens. Your issue is likely:
        'RAG system includes too much context per query'
        
        Let me help you measure context bloat..."
```

### Pattern C: Unknown Starting Point for AI
```
AGENT: "No problem! Quick AI health check - answer these:"

        "Daily AI requests?"
        [<1k] [1k-10k] [10k-100k] [>100k]

        "Average cost per request?"
        [<$0.01] [$0.01-0.10] [$0.10-1.00] [>$1.00]
        
        "Biggest pain?"
        [Cost] [Speed] [Quality] [Complexity]

USER: "10k-100k, $0.10-1.00, Cost"

AGENT: "At ~50k requests/day × $0.50 = $750/day on AI!
        
        Top savings opportunities:
        🎯 Prompt compression (30-50% reduction)
        🎯 Caching repeated queries (40% savings)
        🎯 Model routing (use cheaper models when possible)
        
        Start with which?"
```

---

## Token Optimization Techniques

### A. The "Token Calculator" Technique
```
AGENT: "Let's calculate your token waste:
        
        Paste your typical prompt here, and I'll show:
        - Actual tokens: ___
        - Wasted tokens: ___
        - Optimized version: ___
        - Savings: $___/month"
```

### B. The "Model Arbitrage" Technique
```
AGENT: "Different tasks need different models:
        
        Your task: '_______'
        
        Currently using: GPT-4 ($0.03/1k)
        Could use: GPT-3.5 Turbo ($0.0015/1k)
        Savings: 95% on this task
        
        Want me to test quality difference?"
```

### C. The "Context Window" Technique
```
AGENT: "How much context do you really need?
        
        Current: Sending 10 documents
        Tested: 3 documents give 90% accuracy
        Savings: 70% token reduction
        
        Worth the 10% accuracy trade-off?"
```

---

## Implementation Code Examples

### Quick Token Counter
```python
def quick_token_audit(prompt, response):
    """Instant token waste detection"""
    import tiktoken
    enc = tiktoken.encoding_for_model("gpt-4")
    
    prompt_tokens = len(enc.encode(prompt))
    response_tokens = len(enc.encode(response))
    
    # Detect waste
    waste_indicators = {
        "repeated_context": prompt.count("Instructions:") > 1,
        "verbose_json": "```json" in prompt and len(prompt) > 2000,
        "example_overload": prompt.count("Example:") > 3,
        "system_prompt_bloat": prompt.startswith("You are") and len(prompt.split("\n")[0]) > 200
    }
    
    return {
        "prompt_tokens": prompt_tokens,
        "response_tokens": response_tokens,
        "total_cost": (prompt_tokens * 0.03 + response_tokens * 0.06) / 1000,
        "waste_found": [k for k, v in waste_indicators.items() if v]
    }
```

### Smart Model Router
```python
def route_to_optimal_model(task_complexity, speed_required, quality_required):
    """Pick cheapest model that meets requirements"""
    
    models = {
        "gpt-3.5-turbo": {"cost": 0.0015, "speed": 10, "quality": 7},
        "gpt-4-turbo": {"cost": 0.01, "speed": 7, "quality": 9},
        "gpt-4": {"cost": 0.03, "speed": 5, "quality": 10},
        "claude-instant": {"cost": 0.0008, "speed": 10, "quality": 7},
        "claude-2": {"cost": 0.008, "speed": 7, "quality": 9}
    }
    
    # Filter by requirements
    suitable = [
        m for m, specs in models.items()
        if specs["quality"] >= quality_required 
        and specs["speed"] >= speed_required
    ]
    
    # Pick cheapest
    return min(suitable, key=lambda m: models[m]["cost"])
```

### Prompt Compression
```python
def compress_prompt(original_prompt):
    """Reduce tokens while maintaining meaning"""
    
    compressions = {
        # Remove fluff
        "Please could you": "",
        "I would like you to": "",
        "Can you please": "",
        
        # Shorten instructions
        "Your task is to": "Task:",
        "You should": "Must",
        "Make sure to": "Must",
        
        # Compress formats
        "in JSON format": "JSON:",
        "as a bullet list": "List:",
        "step by step": "Steps:"
    }
    
    compressed = original_prompt
    for long, short in compressions.items():
        compressed = compressed.replace(long, short)
    
    # Remove extra whitespace
    compressed = " ".join(compressed.split())
    
    return compressed
```

---

## Common LLM Token Waste Patterns

### 1. **System Prompt Obesity**
```
BEFORE: 500 tokens of "You are a helpful, harmless, honest AI assistant..."
AFTER: 50 tokens of role definition
SAVINGS: $15/day at 10k requests
```

### 2. **RAG Context Dump**
```
BEFORE: Retrieve 20 documents, send all
AFTER: Retrieve 20, rerank, send top 3
SAVINGS: 85% context tokens
```

### 3. **JSON Template Bloat**
```
BEFORE: Send full JSON schema in every request
AFTER: Send schema once, reference by ID
SAVINGS: 200-500 tokens per request
```

### 4. **Example Overload**
```
BEFORE: 10 examples in every prompt
AFTER: 2 most relevant examples
SAVINGS: 70% of prompt tokens
```

### 5. **Chain Repetition**
```
BEFORE: Each agent repeats full context
AFTER: Pass summary + deltas only
SAVINGS: 60% in multi-agent systems
```

---

## Quick Optimization Wins

### Immediate Actions (Same Day)
1. **Switch simple tasks to GPT-3.5 Turbo** → 95% cost reduction
2. **Add response length limits** → `max_tokens=500` 
3. **Cache frequent queries** → 40% reduction
4. **Compress prompts** → 30% fewer tokens

### Week 1 Optimizations
1. **Implement model routing** → Right model for each task
2. **Add semantic caching** → Avoid duplicate API calls
3. **Optimize RAG retrieval** → Fewer, better documents
4. **Batch similar requests** → Better rate limits

### Month 1 Transformations
1. **Fine-tune smaller models** → 10x cost reduction
2. **Implement prompt templates** → Consistent optimization
3. **Add token budgets** → Cost controls
4. **Build fallback chains** → Graceful degradation

---

## ROI Calculator

```
Current State:
- 50,000 requests/day
- GPT-4 for everything
- 2000 tokens average per request
- Cost: $3,000/day

After Optimization:
- 30% to GPT-3.5 Turbo: $45/day
- 50% with compressed prompts: $750/day  
- 20% with caching: $0/day
- New cost: $795/day

SAVINGS: $2,205/day (73.5% reduction)
ANNUAL SAVINGS: $804,825
```

---

## Success Metrics

### Token Efficiency
- Tokens per meaningful output: Reduce by 50%
- Cache hit rate: >30%
- Model routing accuracy: >90%

### Cost Metrics  
- Cost per request: Reduce by 60-80%
- Monthly API spend: Reduce by 50-70%
- ROI on optimization: 10-50x

### Quality Maintenance
- User satisfaction: Maintain or improve
- Response accuracy: >95% of original
- Latency: Improve by 30%