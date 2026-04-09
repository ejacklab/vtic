"""Comprehensive tests for the vtic markdown store.

Tests cover:
- Path utilities (ticket_file_path, resolve_path, trash_path, ensure_dirs)
- Markdown serialization/parsing (ticket_to_markdown, markdown_to_ticket)
- File operations (write_ticket, read_ticket, delete_ticket)
- Listing and scanning (list_tickets, scan_all_tickets)
"""

import pytest
import tempfile
import shutil
import time
import threading
from pathlib import Path
from datetime import datetime, timezone

from vtic.store.paths import (
    ticket_file_path,
    resolve_path,
    trash_path,
    ensure_dirs,
)
from vtic.store.markdown import (
    ticket_to_markdown,
    markdown_to_ticket,
    write_ticket,
    read_ticket,
    delete_ticket,
    list_tickets,
    scan_all_tickets,
)


# =============================================================================
# Sample Test Data
# =============================================================================

SAMPLE_TICKETS = [
    {
        "id": "C1",
        "title": "Segmentation Fault on Startup",
        "description": "App crashes immediately after launch with a segfault. This happens consistently on Linux x86_64 but not on macOS.\n\nStack trace shows the issue in the initialization code.",
        "repo": "ejacklab/api",
        "category": "crash",
        "severity": "critical",
        "status": "open",
        "assignee": "dev1",
        "fix": None,
        "tags": ["crash", "startup", "linux"],
        "references": [],
        "created": "2026-03-18T10:00:00Z",
        "updated": "2026-03-18T10:00:00Z",
    },
    {
        "id": "S1",
        "title": "SQL Injection in Login",
        "description": "User input is not properly sanitized in the login form. An attacker can inject SQL commands through the username field.",
        "repo": "ejacklab/web",
        "category": "security",
        "severity": "critical",
        "status": "in_progress",
        "assignee": "security-team",
        "fix": None,
        "tags": ["security", "sql-injection", "auth"],
        "references": ["S2"],
        "created": "2026-03-17T14:30:00Z",
        "updated": "2026-03-18T09:00:00Z",
    },
    {
        "id": "F1",
        "title": "Add Dark Mode Support",
        "description": "Users have requested a dark mode option for the UI. This should be a toggle in settings that persists across sessions.",
        "repo": "ejacklab/ui",
        "category": "feature",
        "severity": "low",
        "status": "open",
        "assignee": None,
        "fix": None,
        "tags": ["ui", "enhancement", "accessibility"],
        "references": [],
        "created": "2026-03-15T08:00:00Z",
        "updated": "2026-03-15T08:00:00Z",
    },
    {
        "id": "H1",
        "title": "Fix Memory Leak in Worker",
        "description": "Memory usage grows unbounded in the background worker process. After running for 24 hours, the process consumes over 8GB of RAM.",
        "repo": "ejacklab/api",
        "category": "hotfix",
        "severity": "high",
        "status": "fixed",
        "assignee": "dev2",
        "fix": "Added memory limit and periodic garbage collection. Released in v2.1.5.",
        "tags": ["memory", "performance", "worker"],
        "references": [],
        "created": "2026-03-10T11:00:00Z",
        "updated": "2026-03-12T16:30:00Z",
    },
    {
        "id": "G1",
        "title": "Update README Examples",
        "description": "The code examples in README.md are outdated and reference the old API. Need to update all examples to match v2.0 API.",
        "repo": "ejacklab/docs",
        "category": "general",
        "severity": "low",
        "status": "open",
        "assignee": None,
        "fix": None,
        "tags": ["documentation"],
        "references": [],
        "created": "2026-03-01T00:00:00Z",
        "updated": "2026-03-01T00:00:00Z",
    },
]


# =============================================================================
# Path Utilities Tests
# =============================================================================

