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

    def add_user_message(self, message: str) -> None:
        ChatMessage.objects.create(
            thread=self.thread, role=ChatMessage.Role.USER, content=message
        )

    def add_ai_message(self, message: str) -> None:
        ChatMessage.objects.create(
            thread=self.thread, role=ChatMessage.Role.AI, content=message
        )

    def add_message(self, message):
        role = (
            ChatMessage.Role.USER
            if isinstance(message, HumanMessage)
            else ChatMessage.Role.AI
        )
        ChatMessage.objects.create(
            thread=self.thread,
            role=role,
            content=message.content,
        )

    def clear(self):
        self.thread.messages.all().delete()
