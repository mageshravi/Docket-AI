from django.db.models import Q
from django.utils.timezone import datetime
from langchain.schema import Document
from langchain_core.tools import BaseTool
from pgvector.django.functions import CosineDistance

from poc.models import ParsedEmail, ParsedEmailEmbedding
from poc.utils import create_vector_embedding

__all__ = [
    "SearchByDate",
    "SearchBySender",
    "SearchByRecipient",
    "SearchBySubject",
    "SemanticEmailSearch",
]


def _get_results(emails: list[ParsedEmail]) -> list:
    results = []
    for email in emails:
        content = email.cleaned_body
        source = (
            "Type: Email",
            f"Subject: {email.subject}\n"
            f"From: {email.sender}\n"
            f"To: {email.to_recipients}\n"
            f"CC: {email.cc_recipients}\n"
            f"Date: {email.sent_on}\n",
        )
        results.append(
            {
                "content": content,
                "source": source,
            }
        )

    return results


class SearchByDate(BaseTool):
    name: str = "search_email_by_date"
    description: str = (
        "Search emails sent within a date range."
        " Date format: YYYY-MM-DD."
        " Returns the email content and metadata about the source."
    )

    def _run(self, from_date: str, to_date: str) -> list[Document]:
        try:
            _from_date = datetime.strptime(from_date, "%Y-%m-%d").date()
            _to_date = datetime.strptime(to_date, "%Y-%m-%d").date()
        except ValueError:
            return []

        emails = ParsedEmail.objects.filter(
            sent_on__date__range=(_from_date, _to_date)
        ).order_by("-sent_on")
        return _get_results(emails)


class SearchBySender(BaseTool):
    name: str = "search_email_by_sender"
    description: str = (
        "Search emails by sender's name or email address."
        " Returns the email content and metadata about the source."
    )

    def _run(self, sender: str) -> list[Document]:
        emails = ParsedEmail.objects.filter(sender__icontains=sender).order_by(
            "-sent_on"
        )
        return _get_results(emails)


class SearchByRecipient(BaseTool):
    name: str = "search_email_by_recipient"
    description: str = (
        "Search emails by recipient's name or email address."
        " Returns the email content and metadata about the source."
    )

    def _run(self, recipient: str) -> list[Document]:
        emails = ParsedEmail.objects.filter(
            Q(to_recipients__icontains=recipient)
            | Q(cc_recipients__icontains=recipient)
        ).order_by("-sent_on")
        return _get_results(emails)


class SearchBySubject(BaseTool):
    name: str = "search_email_by_subject"
    description: str = (
        "Search emails by subject keywords."
        " Returns the email content and metadata about the source."
    )

    def _run(self, subject_keywords: str) -> list[Document]:
        emails = ParsedEmail.objects.filter(
            subject__icontains=subject_keywords
        ).order_by("-sent_on")
        return _get_results(emails)


class SemanticEmailSearch(BaseTool):
    name: str = "semantic_email_search"
    description: str = (
        "Search emails using semantic search."
        " Returns a list of relevant emails including metadata about the source."
    )

    def _run(self, query: str, top_k: int = 5) -> list[Document]:
        query_vector = create_vector_embedding([query])[0]["embedding"]
        email_chunks = ParsedEmailEmbedding.objects.annotate(
            distance=CosineDistance("embedding", query_vector)
        ).order_by("distance")[:top_k]

        # adding to a set to remove duplicates
        email_set = {chunk.parsed_email for chunk in email_chunks}

        emails = list(email_set)
        return _get_results(emails)
