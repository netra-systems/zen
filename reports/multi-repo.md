This Mermaid diagram illustrates the architecture of the AI-Native GitOps Factory and its two primary workflows: (1) Customization and Evolution via feature requests, and (2) Automated Synchronization of core updates across the organization.

```mermaid
graph TD
    %% --- Component Definitions & Styling ---
    classDef human fill:#D1F2EB,stroke:#148F77,stroke-width:2px;
    classDef ai fill:#E8DAEF,stroke:#9B59B6,stroke-width:2px;
    classDef git fill:#D6EAF8,stroke:#3498DB,stroke-width:2px;
    classDef coregit fill:#A9CCE3,stroke:#2E86C1,stroke-width:3px;
    classDef exec fill:#FCF3CF,stroke:#F39C12,stroke-width:2px;

    %% --- Architecture Components ---

    H([Human Curator / Architect]):::human

    subgraph "AI Factory System"
        direction TB
        CP(AI Control Plane - Factory Manager):::ai
        Swarm(AI Agent Swarm - 100x Workforce):::ai
        CP -- Orchestrates --> Swarm
    end

    subgraph "Execution Layer"
        Exec(Ephemeral Environments - Efficient Compute):::exec
    end

    subgraph "Git Ecosystem (e.g., GitHub/GitLab)"
        direction TB
        Core(Core Root Module - Optimized Foundation):::coregit

        subgraph "Application Repositories (The Delta)"
            Repo1(App Repo 1):::git
            Repo2(App Repo 2):::git
            RepoN(App Repo N...):::git
        end
        %% Dependencies
        Repo1 -- Depends on v2.1 --> Core
        Repo2 -- Depends on v2.1 --> Core
        RepoN -- Depends on v2.1 --> Core
    end

    %% --- Workflow A: Customization & Evolution (Solid Blue Lines) ---
    H -- "A1. Creates Issue (Intent)" --> Repo1
    CP -- "A2. Monitors & Detects Issue" --> Repo1
    CP -- "A3. Dispatches Agents" --> Swarm
    Swarm -- "A4. Executes & Verifies" --> Exec

    %% Execution Details
    Exec -- "Clones Repo & Runs Tests" --> Repo1
    Exec -- "Uses Core Toolchain & Constraints" --> Core

    Swarm -- "A5. Submits PR (Solution)" --> Repo1
    H -- "A6. Reviews & Merges PR" --> Repo1

    %% --- Workflow B: Automated Synchronization & Refactoring (Dotted Red Lines) ---
    Core -. "B1. Core Updated (v2.2)" .-> CP
    CP -. "B2. Initiates Global Migration" .-> Swarm
    Swarm -. "B3. Parallel Refactoring & Conflict Resolution" .-> Exec
    Swarm -. "B4. Automated PRs (Update to v2.2)" .-> Repo1
    Swarm -. "B4. Automated PRs (Update to v2.2)" .-> Repo2
    Swarm -. "B4. Automated PRs (Update to v2.2)" .-> RepoN

    %% --- Link Styling ---
    %% Workflow A Styling (Blue) - Solid lines for customization workflow
    linkStyle 4 stroke:#3498DB,stroke-width:2px;
    linkStyle 5 stroke:#3498DB,stroke-width:2px;
    linkStyle 6 stroke:#3498DB,stroke-width:2px;
    linkStyle 7 stroke:#3498DB,stroke-width:2px;
    linkStyle 8 stroke:#3498DB,stroke-width:2px;
    linkStyle 9 stroke:#3498DB,stroke-width:2px;

    %% Workflow B Styling (Red Dashed) - Dotted lines for sync workflow
    linkStyle 10 stroke-width:2px,stroke:#E74C3C,stroke-dasharray: 5 5;
    linkStyle 11 stroke-width:2px,stroke:#E74C3C,stroke-dasharray: 5 5;
    linkStyle 12 stroke-width:2px,stroke:#E74C3C,stroke-dasharray: 5 5;
    linkStyle 13 stroke-width:2px,stroke:#E74C3C,stroke-dasharray: 5 5;
    linkStyle 14 stroke-width:2px,stroke:#E74C3C,stroke-dasharray: 5 5;
    linkStyle 15 stroke-width:2px,stroke:#E74C3C,stroke-dasharray: 5 5;
```

### Diagram Explanation

#### Components

  * **Human Curator / Architect:** The human user who defines intent (via Issues) and oversees the results (via PRs).
  * **Git Ecosystem:** The source of truth.
      * **Core Root Module:** The optimized, opinionated foundation defining the architecture, toolchain, and constraints.
      * **Application Repositories:** Individual projects that depend on the Core and contain only the customized business logic (the "delta").
  * **AI Factory System:** The intelligence core. The **AI Control Plane** acts as the Factory Manager, monitoring the Git ecosystem and orchestrating the **AI Agent Swarm** (the 100x compute workforce).
  * **Execution Layer:** The lightweight, **Ephemeral Environments** where agents clone code, execute tasks, and verify solutions at scale.

#### Workflows

**Workflow A: Customization & Evolution (Solid Blue Arrows)**

This follows the standard development cycle for a specific feature or change.

1.  A Human creates a GitHub Issue in an App Repo (e.g., a feature request).
2.  The AI Control Plane detects the issue.
3.  It dispatches the AI Swarm.
4.  The agents execute the task in the Ephemeral Environments, utilizing the Core's toolchain to ensure compliance and efficiency.
5.  The optimal solution is submitted as a Pull Request.
6.  The Human reviews and merges the AI-generated code.

**Workflow B: Automated Synchronization & Refactoring (Dotted Red Arrows)**

This is the high-value automation capability that eliminates framework-level technical debt.

1.  The Core Root Module is updated (e.g., a security patch or architectural improvement, moving from v2.1 to v2.2).
2.  The AI Control Plane detects the change and initiates a global migration.
3.  The Swarm mobilizes in parallel across *all* dependent repositories, automatically refactoring customizations and resolving conflicts.
4.  Automated PRs are opened across the organization, bringing the entire ecosystem up to date.