class TestTicketFilePath:
    """Tests for ticket_file_path function."""
    
    def test_basic_path_generation(self):
        """Test basic path generation with all parameters."""
        result = ticket_file_path(
            Path("/tickets"),
            "ejacklab/open-dsearch",
            "security",
            "C1",
            "cors-wildcard-issue"
        )
        expected = Path("/tickets/ejacklab/open-dsearch/security/C1-cors-wildcard-issue.md")
        assert result == expected
    
    def test_path_with_nested_repo(self):
        """Test path with nested repository name."""
        result = ticket_file_path(
            Path("/data"),
            "org/sub-org/repo-name",
            "feature",
            "F42",
            "new-feature"
        )
        expected = Path("/data/org/sub-org/repo-name/feature/F42-new-feature.md")
        assert result == expected
    
    def test_path_with_special_chars_in_slug(self):
        """Test path with valid slug characters."""
        result = ticket_file_path(
            Path("/tickets"),
            "ejacklab/api",
            "crash",
            "C1",
            "fix-123-memory-leak"
        )
        assert "C1-fix-123-memory-leak.md" in str(result)


class TestResolvePath:
    """Tests for resolve_path function."""
    
    def test_find_ticket_by_id(self, tmp_path):
        """Test finding a ticket file by ID."""
        # Create a ticket file
        ticket_dir = tmp_path / "ejacklab" / "api" / "crash"
        ticket_dir.mkdir(parents=True)
        ticket_file = ticket_dir / "C1-segfault-startup.md"
        ticket_file.write_text("# test")
        
        results = resolve_path(tmp_path, "C1")
        assert len(results) == 1
        assert results[0] == ticket_file
    
    def test_find_multiple_tickets_same_id(self, tmp_path):
        """Test finding multiple tickets with same ID across repos."""
        # Create tickets in different repos
        dir1 = tmp_path / "repo1" / "crash"
        dir1.mkdir(parents=True)
        (dir1 / "C1-issue1.md").write_text("# test1")
        
        dir2 = tmp_path / "repo2" / "security"
        dir2.mkdir(parents=True)
        (dir2 / "C1-issue2.md").write_text("# test2")
        
        results = resolve_path(tmp_path, "C1")
        assert len(results) == 2
    
    def test_find_no_tickets(self, tmp_path):
        """Test finding no tickets for non-existent ID."""
        results = resolve_path(tmp_path, "X999")
        assert results == []
    
    def test_find_tickets_nonexistent_base_dir(self, tmp_path):
        """Test resolve_path when base dir doesn't exist."""
        nonexistent = tmp_path / "nonexistent"
        results = resolve_path(nonexistent, "C1")
        assert results == []


class TestTrashPath:
    """Tests for trash_path function."""
    
    def test_trash_path_generation(self):
        """Test trash path generation with timestamp."""
        result = trash_path(Path("/tickets"), "C1", "20260318220000")
        expected = Path("/tickets/.trash/C1-20260318220000.md")
        assert result == expected
    
    def test_trash_path_different_ids(self):
        """Test trash paths are unique for different IDs."""
        path1 = trash_path(Path("/tickets"), "C1", "20260318220000")
        path2 = trash_path(Path("/tickets"), "S1", "20260318220000")
        assert path1 != path2


class TestEnsureDirs:
    """Tests for ensure_dirs function."""
    
    def test_create_nested_directories(self, tmp_path):
        """Test creating deeply nested directories."""
        nested_path = tmp_path / "a" / "b" / "c" / "d" / "file.md"
        ensure_dirs(nested_path)
        assert nested_path.parent.exists()
    
    def test_existing_directories(self, tmp_path):
        """Test ensure_dirs when directories already exist."""
        nested_path = tmp_path / "existing" / "path" / "file.md"
        nested_path.parent.mkdir(parents=True, exist_ok=True)
        # Should not raise
        ensure_dirs(nested_path)
        assert nested_path.parent.exists()


# =============================================================================
# Markdown Serialization Tests
# =============================================================================

