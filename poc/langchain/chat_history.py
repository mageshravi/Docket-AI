from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import AIMessage, HumanMessage

from poc.models import ChatMessage, ChatThread


class DjangoChatMessageHistory(BaseChatMessageHistory):
    def __init__(self, thread_id: int, max_turns: int = 10):
        self.thread = ChatThread.objects.get(pk=thread_id)
        self.max_turns = max_turns

    @property
    def messages(self):
        msgs = (
            self.thread.messages.order_by("-created_at")[: self.max_turns * 2]
            .select_related("thread")
            .all()
        )

        msgs = list(msgs)[::-1]  # reverse to chronological order

        formatted = []
        for msg in msgs:
            if msg.role == ChatMessage.Role.USER:
                formatted.append(HumanMessage(content=msg.content))
            else:
                formatted.append(AIMessage(content=msg.content))

        return formatted

    def persist_user_message(self, message: str) -> ChatMessage:
        """
        Persist a user message and return the created ChatMessage instance.
        Adding this extra method to NOT change the return type of add_user_message.
        """
        return ChatMessage.objects.create(
            thread=self.thread, role=ChatMessage.Role.USER, content=message
        )

    def persist_ai_message(self, message: str) -> ChatMessage:
        """
        Persist an AI message and return the created ChatMessage instance.
        Adding this extra method to NOT change the return type of add_ai_message.
        """
        return ChatMessage.objects.create(
            thread=self.thread, role=ChatMessage.Role.AI, content=message
        )

    def add_message(self, message) -> None:
        # if isinstance(message, HumanMessage):
        #     self.persist_user_message(message.content)
        # elif isinstance(message, AIMessage):
        #     self.persist_ai_message(message.content)
        # ? Why no-op?
        # To prevent double saving in database.
        # See send_message in poc/langchain/chat_agent.py for more details.
        pass

    def clear(self):
        self.thread.messages.all().delete()
