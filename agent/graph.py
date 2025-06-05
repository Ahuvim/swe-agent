from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from typing import Annotated, List, Literal
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from pydantic import BaseModel, Field

from agent.architect.graph import swe_architect
from agent.developer.graph import swe_developer
from agent.analyst.graph import sql_analyst
from agent.analyst.state import SQLAnalysisResult

class CollaborativeState(BaseModel):
    """State for collaborative multi-agent workflows"""
    implementation_research_scratchpad: Annotated[List[BaseMessage], add_messages] = Field(default_factory=list)
    
    # Architect outputs
    research_summary: str = ""
    implementation_plan: dict = Field(default_factory=dict)
    collaboration_plan: dict = Field(default_factory=dict)
    
    # SQL Analyst outputs  
    sql_analysis_result: SQLAnalysisResult = None
    
    # Shared context between agents
    sql_queries: List[str] = Field(default_factory=list)
    database_schema: str = ""

def enhanced_architect(state: CollaborativeState):
    """Architect analyzes requirements and decides on collaboration strategy"""
    
    # Enhanced prompt for the architect to make collaboration decisions
    if state.implementation_research_scratchpad:
        original_content = state.implementation_research_scratchpad[-1].content
    else:
        original_content = "No specific requirements provided"
    
    enhanced_message = HumanMessage(content=f"""
    {original_content}
    
    COLLABORATION ANALYSIS INSTRUCTIONS:
    Please analyze this request and determine what type of work is needed:
    
    1. If SQL/database analysis is needed, mark tasks with [SQL_REQUIRED]
    2. If software development is needed, mark tasks with [CODE_REQUIRED]  
    3. If both are needed, plan how they should work together
    
    Consider these indicators:
    - SQL needed: dashboards, analytics, reports, data visualization, database queries, KPIs, metrics
    - Code needed: applications, APIs, web development, implementation, software features
    - Both needed: data-driven applications, analytics dashboards, reporting systems
    
    Create a clear implementation plan that shows:
    - What data analysis/SQL work is needed (if any)
    - What software development work is needed (if any)  
    - How they should collaborate (if both are needed)
    """)
    
    # Call architect with enhanced message
    enhanced_state = {
        "implementation_research_scratchpad": [enhanced_message]
    }
    
    result = swe_architect.invoke(enhanced_state)
    
    # Analyze the architect's plan to determine collaboration strategy
    plan_text = str(result.get('implementation_plan', ''))
    research_text = str(result.get('research_summary', ''))
    
    needs_sql = '[SQL_REQUIRED]' in plan_text or any(
        keyword in (plan_text + research_text).lower() 
        for keyword in ['sql', 'query', 'database', 'data analysis', 'analytics', 'dashboard', 'report']
    )
    
    needs_code = '[CODE_REQUIRED]' in plan_text or any(
        keyword in (plan_text + research_text).lower()
        for keyword in ['implement', 'develop', 'code', 'application', 'api', 'web', 'software']
    )
    
    # Determine collaboration strategy
    if needs_sql and needs_code:
        collaboration_plan = {
            "strategy": "collaborative",
            "steps": [
                "1. SQL Analyst: Analyze data requirements and create optimized queries",
                "2. Pass SQL results to Developer", 
                "3. Developer: Implement application using SQL queries"
            ]
        }
    elif needs_sql:
        collaboration_plan = {
            "strategy": "sql_only",
            "steps": ["1. SQL Analyst: Complete data analysis"]
        }
    elif needs_code:
        collaboration_plan = {
            "strategy": "code_only", 
            "steps": ["1. Developer: Implement software solution"]
        }
    else:
        collaboration_plan = {
            "strategy": "code_only",
            "steps": ["1. Developer: Implement basic solution"]
        }
    
    return {
        "research_summary": result.get('research_summary', ''),
        "implementation_plan": result.get('implementation_plan', {}),
        "collaboration_plan": collaboration_plan
    }

