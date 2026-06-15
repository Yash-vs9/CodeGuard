# AI Agent System

![CODEGUARD Banner](codeguard_banner.svg)
This repository houses a powerful, dual-mode multi-agent system built with **LangGraph** and **Langchain Google GenAI**. The system is designed to autonomously analyze, review, and write code by orchestrating specialized AI agents.

Both modes utilize Google's Gemini LLMs and structured state-graphs to handle planning, context gathering, and execution.

---

## High-Level Architecture

The system features a single CLI entry point (`cli.py`) that acts as a router, dropping the user into one of two specialized state graphs based on the mode provided:

1.  **Scan Mode (`--mode scan`)**: Analyzes an existing repository for security vulnerabilities, logic errors, and code quality issues.
2.  **Code Mode (`--mode code`)**: An autonomous coding agent that plans out a feature or fix, breaks it into tasks, and iteratively writes code until a reviewer agent approves.

```mermaid
graph TD
    %% Nodes
    CLI[/"Dragon CLI — cli.py"/]
    UserInput(("User Input"))
    
    ChatAgent["Chat Agent — Memory & Query Refinement"]
    
    ModeSwitch{"Mode Selection"}

    subgraph ScanGraph ["🔍 Scan Mode (graph.py)"]
        Scanner["Project Scanner Agent"]
        ScanPlanner["Planner Agent — Strategy"]
        
        Security["Security Agent"]
        Logic["Logic Agent"]
        Quality["Code Quality Agent"]
        
        Report["Report Aggregator"]
    end

    subgraph CodeGraph ["💻 Code Mode (code.py)"]
        CodePlanner["Code Planner Agent — Task Breakdown"]
        Coder["Coding Agent — Workspace Execution"]
        Reviewer["Reviewer Agent — Feedback Loop"]
    end

    FinalOutput[/"Final Result to User"/]

    %% Data Flow
    UserInput --> CLI
    CLI --> ChatAgent
    ChatAgent -->|Extracts Goal| ModeSwitch
    
    ModeSwitch -->|--mode scan| Scanner
    ModeSwitch -->|--mode code| CodePlanner

    %% Scan Flow
    Scanner -->|Project Map| ScanPlanner
    ScanPlanner -->|Review Plan| Security
    ScanPlanner -->|Review Plan| Logic
    ScanPlanner -->|Review Plan| Quality
    
    Security --> Report
    Logic --> Report
    Quality --> Report
    
    Report --> FinalOutput

    %% Code Flow
    CodePlanner --> Coder
    Coder <--> Reviewer
    Reviewer --> FinalOutput

    %% Styling
    classDef io fill:#ccfbf1,stroke:#0f766e,stroke-width:1.5px,color:#134e4a;
    classDef core fill:#e0e7ff,stroke:#4338ca,stroke-width:1.5px,color:#312e81;
    classDef code_agent fill:#dbeafe,stroke:#1d4ed8,stroke-width:1.5px,color:#1e3a8a;
    classDef scan_agent fill:#dcfce7,stroke:#15803d,stroke-width:1.5px,color:#14532d;
    classDef data fill:#ffedd5,stroke:#c2410c,stroke-width:1.5px,color:#7c2d12;

    class UserInput,CLI,FinalOutput io;
    class ChatAgent,ModeSwitch core;
    class CodePlanner,Coder,Reviewer code_agent;
    class Scanner,ScanPlanner,Security,Logic,Quality,Report scan_agent;
```

---

## Detailed Flow: Scan Mode (`graph.py`)

In **Scan Mode**, the agent system acts as a multi-threaded code reviewer. The state graph passes an `AgentState` containing the project map, review plan, and individual reports between nodes.

### How the Flow Works:

1.  **Input & Chat Memory**: The CLI collects the user query and project path. A `Chat Agent` refines the user's raw input into a concise, actionable goal (and respects exclusions, e.g., "Skip security checks").
2.  **Context Gathering**: The `Project Scanner` uses terminal tools to list files, read directories, and build a high-level `project_map` of the codebase.
3.  **Planning & Routing**: The `Planner Agent` consumes the map and query to generate a review `plan`. It also outputs a structured dictionary (`agents_required`) dictating which specific review agents should run.
4.  **Parallel Execution**: The state graph uses conditional routing to trigger the `Security`, `Logic`, and `Code Quality` agents. These agents run concurrently, each appending their findings to the state.
5.  **Aggregation**: The `Report Node` formats the individual reports into a single, comprehensive markdown output.