class TestTicketToMarkdown:
    """Tests for ticket_to_markdown function."""
    
    def test_full_ticket_serialization(self):
        """Test serializing a complete ticket."""
        ticket = SAMPLE_TICKETS[0]  # C1 - crash ticket
        md = ticket_to_markdown(ticket)
        
        # Check frontmatter markers
        assert md.startswith("---\n")
        assert "---\n\n## Description" in md
        
        # Check all fields are present
        assert "id: C1" in md
        assert "title: Segmentation Fault on Startup" in md
        assert "repo: ejacklab/api" in md
        assert "category: crash" in md
        assert "severity: critical" in md
        assert "status: open" in md
        assert "assignee: dev1" in md
        assert "fix: null" in md
        assert "- crash" in md
        assert "- startup" in md
        
        # Check body sections
        assert "## Description" in md
        assert "App crashes immediately" in md
        # Fix section should NOT appear when fix is None
        assert "## Fix\n" not in md
    
    def test_ticket_with_fix(self):
        """Test serializing a ticket with fix field set."""
        ticket = SAMPLE_TICKETS[3]  # H1 - has fix
        md = ticket_to_markdown(ticket)
        
        assert "fix: Added memory limit" in md
        assert "## Fix" in md
        assert "Added memory limit and periodic garbage collection" in md
    
    def test_ticket_with_null_assignee(self):
        """Test serializing ticket with null assignee."""
        ticket = SAMPLE_TICKETS[2]  # F1 - null assignee
        md = ticket_to_markdown(ticket)
        
        assert "assignee: null" in md
    
    def test_ticket_with_empty_lists(self):
        """Test serializing ticket with empty lists."""
        ticket = SAMPLE_TICKETS[4]  # G1 - minimal tags
        md = ticket_to_markdown(ticket)
        
        # Empty lists should serialize as []
        assert "references: []" in md
    
    def test_ticket_with_references(self):
        """Test serializing ticket with references."""
        ticket = SAMPLE_TICKETS[1]  # S1 - has references
        md = ticket_to_markdown(ticket)
        
        assert "- S2" in md or "S2" in md  # Reference should appear
    
    def test_multiline_description(self):
        """Test serializing ticket with multiline description."""
        ticket = {
            "id": "T1",
            "title": "Test",
            "description": "Line 1\nLine 2\n\nParagraph 2",
            "repo": "test/repo",
            "category": "general",
            "severity": "low",
            "status": "open",
            "assignee": None,
            "fix": None,
            "tags": [],
            "references": [],
            "created": "2026-03-18T00:00:00Z",
            "updated": "2026-03-18T00:00:00Z",
        }
        md = ticket_to_markdown(ticket)
        assert "Line 1\nLine 2" in md


class TestMarkdownToTicket:
    """Tests for markdown_to_ticket function."""
    
    def test_parse_full_ticket(self):
        """Test parsing a complete ticket markdown."""
        md = """---
id: C1
title: CORS Wildcard Issue
description: The API allows wildcard CORS origins in production environments.
repo: ejacklab/open-dsearch
category: security
severity: high
status: open
assignee: null
fix: null
tags:
- cors
- security
references: []
created: 2026-03-18T10:00:00Z
updated: 2026-03-18T10:00:00Z
---

## Description
The API allows wildcard CORS origins in production environments.
"""
        ticket = markdown_to_ticket(md)
        
        assert ticket["id"] == "C1"
        assert ticket["title"] == "CORS Wildcard Issue"
        assert ticket["repo"] == "ejacklab/open-dsearch"
        assert ticket["category"] == "security"
        assert ticket["severity"] == "high"
        assert ticket["status"] == "open"
        assert ticket["assignee"] is None
        assert ticket["fix"] is None
        assert ticket["tags"] == ["cors", "security"]
        assert ticket["references"] == []
        assert "wildcard CORS" in ticket["description"]
    
    def test_parse_ticket_with_fix(self):
        """Test parsing a ticket with fix section."""
        md = """---
id: H1
title: Fixed Issue
description: Something was broken.
repo: test/repo
category: hotfix
severity: high
status: fixed
assignee: dev1
fix: This is the fix description
tags: []
references: []
created: 2026-03-18T10:00:00Z
updated: 2026-03-18T12:00:00Z
---

## Description
Something was broken.

## Fix
This is the fix description
"""
        ticket = markdown_to_ticket(md)
        
        assert ticket["fix"] == "This is the fix description"
    
    def test_parse_invalid_frontmatter(self):
        """Test parsing invalid frontmatter raises error."""
        md = "This has no frontmatter"
        with pytest.raises(ValueError, match="missing YAML frontmatter"):
            markdown_to_ticket(md)
    
    def test_parse_malformed_yaml(self):
        """Test parsing malformed YAML raises error."""
        md = """---
id: [invalid yaml
title: Test
---

## Description
Test
"""
        with pytest.raises(ValueError, match="Invalid YAML"):
            markdown_to_ticket(md)
    
    def test_parse_all_types(self):
        """Test parsing all data types from frontmatter."""
        md = """---
id: T1
title: Type Test
description: Testing all types
string_val: hello
int_val: 42
float_val: 3.14
bool_val: true
null_val: null
list_val:
- one
- two
dict_val:
  key: value
repo: test/repo
category: general
severity: low
status: open
assignee: null
fix: null
tags: []
references: []
created: 2026-03-18T00:00:00Z
updated: 2026-03-18T00:00:00Z
---

## Description
Testing all types
"""
        ticket = markdown_to_ticket(md)
        
        assert isinstance(ticket["string_val"], str)
        assert isinstance(ticket["int_val"], int)
        assert isinstance(ticket["float_val"], float)
        assert isinstance(ticket["bool_val"], bool)
        assert ticket["null_val"] is None
        assert isinstance(ticket["list_val"], list)
        assert isinstance(ticket["dict_val"], dict)