def route_after_architect(state: CollaborativeState):
    """Route based on architect's collaboration plan"""
    strategy = state.collaboration_plan.get("strategy", "code_only")
    
    if strategy == "collaborative":
        return "sql_analyst"  # Start with SQL analysis
    elif strategy == "sql_only":
        return "sql_analyst"
    else:  # code_only
        return "developer"

def sql_analyst_step(state: CollaborativeState):
    """SQL Analyst analyzes data requirements"""
    
    # Extract SQL requirements from architect's plan
    plan_text = str(state.implementation_plan)
    research_text = state.research_summary
    original_request = state.implementation_research_scratchpad[-1].content if state.implementation_research_scratchpad else ""
    
    sql_requirements = f"""
    Original Request: {original_request}
    
    Architect's Analysis: {research_text}
    
    Implementation Plan Context: {plan_text}
    
    Please create optimized SQL queries and analysis for this project.
    Focus on data extraction, performance, and how the results will be used.
    """
    
    sql_input = {
        "requirements": sql_requirements,
        "schema_information": state.database_schema or "Schema not provided - create optimal generic queries"
    }
    
    result = sql_analyst.invoke(sql_input)
    
    # Extract SQL queries for use by developer
    sql_result = result.get('sql_analysis_result')
    queries = [sql_result.query] if sql_result and sql_result.query else []
    
    return {
        "sql_analysis_result": sql_result,
        "sql_queries": queries
    }

def route_after_sql(state: CollaborativeState):
    """Route after SQL analysis"""
    strategy = state.collaboration_plan.get("strategy", "code_only")
    
    if strategy == "collaborative":
        return "developer"  # Now implement the software using SQL results
    else:
        return "end"  # SQL-only task is complete

def developer_step(state: CollaborativeState):
    """Developer implements software, optionally using SQL results"""
    
    # Prepare enhanced context for developer
    developer_messages = list(state.implementation_research_scratchpad)
    
    # Add SQL context if available
    if state.sql_analysis_result:
        sql_context = f"""
        SQL ANALYSIS RESULTS:
        
        Query: {state.sql_analysis_result.query}
        
        Explanation: {state.sql_analysis_result.explanation}
        
        Confidence: {state.sql_analysis_result.confidence}
        
        Warnings: {state.sql_analysis_result.warnings if state.sql_analysis_result.warnings else 'None'}
        
        INTEGRATION INSTRUCTIONS:
        - Use the above SQL query in your implementation
        - Consider the data structure returned by this query  
        - Implement proper error handling for database operations
        - Add data validation and transformation as needed
        """
        
        developer_messages.append(AIMessage(content=sql_context))
    
    # Add architect's plan context
    if state.implementation_plan:
        plan_context = f"""
        ARCHITECT'S IMPLEMENTATION PLAN:
        {str(state.implementation_plan)}
        
        COLLABORATION STRATEGY: {state.collaboration_plan.get('strategy', 'unknown')}
        """
        developer_messages.append(AIMessage(content=plan_context))
    
    # Call developer with enhanced context
    developer_input = {
        "implementation_research_scratchpad": developer_messages,
        "implementation_plan": state.implementation_plan
    }
    
    result = swe_developer.invoke(developer_input)
    
    return result

# Create the simplified collaborative workflow
workflow = StateGraph(CollaborativeState)

# Add the 3 core agents
workflow.add_node("architect", enhanced_architect)
workflow.add_node("sql_analyst", sql_analyst_step)
workflow.add_node("developer", developer_step)

# Simple linear flow with conditional routing
workflow.add_edge(START, "architect")

# Architect decides the collaboration strategy
workflow.add_conditional_edges(
    "architect",
    route_after_architect,
    {
        "sql_analyst": "sql_analyst",
        "developer": "developer"
    }
)

# After SQL analysis, either go to developer (collaborative) or end (SQL-only)
workflow.add_conditional_edges(
    "sql_analyst", 
    route_after_sql,
    {
        "developer": "developer",
        "end": END
    }
)

# Developer is always the final step
workflow.add_edge("developer", END)

# Compile the main agent
swe_agent = workflow.compile()

# Export aliases for backward compatibility
collaborative_agent = swe_agent
supervisor_agent = swe_agent
simple_agent = swe_agent
