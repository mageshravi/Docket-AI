from langchain_core.tools import BaseTool

from poc.models import Case, ChatThread

__all__ = [
    "CaseDetails",
]


def get_case_details(case: Case) -> str:
    case_litigants = case.case_litigants.all()
    litigant_details = ""
    for litigant in case_litigants:
        our_client = "Yes" if litigant.is_our_client else "No"
        litigant_details += (
            f"{litigant.role.name}\n"
            f"Name: {litigant.litigant.name}\n"
            f"Bio: {litigant.litigant.bio}\n"
            f"Phone: {litigant.litigant.phone}\n"
            f"Email: {litigant.litigant.email}\n"
            f"Our Client: {our_client}\n"
            "---\n"
        )

    details = (
        f"Case Number: {case.case_number}\n"
        f"Title: {case.title}\n"
        f"Litigants:\n{litigant_details if litigant_details else 'No litigants found.'}\n"
        # f"Dispute/Allegations:\n{case.description}\n\n"
    )

    return details


class CaseDetails(BaseTool):
    name: str = "case_details"
    description: str = "Get case details by chat thread ID"

    def _run(self, thread_id: int) -> str:
        try:
            thread = ChatThread.objects.get(id=thread_id)
        except ChatThread.DoesNotExist:
            return "Chat thread not found."

        if not thread.case:
            return "No case associated with this chat thread."

        return get_case_details(thread.case)
