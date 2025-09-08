# Data Helper Agent - Streamlined V4
## Maximum 4 Steps to Start

---

## Example 1: AWS Cloud Cost Optimization
**User says:** "Help me optimize my AWS cloud costs"

### 🎯 GET YOUR AWS BILL (4 Steps)

```
Let's get your AWS costs in 4 quick steps:

1. Go to: https://console.aws.amazon.com → Log in
2. Search box at top → Type "Cost Explorer" → Press Enter  
3. Click "Download CSV" button
4. Reply with that CSV file attached

Done! 
```

**If stuck:** Type "help" and I'll guide you through screenshots instead

**After receiving data:**
```
Got it! You're spending $45k/month. EC2 is 60% of that.
Want to see why? (Type 'yes' for 2 more steps)
```

---

## Example 2: Database Performance
**User says:** "Our database is slow"

### 🎯 MEASURE THE SLOWNESS (4 Steps)

```
Let's measure how slow:

1. Open your app
2. Do the slow action (e.g., load customer list)
3. Time it with your phone
4. Reply: "It takes ___ seconds"

That's it!
```

**After response:** "15 seconds"

```
15 seconds is very slow! 
Want to find why? Reply 'yes' for the next check (just 3 steps)
```

---

## Example 3: Kubernetes Costs
**User says:** "Need to optimize Kubernetes"

### 🎯 CHECK RESOURCE USAGE (4 Steps)

```
Let's see your cluster usage:

1. Open terminal
2. Type: kubectl top nodes
3. Copy what appears
4. Paste it in your reply

No kubectl? Just ask your team: "What's our cluster CPU usage?"
```

---

## Example 4: Redis Cache Issues  
**User says:** "Redis cache not working well"

### 🎯 CHECK HIT RATE (4 Steps)

```
Quick cache check:

1. Open terminal
2. Type: redis-cli INFO stats | grep keyspace
3. Copy the 2 lines that appear
4. Reply with those lines

No access? Ask your team: "What's our Redis hit rate?"
```

---

## Example 5: Lambda Expensive
**User says:** "Lambda costs too much"

### 🎯 FIND THE COSTLY FUNCTION (4 Steps)

```
Let's find the expensive function:

1. AWS Console → Cost Explorer
2. Filter → Service → Lambda
3. Screenshot the top item
4. Send me that screenshot

Takes 30 seconds!
```

---

## Example 6: API Rate Limits
**User says:** "Getting rate limited"

### 🎯 COUNT YOUR TRAFFIC (4 Steps)

```
Quick traffic check:

1. How many users do you have? (roughly)
2. Pick one:
   [ ] <1000
   [ ] 1000-10000  
   [ ] >10000
3. Peak time? (e.g., "9am EST")
4. Reply with those 2 answers

Super quick!
```

---

# Imagination Agent Plan
## Helping Users Discover What to Optimize

---

## 🧠 Imagination Agent Concept

**Purpose:** Help users who know something is wrong but don't know what to optimize

**Core Function:** Transform vague concerns into specific optimization targets through guided discovery

---

## Agent Architecture

### 1. Entry Detection Patterns
Users who need the Imagination Agent typically say:
- "Things are expensive but I don't know why"
- "System feels slow"
- "We're having issues"
- "Help me improve things"
- "Where do I start?"
- "What should I optimize?"
- "Is there waste in our system?"

### 2. Discovery Flow