class TestRoundtrip:
    """Tests for ticket_to_markdown → markdown_to_ticket roundtrip."""
    
    @pytest.mark.parametrize("ticket", SAMPLE_TICKETS)
    def test_roundtrip_preserves_all_fields(self, ticket):
        """Test that roundtrip preserves all ticket fields."""
        md = ticket_to_markdown(ticket)
        parsed = markdown_to_ticket(md)
        
        # Check all fields are preserved
        for key, value in ticket.items():
            assert key in parsed, f"Missing field: {key}"
            assert parsed[key] == value, f"Field {key}: expected {value!r}, got {parsed[key]!r}"
    
    def test_roundtrip_with_unicode(self):
        """Test roundtrip with unicode characters."""
        ticket = {
            "id": "T1",
            "title": "Unicode Test 日本語 🎉",
            "description": "Description with émojis 🚀 and 日本語",
            "repo": "test/repo",
            "category": "general",
            "severity": "low",
            "status": "open",
            "assignee": None,
            "fix": None,
            "tags": ["unicode", "テスト"],
            "references": [],
            "created": "2026-03-18T00:00:00Z",
            "updated": "2026-03-18T00:00:00Z",
        }
        md = ticket_to_markdown(ticket)
        parsed = markdown_to_ticket(md)
        
        assert parsed["title"] == ticket["title"]
        assert parsed["description"] == ticket["description"]
        assert parsed["tags"] == ticket["tags"]


# =============================================================================
# File Operations Tests
# =============================================================================

class TestWriteTicket:
    """Tests for write_ticket function."""
    
    def test_write_creates_file(self, tmp_path):
        """Test that write_ticket creates a file."""
        ticket_path = tmp_path / "C1-test-ticket.md"
        ticket = SAMPLE_TICKETS[0]
        
        write_ticket(ticket_path, ticket)
        
        assert ticket_path.exists()
    
    def test_write_creates_directories(self, tmp_path):
        """Test that write_ticket creates parent directories."""
        ticket_path = tmp_path / "nested" / "path" / "C1-test.md"
        ticket = SAMPLE_TICKETS[0]
        
        write_ticket(ticket_path, ticket)
        
        assert ticket_path.exists()
        assert ticket_path.parent.exists()
    
    def test_atomic_write_no_partial_files(self, tmp_path):
        """Test atomic write leaves no partial files on failure."""
        ticket_path = tmp_path / "test.md"
        ticket = SAMPLE_TICKETS[0]
        
        # Count files before
        files_before = set(tmp_path.glob("*"))
        
        # Successful write
        write_ticket(ticket_path, ticket)
        
        # Should only have the target file
        files_after = set(tmp_path.glob("*"))
        assert len(files_after - files_before) == 1
        assert ticket_path in files_after
        
        # No temp files left
        temp_files = list(tmp_path.glob("*.tmp"))
        assert temp_files == []
    
    def test_write_content_is_valid_markdown(self, tmp_path):
        """Test that written content is valid markdown."""
        ticket_path = tmp_path / "test.md"
        ticket = SAMPLE_TICKETS[0]
        
        write_ticket(ticket_path, ticket)
        
        content = ticket_path.read_text()
        parsed = markdown_to_ticket(content)
        
        assert parsed["id"] == ticket["id"]
        assert parsed["title"] == ticket["title"]