```mermaid
graph TD
    %% Nodes
    Input[/"Input: user_query, project_path"/]
    Chat["Chat Agent\nRefines Query"]
    Scanner["Scanner Agent\nGenerates project_map"]
    Planner["Planner Agent\nGenerates plan & agents_required dict"]
    
    Router{"Conditional Router\nChecks agents_required"}
    
    Security["Security Agent\nGenerates security_report"]
    Logic["Logic Agent\nGenerates logic_report"]
    Quality["Code Quality Agent\nGenerates quality_report"]
    
    Report["Report Node\nCompiles final_report"]
    End((END))

    %% Connections
    Input --> Chat
    Chat --> Scanner
    Scanner --> Planner
    Planner --> Router
    
    Router -->|if security_agent: true| Security
    Router -->|if logic_agent: true| Logic
    Router -->|if code_quality_agent: true| Quality
    
    Security --> Report
    Logic --> Report
    Quality --> Report
    Router -->|if no agents required| Report
    
    Report --> End

    %% Styling
    classDef io fill:#e0e7ff,stroke:#4f46e5,stroke-width:2px,color:#1e1b4b;
    classDef process fill:#dcfce7,stroke:#16a34a,stroke-width:2px,color:#14532d;
    classDef router fill:#ffedd5,stroke:#ea580c,stroke-width:2px,color:#7c2d12;
    classDef report fill:#fae8ff,stroke:#c026d3,stroke-width:2px,color:#4a044e;

    class Input,End io;
    class Chat,Scanner,Planner,Security,Logic,Quality process;
    class Router router;
    class Report report;
```

---

## Detailed Flow: Code Mode (`code.py`)

In **Code Mode**, the system acts as an autonomous pair programmer. It features an iterative feedback loop where code is written, reviewed, and rewritten until it passes validation.

### How the Flow Works:

1.  **Task Breakdown**: The `Code Planner Agent` looks at the user query and generates a step-by-step implementation plan. This is converted into an ordered queue of `tasks` (e.g., [1. Setup Node project, 2. Write UI, 3. Add API integration]).
2.  **Execution (Coder)**: The `Coding Agent` is given the current task, the overarching plan, and access to an array of tools (file reading, writing, terminal commands). It executes the task in the actual file system.
3.  **Validation (Reviewer)**: Once the coder finishes, the `Reviewer Agent` analyzes the changes made. It checks if the specific task requirements were met without breaking existing functionality.
4.  **Feedback Loop**:
    *   If the reviewer **fails** the code, it populates `feedback_on_current_task_ifany`. The graph routes back to the Coder, which tries again with the feedback in mind.
    *   If the reviewer **passes** the code, `current_task` is incremented.
5.  **Completion**: This loop repeats until `current_task` exceeds the number of items in the queue, at which point the graph terminates.

```mermaid
graph TD
    %% Nodes
    Input[/"Input: user_query, working_dir"/]
    Planner["Code Planner Agent\nGenerates plan & tasks queue"]
    
    CheckTasks{"Are all tasks\ncompleted?"}
    
    Coder["Coding Agent\nExecutes task using tools\n(reads, writes, terminal)"]
    Reviewer["Reviewer Agent\nValidates task completion"]
    
    FeedbackCheck{"Did Review\nPass?"}
    
    UpdateFeedback["State Update:\nProvide Feedback"]
    NextTask["State Update:\nIncrement current_task"]
    
    End((END))

    %% Flow
    Input --> Planner
    Planner -->|Initializes plan, tasks,\ncurrent_task=0| CheckTasks
    
    CheckTasks -->|Yes| End
    CheckTasks -->|No| Coder
    
    Coder -->|Reads plan, task,\nfeedback, tools| Reviewer
    
    Reviewer --> FeedbackCheck
    
    FeedbackCheck -->|No| UpdateFeedback
    UpdateFeedback -->|Passes feedback back to coder| Coder
    
    FeedbackCheck -->|Yes| NextTask
    NextTask --> CheckTasks

    %% Styling
    classDef io fill:#e0e7ff,stroke:#4f46e5,stroke-width:2px,color:#1e1b4b;
    classDef agent fill:#dbeafe,stroke:#2563eb,stroke-width:2px,color:#1e3a8a;
    classDef condition fill:#fef08a,stroke:#ca8a04,stroke-width:2px,color:#713f12;
    classDef state_update fill:#d1fae5,stroke:#059669,stroke-width:2px,color:#064e3b;

    class Input,End io;
    class Planner,Coder,Reviewer agent;
    class CheckTasks,FeedbackCheck condition;
    class UpdateFeedback,NextTask state_update;
```

---

## Usage

Execute the vulnerability scanner or the coding agent using the Dragon CLI. The CLI features rich progress spinners and interactive prompts.

```bash
# Scan Mode (Vulnerability & Quality analysis)
python cli.py --mode scan -q "Find bugs" -p /path/to/project

# Code Mode (Autonomous coding & building)
python cli.py --mode code -q "Build a tic tac toe app" -p /path/to/project

# Interactive Mode (Prompts for inputs)
python cli.py --mode code
```
*(Make sure to specify a valid absolute or relative path to your project).*

---

## Environment Variables

Create a `.env` file in the root directory with the following variables:

```env
GOOGLE_API_KEY_1=
GOOGLE_API_KEY=

GOOGLE_API_KEY_2=
GOOGLE_API_KEY_3=
SERPAPI_KEY=
OPENROUTER_API_KEY=
GROQ_API_KEY=
AGENT_WORKING_DIR=
```

---

## License
This project is open-source. Feel free to use and modify the agents for your personal workflows.