```mermaid
stateDiagram-v2
    [*] --> VagueConcern: User has general concern
    
    VagueConcern --> CategoryProbe: Imagination Agent activates
    
    state CategoryProbe {
        [*] --> AskCategory
        AskCategory --> Cost: "Spending too much"
        AskCategory --> Performance: "Too slow"
        AskCategory --> Reliability: "Breaks often"
        AskCategory --> Scale: "Can't grow"
        AskCategory --> Unknown: "Not sure"
    }
    
    Cost --> CostDiscovery
    Performance --> PerfDiscovery
    Reliability --> ReliabilityDiscovery
    Scale --> ScaleDiscovery
    Unknown --> GeneralDiscovery
    
    state CostDiscovery {
        [*] --> BillCheck
        BillCheck --> FindSpikes
        FindSpikes --> IdentifyWaste
        IdentifyWaste --> SuggestTarget
    }
    
    state PerfDiscovery {
        [*] --> UserPath
        UserPath --> MeasureSteps
        MeasureSteps --> FindBottleneck
        FindBottleneck --> SuggestTarget
    }
    
    SuggestTarget --> SpecificPrompt: Generate optimization prompt
    SpecificPrompt --> DataHelper: Trigger Data Helper
    DataHelper --> [*]
```

---

## 3. Conversation Patterns

### Pattern A: Cost Discovery
```
AGENT: "I'll help you find optimization opportunities! 
        What's your biggest pain point?"
        
        💰 Costs too high
        ⚡ System too slow  
        🔥 Things keep breaking
        📈 Can't handle growth
        🤷 Not sure, just help

USER: "Costs too high"

AGENT: "Let's find where money is hiding! Pick your situation:"
        
        ☁️ Cloud bills keep growing
        💻 Too many servers/resources
        📊 Don't know what we're paying for
        🔄 Paying for stuff we don't use

USER: "Cloud bills keep growing"

AGENT: "Perfect! Which cloud?"
        [AWS] [Google] [Azure] [Multiple]

USER: "AWS"

AGENT: "Got it! Your optimization target is:
        'Help me optimize my AWS cloud costs'
        
        Let me get the right data for this..."
        [Triggers Data Helper with context]
```

### Pattern B: Performance Discovery
```
AGENT: "Let's find what's slow! When do you notice it?"
        
        🌅 Morning startup
        🏃 During user actions
        📈 Under heavy load
        🌙 Batch jobs at night
        🎲 Randomly

USER: "During user actions"

AGENT: "Which action feels slowest?"
        
        🔍 Search/queries
        📝 Loading lists/tables
        💾 Saving/uploading
        🔄 Page navigation
        📊 Reports/analytics

USER: "Loading lists"

AGENT: "Database optimization needed!
        Your optimization target is:
        'Our database queries are slow when loading lists'
        
        Let me help you measure this..."
```

### Pattern C: Unknown Starting Point
```
AGENT: "No problem! Let's explore. Answer 3 quick questions:"

        "1. What's your role?"
        [Developer] [DevOps] [Manager] [Other]

        "2. Biggest worry about your system?"
        [Costs] [Downtime] [Speed] [Growth]
        
        "3. Monthly cloud/infra spend?"
        [<$1k] [$1-10k] [$10-50k] [>$50k]

USER: "DevOps, Costs, $10-50k"

AGENT: "Based on your profile, I suggest starting with:
        
        🎯 Container/K8s optimization (usually 30% savings)
        🎯 Database right-sizing (common overprovisioning)
        🎯 Storage cleanup (forgotten snapshots/logs)
        
        Which interests you most?"
```

---

## 4. Imagination Techniques

### A. The "Bill Surprise" Technique
```
AGENT: "Imagine opening your cloud bill. 
        What line item would make you go 'WHAT?!'
        
        Even if you don't know, guess:"
        
        💾 Storage: "Why do we have 50TB?"
        🖥️ Compute: "Why so many servers?"
        🌐 Network: "Why huge data transfer?"
        📊 Database: "Why is RDS so expensive?"
        🔧 Random services: "What even is this?"
```

### B. The "User Complaint" Technique
```
AGENT: "If users could complain directly to you,
        what would they say?"
        
        😤 "Why is login so slow?"
        😡 "Search never works!"
        🙄 "Always getting errors!"
        😴 "Reports take forever!"
        💔 "App crashes daily!"
```

