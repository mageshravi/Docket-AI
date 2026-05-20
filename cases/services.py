import logging

from cases.models import Case, CaseLitigant
from litigants.models import LitigantRole

logger = logging.getLogger(__name__)


def get_case_details(case: Case, minimal: bool = False) -> str:
    """Retrieves the case details to be used for event extraction.

    Args:
        case (Case): The case for which to retrieve details.
        minimal (bool): Whether to retrieve minimal case details.

    Returns:
        str: The case details to be used for event extraction.
    """
    case_details = f"Case Title: {case.title}\n"

    if case.case_number:
        case_details += f"Case Number: {case.case_number}\n"

    if not minimal:
        case_details += f"Case Description: {case.description}\n"

    return case_details


def get_litigants_info(case: Case) -> str:
    """Retrieves the litigants information for the case.

    Args:
        case (Case): The case for which to retrieve litigants information.
    Returns:
        str: The litigants information for the case.
    """
    litigant_info = ""
    litigant_roles = LitigantRole.objects.all()
    for role in litigant_roles:
        case_litigants = CaseLitigant.objects.filter(case=case, role=role)
        if case_litigants.exists():
            litigant_info += f"{role.name.upper()}S:\n"
            for case_litigant in case_litigants:
                if case_litigant.is_our_client:
                    litigant_info += "(Our Client)\n"

                litigant_info += (
                    f"Name: {case_litigant.litigant.name}\n"
                    f"Email: {case_litigant.litigant.email}\n"
                    f"Phone: {case_litigant.litigant.phone}\n"
                    "---\n"
                )

    return litigant_info