class TestReadTicket:
    """Tests for read_ticket function."""
    
    def test_read_existing_ticket(self, tmp_path):
        """Test reading an existing ticket."""
        ticket_path = tmp_path / "test.md"
        ticket = SAMPLE_TICKETS[0]
        
        write_ticket(ticket_path, ticket)
        parsed = read_ticket(ticket_path)
        
        assert parsed is not None
        assert parsed["id"] == ticket["id"]
    
    def test_read_nonexistent_returns_none(self, tmp_path):
        """Test reading non-existent file returns None."""
        ticket_path = tmp_path / "nonexistent.md"
        
        result = read_ticket(ticket_path)
        
        assert result is None
    
    def test_read_preserves_all_fields(self, tmp_path):
        """Test reading preserves all ticket fields."""
        ticket_path = tmp_path / "test.md"
        ticket = SAMPLE_TICKETS[1]  # S1 - security ticket with references
        
        write_ticket(ticket_path, ticket)
        parsed = read_ticket(ticket_path)
        
        for key, value in ticket.items():
            assert parsed.get(key) == value


class TestDeleteTicket:
    """Tests for delete_ticket function."""
    
    def test_soft_delete_moves_to_trash(self, tmp_path):
        """Test soft delete moves file to trash directory."""
        ticket_path = tmp_path / "repo" / "crash" / "C1-test.md"
        ticket_path.parent.mkdir(parents=True)
        ticket_path.write_text("# test")
        
        trash_dir = tmp_path / ".trash"
        
        delete_ticket(ticket_path, mode="soft", trash_dir=trash_dir)
        
        # Original should be gone
        assert not ticket_path.exists()
        # Trash should exist
        assert trash_dir.exists()
        # Should have a trashed file
        trashed_files = list(trash_dir.glob("*.md"))
        assert len(trashed_files) == 1
        assert "C1-test" in trashed_files[0].name
    
    def test_hard_delete_removes_file(self, tmp_path):
        """Test hard delete permanently removes file."""
        ticket_path = tmp_path / "repo" / "crash" / "C1-test.md"
        ticket_path.parent.mkdir(parents=True)
        ticket_path.write_text("# test")
        
        delete_ticket(ticket_path, mode="hard")
        
        assert not ticket_path.exists()
    
    def test_delete_nonexistent_raises_error(self, tmp_path):
        """Test deleting non-existent file raises error."""
        ticket_path = tmp_path / "nonexistent.md"
        
        with pytest.raises(FileNotFoundError):
            delete_ticket(ticket_path, mode="hard")
    
    def test_invalid_delete_mode_raises_error(self, tmp_path):
        """Test invalid delete mode raises error."""
        ticket_path = tmp_path / "test.md"
        ticket_path.write_text("# test")
        
        with pytest.raises(ValueError, match="Invalid delete mode"):
            delete_ticket(ticket_path, mode="invalid")
        
        # File should still exist
        assert ticket_path.exists()


# =============================================================================
# Listing and Scanning Tests
# =============================================================================