### C. The "Crystal Ball" Technique
```
AGENT: "Looking 6 months ahead, what breaks first?"
        
        💥 Database can't handle load
        💳 Budget runs out
        👥 Can't onboard new customers
        🐌 Everything gets slower
        ☁️ Cloud costs double
```

---

## 5. Implementation Strategy

### Phase 1: Pattern Recognition
- Detect vague/uncertain user inputs
- Trigger Imagination Agent for discovery
- Use minimal questions (max 3-4)

### Phase 2: Progressive Narrowing
```python
discovery_funnel = {
    "level_1": ["cost", "performance", "reliability", "scale"],
    "level_2": {
        "cost": ["cloud", "database", "network", "waste"],
        "performance": ["api", "database", "frontend", "processing"]
    },
    "level_3": {
        "cloud": ["AWS", "GCP", "Azure"],
        "database": ["queries", "connections", "storage"]
    }
}
```

### Phase 3: Handoff to Data Helper
Once specific target identified:
1. Generate clear optimization prompt
2. Pass context to Data Helper
3. Include discovered constraints (access level, technical knowledge)

---

## 6. Success Metrics

### User Journey Metrics
- Time from vague concern → specific target: <2 minutes
- Questions asked: Maximum 4
- Abandonment rate: <10%
- Successful handoff to Data Helper: >90%

### Discovery Quality
- User confirms discovered target matches need: >85%
- Optimization yields measurable improvement: >70%
- User returns for more optimizations: >60%

---

## 7. Example Implementation

```python
class ImaginationAgent:
    def __init__(self):
        self.discovery_templates = {
            "cost": CostDiscoveryFlow(),
            "performance": PerformanceDiscoveryFlow(),
            "reliability": ReliabilityDiscoveryFlow(),
            "unknown": GeneralDiscoveryFlow()
        }
    
    async def discover_optimization_target(self, vague_input: str) -> str:
        # Step 1: Categorize concern
        category = await self.categorize_concern(vague_input)
        
        # Step 2: Run appropriate discovery flow
        flow = self.discovery_templates[category]
        target = await flow.guide_user_to_specific_target()
        
        # Step 3: Generate optimization prompt
        optimization_prompt = self.craft_optimization_prompt(target)
        
        # Step 4: Handoff with context
        context = {
            "discovered_target": target,
            "user_technical_level": flow.assessed_level,
            "access_constraints": flow.discovered_constraints,
            "priority": flow.urgency_level
        }
        
        return optimization_prompt, context
    
    def categorize_concern(self, input_text: str) -> str:
        keywords = {
            "cost": ["expensive", "cost", "bill", "paying", "budget"],
            "performance": ["slow", "lag", "wait", "loading", "timeout"],
            "reliability": ["crash", "error", "down", "broken", "fail"],
            "unknown": ["help", "improve", "optimize", "better", "issue"]
        }
        # ... categorization logic
```

---

## 8. Key Innovation: Psychological Techniques

### The "Pain Point Pyramid"
Start broad, narrow quickly:
```
Level 1: "What keeps you up at night?"
Level 2: "When did you last curse at your computer?"
Level 3: "What would you fix with a magic wand?"
Result: Specific optimization target
```

### The "Comparison Method"
```
"Which is worse for you?
A) Paying too much
B) System too slow

[User picks A]

Which costs more pain?
A) Cloud infrastructure  
B) Developer time

[User picks A]

What's your biggest cloud expense?
A) Compute (EC2, VMs)
B) Storage (S3, disks)
C) Database (RDS, BigQuery)
D) Not sure

[Result: Specific target]
```

---

## Summary

The Imagination Agent transforms uncertainty into action by:
1. **Recognizing confusion** in user requests
2. **Guiding discovery** through smart questions
3. **Limiting cognitive load** (max 4 choices)
4. **Creating specific targets** from vague concerns
5. **Seamlessly transitioning** to Data Helper with context

This ensures users who don't know what to optimize can still get value from the optimization platform.