from langchain_core.prompts import ChatPromptTemplate

def get_agent_prompt(system_prompt: str) -> ChatPromptTemplate:
    return ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            ("placeholder", "{messages}"),
        ]
    )

WRITE_TODOS_DESCRIPTION = "A tool to write todos."
EDIT_DESCRIPTION = "A tool to edit files."
TOOL_DESCRIPTION = "A tool to read files."
