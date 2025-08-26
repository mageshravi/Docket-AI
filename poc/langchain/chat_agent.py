from django.conf import settings
from langchain.agents import AgentExecutor
from langchain.agents.format_scratchpad.openai_tools import (
    format_to_openai_tool_messages,
)
from langchain.agents.output_parsers.openai_tools import OpenAIToolsAgentOutputParser
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.schema import HumanMessage, SystemMessage
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_openai import ChatOpenAI

from .chat_history import DjangoChatMessageHistory
from .tools import cases, emails, files

llm = ChatOpenAI(model="gpt-4o", api_key=settings.OPENAI_API_KEY)


def build_prompt(thread_id: str):
    base_prompt = f"""You are an intelligent legal assistant helping lawyers
recognize patterns and uncover insights from legal documents.

Case thread ID: {thread_id}

Available data sources (via tools):
- Case details - structured case metadata (title, description of the conflict, parties involved, etc.)
- Files - unstructured data from various file types (PDFs, Word documents, spreadsheets, etc.)
- Emails - unstructured communication between parties/litigants

Instructions:
- Use the dispute description only for context. Treat it as allegations and not facts.
- Always prefer calling tools to fetch factual data (case details, files, emails).
- Fetch factual data from all available data sources (files, emails) before generating answers.
- The tools may return objects with "content" and "source".
- Always use "content" for facts, and include the "source" field as a citation, e.g., [source: ...].
- For files, include the filename in the citation.
- For emails, include the subject, sender and sent date in the citation.
- If multiple sources are used, include all of them.
- Never make up case details — ask clarifying questions if unsure.
"""
    return ChatPromptTemplate.from_messages(
        [
            MessagesPlaceholder("chat_history"),
            SystemMessage(content=base_prompt),
            HumanMessage(content="{input}"),
            MessagesPlaceholder("agent_scratchpad"),  # tool call reasoning
        ]
    )


def get_tools():
    return [
        cases.CaseDetails(),
        files.SemanticFileSearch(),
        files.SearchByFilename(),
        files.SearchByFileType(),
        emails.SemanticEmailSearch(),
        emails.SearchByDate(),
        emails.SearchBySender(),
        emails.SearchByRecipient(),
        emails.SearchBySubject(),
    ]


def get_history(session_id: str):
    return DjangoChatMessageHistory(thread_id=int(session_id))


def build_agent(llm, tools, prompt):
    return (
        {
            "input": lambda x: x["input"],
            "chat_history": lambda x: x.get("chat_history", []),
            "agent_scratchpad": lambda x: format_to_openai_tool_messages(
                x["intermediate_steps"]
            ),
        }
        | prompt
        | llm.bind_tools(tools)
        | OpenAIToolsAgentOutputParser()
    )


def get_agent_with_history(thread_id: int):
    prompt = build_prompt(thread_id)
    tools = get_tools()

    agent = build_agent(llm, tools, prompt)

    executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=False,
    )

    agent_with_history = RunnableWithMessageHistory(
        executor,
        get_history,
        input_messages_key="input",
        history_messages_key="chat_history",
    )

    return agent_with_history


def send_message(thread_id: int, user_input: str) -> str:
    """
    Send a message to a specific chat thread and return the AI response.

    Args:
        thread_id (int): The ID of the chat thread.
        user_input (str): The user message to send.

    Returns:
        str: The AI response.
    """

    config = {"configurable": {"session_id": str(thread_id)}}

    # fetch the history object for this session
    history = get_history(str(thread_id))

    # add the user’s message
    history.add_user_message(user_input)

    result = get_agent_with_history(thread_id).invoke(
        {"input": user_input},
        config=config,
    )

    # add the AI response
    history.add_ai_message(result["output"])

    return result["output"]