class TestListTickets:
    """Tests for list_tickets function."""
    
    def test_list_all_tickets(self, tmp_path):
        """Test listing all tickets without filters."""
        # Create tickets in different repos
        dir1 = tmp_path / "repo1" / "crash"
        dir1.mkdir(parents=True)
        (dir1 / "C1-issue1.md").write_text("# test1")
        (dir1 / "C2-issue2.md").write_text("# test2")
        
        dir2 = tmp_path / "repo2" / "feature"
        dir2.mkdir(parents=True)
        (dir2 / "F1-feature.md").write_text("# test3")
        
        results = list_tickets(tmp_path)
        
        assert len(results) == 3
    
    def test_list_tickets_with_repo_filter(self, tmp_path):
        """Test listing tickets filtered by repo."""
        dir1 = tmp_path / "ejacklab" / "api" / "crash"
        dir1.mkdir(parents=True)
        (dir1 / "C1-issue.md").write_text("# test1")
        
        dir2 = tmp_path / "ejacklab" / "web" / "security"
        dir2.mkdir(parents=True)
        (dir2 / "S1-security.md").write_text("# test2")
        
        results = list_tickets(tmp_path, repo="ejacklab/api")
        
        assert len(results) == 1
        assert "C1" in results[0].name
    
    def test_list_tickets_with_category_filter(self, tmp_path):
        """Test listing tickets filtered by category."""
        dir1 = tmp_path / "ejacklab" / "api" / "crash"
        dir1.mkdir(parents=True)
        (dir1 / "C1-issue.md").write_text("# test1")
        
        dir2 = tmp_path / "ejacklab" / "api" / "feature"
        dir2.mkdir(parents=True)
        (dir2 / "F1-feature.md").write_text("# test2")
        
        results = list_tickets(tmp_path, repo="ejacklab/api", category="crash")
        
        assert len(results) == 1
        assert "C1" in results[0].name
    
    def test_list_tickets_with_both_filters(self, tmp_path):
        """Test listing tickets with both repo and category filters."""
        dir1 = tmp_path / "ejacklab" / "api" / "crash"
        dir1.mkdir(parents=True)
        (dir1 / "C1-issue.md").write_text("# test1")
        
        dir2 = tmp_path / "ejacklab" / "api" / "feature"
        dir2.mkdir(parents=True)
        (dir2 / "F1-feature.md").write_text("# test2")
        
        dir3 = tmp_path / "ejacklab" / "web" / "crash"
        dir3.mkdir(parents=True)
        (dir3 / "C2-other.md").write_text("# test3")
        
        results = list_tickets(tmp_path, repo="ejacklab/api", category="crash")
        
        assert len(results) == 1
        assert "C1" in results[0].name
    
    def test_list_tickets_empty_directory(self, tmp_path):
        """Test listing tickets in empty directory."""
        results = list_tickets(tmp_path)
        assert results == []
    
    def test_list_tickets_nonexistent_directory(self, tmp_path):
        """Test listing tickets in non-existent directory."""
        nonexistent = tmp_path / "nonexistent"
        results = list_tickets(nonexistent)
        assert results == []


class TestScanAllTickets:
    """Tests for scan_all_tickets function."""
    
    def test_scan_multiple_repos(self, tmp_path):
        """Test scanning tickets across multiple repos."""
        # Create tickets in different repos
        dir1 = tmp_path / "ejacklab" / "api" / "crash"
        dir1.mkdir(parents=True)
        write_ticket(dir1 / "C1-segfault.md", SAMPLE_TICKETS[0])
        
        dir2 = tmp_path / "ejacklab" / "web" / "security"
        dir2.mkdir(parents=True)
        write_ticket(dir2 / "S1-sql-injection.md", SAMPLE_TICKETS[1])
        
        dir3 = tmp_path / "ejacklab" / "ui" / "feature"
        dir3.mkdir(parents=True)
        write_ticket(dir3 / "F1-dark-mode.md", SAMPLE_TICKETS[2])
        
        results = scan_all_tickets(tmp_path)
        
        assert len(results) == 3
        
        # Check all tickets were parsed
        ids = {ticket["id"] for _, ticket in results}
        assert ids == {"C1", "S1", "F1"}
    
    def test_scan_skips_trash_directory(self, tmp_path):
        """Test that scan skips .trash directory."""
        # Create active ticket
        dir1 = tmp_path / "repo" / "crash"
        dir1.mkdir(parents=True)
        write_ticket(dir1 / "C1-active.md", SAMPLE_TICKETS[0])
        
        # Create trashed ticket
        trash_dir = tmp_path / ".trash"
        trash_dir.mkdir(parents=True)
        (trash_dir / "C2-trashed.md").write_text("---\nid: C2\n---\n\n## Description\nTrashed")
        
        results = scan_all_tickets(tmp_path)
        
        assert len(results) == 1
        assert results[0][1]["id"] == "C1"
    
    def test_scan_returns_path_and_ticket(self, tmp_path):
        """Test that scan returns both path and parsed ticket."""
        dir1 = tmp_path / "repo" / "crash"
        dir1.mkdir(parents=True)
        write_ticket(dir1 / "C1-test.md", SAMPLE_TICKETS[0])
        
        results = scan_all_tickets(tmp_path)
        
        assert len(results) == 1
        path, ticket = results[0]
        assert isinstance(path, Path)
        assert isinstance(ticket, dict)
        assert ticket["id"] == "C1"
    
    def test_scan_handles_corrupt_files(self, tmp_path):
        """Test that scan handles corrupt/invalid files gracefully."""
        dir1 = tmp_path / "repo" / "crash"
        dir1.mkdir(parents=True)
        
        # Valid ticket
        write_ticket(dir1 / "C1-valid.md", SAMPLE_TICKETS[0])
        
        # Invalid ticket (corrupt YAML)
        (dir1 / "C2-corrupt.md").write_text("not valid markdown at all")
        
        results = scan_all_tickets(tmp_path)
        
        # Should only return the valid ticket
        assert len(results) == 1
        assert results[0][1]["id"] == "C1"
    
    def test_scan_empty_directory(self, tmp_path):
        """Test scanning empty directory."""
        results = scan_all_tickets(tmp_path)
        assert results == []


