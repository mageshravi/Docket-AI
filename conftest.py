import pytest
from django.test import Client
from pytest_factoryboy import register
from rest_framework.test import APIClient

from core.models import User
from poc.models import Case, Litigant, LitigantRole
from poc.tests.factories import (
    CaseFactory,
    CaseLitigantFactory,
    ChatMessageFactory,
    ChatThreadFactory,
    LitigantFactory,
    UploadedFileFactory,
)

register(LitigantFactory)
register(CaseFactory)
register(CaseLitigantFactory)
register(ChatThreadFactory)
register(ChatMessageFactory)
register(UploadedFileFactory)


@pytest.fixture()
def client():
    return Client()


@pytest.fixture()
def api_client():
    return APIClient()


@pytest.fixture()
def users(db) -> dict[str, User]:
    user1 = User.objects.create_user(
        username="user1", email="user1@example.com", password="password123"
    )
    user2 = User.objects.create_user(
        username="user2", email="user2@example.com", password="password123"
    )
    return {"user1": user1, "user2": user2}


@pytest.fixture()
def litigant_roles(db) -> dict[str, LitigantRole]:
    roles = LitigantRole.objects.all()
    result = {}
    for role in roles:
        result[role.handle] = role

    return result


@pytest.fixture()
def litigants(db, litigant_factory) -> dict[str, Litigant]:
    mahadevan = litigant_factory.create(
        name="S Mahadevan",
        bio="Director, Roma Housing Ltd.",
        email="mahadevan.shanmugam@romareal.com",
        phone="+91-7010570105",
        address="768, D Block, Gasa Crande Pollos,\nNolambur, Chennai - 600095.",
        notes="Lorem ipsum dolor sit amet, consectetur adipiscing elit. Duis volutpat enim vitae mi maximus feugiat.",
    )
    gopalan = litigant_factory.create(
        name="K Gopalan",
        bio="Director, Vekkey Enterprises",
        email="gopalan.k@vekkey.com",
        phone="+91-6012355667",
        address="Vekkey Enterprises, 99, Rama street, Porur, Chennai - 600116.",
        notes="Lorem ipsum dolor sit amet, consectetur adipiscing elit. Duis volutpat enim vitae mi maximus feugiat.",
    )
    return {"mahadevan": mahadevan, "gopalan": gopalan}


@pytest.fixture()
def cases(
    db, case_factory, case_litigant_factory, litigant_roles, litigants
) -> dict[str, Case]:
    case1 = case_factory.create(
        title="Roma Housing Ltd. vs Vekkey Enterprises",
        description="A civil suit for recovery of dues.",
    )

    case_litigant_factory.create(
        case=case1,
        litigant=litigants["mahadevan"],
        role=litigant_roles["PLAINTIFF"],
        is_our_client=True,
    )

    case_litigant_factory.create(
        case=case1,
        litigant=litigants["gopalan"],
        role=litigant_roles["DEFENDANT"],
    )

    return {"mahadevan_vs_gopalan": case1}


@pytest.fixture()
def uploaded_files(db, uploaded_file_factory, cases) -> list:
    extensions = ["pdf", "docx", "xlsx", "pptx", "txt"]
    files = []
    for i in range(5):
        odd_even = "odd" if i % 2 == 0 else "even"
        filename = f"exhibit_{i + 1}_{odd_even}.{extensions[i]}"
        uploaded_file = uploaded_file_factory.create(
            filename=filename,
            file=f"/path/to/{filename}",
            case=cases["mahadevan_vs_gopalan"],
            exhibit_code=f"P-{i + 1}",
        )
        files.append(uploaded_file)

    return files
