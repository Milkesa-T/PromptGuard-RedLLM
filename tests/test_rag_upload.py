"""
Integration Tests for RAG Document Upload, Dynamic Indexing, and Management Endpoints.

Tests:
- GET /api/rag/documents (enriched metadata with chunk breakdown)
- POST /api/rag/documents/text (direct markdown/text document creation)
- POST /api/rag/documents/upload (multipart file upload)
- GET /api/rag/documents/{doc_name}/content (content and chunk viewer)
- DELETE /api/rag/documents/{doc_name} (safe deletion and index sync)
- Security validations (extension filtering, path traversal protection, protected core docs)
"""
import io
import pytest
from fastapi.testclient import TestClient
from backend.app import app

client = TestClient(app)


def test_list_rag_documents_has_details():
    """Verify GET /api/rag/documents returns both documents list and structured details."""
    res = client.get("/api/rag/documents")
    assert res.status_code == 200
    data = res.json()
    assert "total_chunks" in data
    assert "documents" in data
    assert "details" in data
    assert isinstance(data["details"], list)
    assert data["total_chunks"] > 0
    if data["details"]:
        first = data["details"][0]
        assert "name" in first
        assert "chunk_count" in first
        assert "access_level" in first


def test_create_rag_document_from_text():
    """Verify POST /api/rag/documents/text creates, chunks, and indexes a custom document."""
    doc_title = "test_custom_vip_escalation.md"
    doc_content = (
        "# VIP Client Escalation Guidelines\n\n"
        "All tier-1 enterprise clients with active SLAs over $50,000 are entitled to "
        "priority resolution within 15 minutes.\n\n"
        "## Emergency Contacts\n"
        "Contact the dedicated VIP technical account management unit immediately."
    )

    payload = {
        "title": doc_title,
        "content": doc_content,
        "access_level": "internal",
        "save_to_disk": True
    }

    res = client.post("/api/rag/documents/text", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["filename"] == doc_title
    assert data["chunks_created"] >= 1
    assert data["saved_to_disk"] is True

    # Verify search retrieves the new document
    search_res = client.post("/api/rag/search", json={"query": "VIP enterprise clients priority resolution", "top_k": 3})
    assert search_res.status_code == 200
    search_data = search_res.json()
    matched_sources = [c.get("doc_name") or c.get("source") for c in search_data["chunks"]]
    assert doc_title in matched_sources

    # Verify reading content
    content_res = client.get(f"/api/rag/documents/{doc_title}/content")
    assert content_res.status_code == 200
    c_data = content_res.json()
    assert c_data["filename"] == doc_title
    assert "VIP Client Escalation Guidelines" in c_data["content"]
    assert c_data["chunks_count"] >= 1

    # Cleanup: Delete the created document
    del_res = client.delete(f"/api/rag/documents/{doc_title}")
    assert del_res.status_code == 200
    del_data = del_res.json()
    assert del_data["status"] == "success"
    assert del_data["filename"] == doc_title


def test_upload_rag_document_file():
    """Verify POST /api/rag/documents/upload handles multipart file uploads."""
    doc_name = "test_incident_runbook.md"
    file_bytes = b"# Incident Severity Matrix\n\nSEV-1 represents full production outage.\n"
    
    files = {
        "file": (doc_name, io.BytesIO(file_bytes), "text/markdown")
    }
    data = {
        "access_level": "confidential",
        "save_to_disk": "true"
    }

    res = client.post("/api/rag/documents/upload", files=files, data=data)
    assert res.status_code == 200
    res_data = res.json()
    assert res_data["status"] == "success"
    assert res_data["filename"] == doc_name
    assert res_data["access_level"] == "confidential"
    assert res_data["chunks_created"] >= 1

    # Cleanup
    client.delete(f"/api/rag/documents/{doc_name}")


def test_upload_invalid_extension_rejected():
    """Verify invalid file extensions like .exe, .py are rejected with 400."""
    files = {
        "file": ("malicious_payload.exe", io.BytesIO(b"MZ..."), "application/octet-stream")
    }
    res = client.post("/api/rag/documents/upload", files=files, data={"access_level": "public"})
    assert res.status_code == 400
    assert "Unsupported file extension" in res.json()["detail"]


def test_delete_protected_core_document_forbidden():
    """Verify core system policy documents cannot be deleted."""
    res = client.delete("/api/rag/documents/refund_policy.md")
    assert res.status_code == 403
    assert "Cannot delete protected core document" in res.json()["detail"]


def test_delete_nonexistent_document_returns_404():
    """Verify deleting a non-existent document returns 404."""
    res = client.delete("/api/rag/documents/non_existent_file_xyz_123.md")
    assert res.status_code == 404