# =============================================================================
# Integration Tests
# =============================================================================

class TestIntegration:
    """Integration tests combining multiple operations."""
    
    def test_create_read_update_delete_workflow(self, tmp_path):
        """Test complete CRUD workflow."""
        ticket_path = tmp_path / "repo" / "crash" / "C1-test-issue.md"
        ticket = SAMPLE_TICKETS[0]
        
        # Create
        write_ticket(ticket_path, ticket)
        assert ticket_path.exists()
        
        # Read
        read_back = read_ticket(ticket_path)
        assert read_back is not None
        assert read_back["id"] == "C1"
        assert read_back["title"] == ticket["title"]
        
        # Update (overwrite)
        updated_ticket = dict(ticket)
        updated_ticket["status"] = "in_progress"
        updated_ticket["assignee"] = "new-dev"
        write_ticket(ticket_path, updated_ticket)
        
        # Verify update
        read_updated = read_ticket(ticket_path)
        assert read_updated["status"] == "in_progress"
        assert read_updated["assignee"] == "new-dev"
        
        # Delete
        trash_dir = tmp_path / ".trash"
        delete_ticket(ticket_path, mode="soft", trash_dir=trash_dir)
        
        # Verify deleted
        assert not ticket_path.exists()
        assert len(list(trash_dir.glob("*.md"))) == 1
    
    def test_multiple_tickets_same_repo(self, tmp_path):
        """Test handling multiple tickets in same repo."""
        base = tmp_path / "ejacklab" / "api"
        
        # Write multiple tickets (C1 and H1 are both in ejacklab/api)
        for ticket in [SAMPLE_TICKETS[0], SAMPLE_TICKETS[3]]:  # C1 and H1
            category_dir = base / ticket["category"]
            category_dir.mkdir(parents=True, exist_ok=True)
            path = category_dir / f"{ticket['id']}-test.md"
            write_ticket(path, ticket)
        
        # List all tickets for this repo
        tickets = list_tickets(tmp_path, repo="ejacklab/api")
        assert len(tickets) >= 2  # C1 and H1 are in ejacklab/api


# =============================================================================
# Sample Markdown Output
# =============================================================================

def test_sample_markdown_output():
    """Generate and display sample markdown output for one complete ticket."""
    ticket = {
        "id": "C1",
        "title": "CORS Wildcard Issue",
        "description": "The API allows wildcard CORS origins in production environments.",
        "repo": "ejacklab/open-dsearch",
        "category": "security",
        "severity": "high",
        "status": "open",
        "assignee": None,
        "fix": None,
        "tags": ["cors", "security"],
        "references": [],
        "created": "2026-03-18T10:00:00Z",
        "updated": "2026-03-18T10:00:00Z",
    }
    
    md = ticket_to_markdown(ticket)
    
    # Verify expected format
    assert md.startswith("---\n")
    assert "---\n\n## Description" in md
    assert "id: C1" in md
    assert "title: CORS Wildcard Issue" in md
    assert "## Description\nThe API allows wildcard CORS origins" in md
    
    # Print sample output (visible in verbose test runs)
    print("\n" + "=" * 60)
    print("SAMPLE MARKDOWN OUTPUT:")
    print("=" * 60)
    print(md)
    print("=" * 60)
