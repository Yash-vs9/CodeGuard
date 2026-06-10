# AI Agent System 🤖

This repository houses two powerful AI-driven multi-agent systems built with **LangGraph** and **Langchain Google GenAI**:

1. **Vulnerability & Code Analysis Agent System** (`main.py`)
2. **DSA Note-Making Reflection Agent** (`prac.py`)

Both systems utilize Google's Gemini LLMs to autonomously orchestrate complex workflows involving planning, interviewing, analyzing, and reporting.

---

## 1. Vulnerability & Code Analysis Agent System

A multi-agent software analysis tool that autonomously scans a local repository, understands its architecture, plans a thorough code review, and produces a final comprehensive report on security, logic, and code quality.

### 🏛️ Architecture & Flow

The system employs a state graph where different specialized AI agents take turns analyzing the project based on the user's query.

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
        Tasks[("Task List Queue")]
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
    
    Security -->|Findings| Report
    Logic -->|Findings| Report
    Quality -->|Findings| Report
    
    Report --> FinalOutput

    %% Code Flow
    CodePlanner -->|Tasks & Plan| Tasks
    Tasks -->|Next Task| Coder
    Coder -->|Implementation| Reviewer
    Reviewer -->|Failed — Feedback| Coder
    Reviewer -->|Passed| Tasks
    Tasks -->|All complete| FinalOutput

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
    class Tasks data;
```

### 🧩 Agents Involved

- **Project Scanner Agent**: Recursively explores the given project path using terminal and file-listing tools. It identifies languages, frameworks, entry points, architecture, and categorizes review targets.
- **Planner Agent**: Consumes the Project Map and the user's initial query to formulate a targeted review plan.
- **Security Agent**: Focuses strictly on identifying vulnerabilities (e.g., Auth issues, API security, injections) without getting distracted by code quality.
- **Logic Agent**: Analyzes business services and workflows for logical bugs and edge-case failures.
- **Code Quality Agent**: Reviews core modules for maintainability, highlighting large classes, refactoring opportunities, and structural issues.
- **Report Node**: Aggregates the findings from the Security, Logic, and Code Quality agents into a unified, easy-to-read final report.

### 🚀 Usage

Execute the vulnerability scanner or the coding agent using the Dragon CLI:

```bash
# 🔍 Scan Mode (Vulnerability & Quality analysis)
python cli.py --mode scan -q "Find bugs" -p /path/to/project

# 💻 Code Mode (Autonomous coding & building)
python cli.py --mode code -q "Build a tic tac toe app" -p /path/to/project

# Interactive mode
python cli.py --mode code
```
*(Make sure to specify your valid project path).*

---



## 📄 License
This project is open-source. Feel free to use and modify the agents for your personal workflows.
