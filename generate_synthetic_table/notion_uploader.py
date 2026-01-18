"""Notion Database uploader for QA results."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
import yaml

try:
    from notion_client import Client
except ImportError:
    Client = None


def _load_notion_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """Load Notion configuration from gemini_keys.yaml or specified path."""
    if config_path is None:
        # Default path
        base_dir = Path(__file__).parent.parent
        config_path = base_dir / "apis" / "gemini_keys.yaml"
    else:
        config_path = Path(config_path)
    
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    
    return config


class NotionUploader:
    """Upload QA results to Notion Database."""
    
    # Domain -> Database ID 매핑
    DOMAIN_DATABASE_MAP = {
        "public": None,      # 설정 파일에서 로드
        "insurance": None,
        "academic": None,
        "business": None,
        "finance": None,
        "medical": None,
    }
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize Notion client with API key from config."""
        if Client is None:
            raise ImportError(
                "notion-client package is not installed. "
                "Install it with: pip install notion-client"
            )
        
        config = _load_notion_config(config_path)
        
        # Get Notion API key
        self.api_key = config.get("notion_key")
        if not self.api_key:
            raise ValueError("notion_key not found in config file")
        
        # Get database IDs from config
        notion_databases = config.get("notion_databases", {})
        for domain, db_id in notion_databases.items():
            if domain in self.DOMAIN_DATABASE_MAP:
                self.DOMAIN_DATABASE_MAP[domain] = db_id
        
        # Initialize Notion client
        self.client = Client(auth=self.api_key)
        
        # Cache for database properties
        self._db_properties_cache: Dict[str, Dict] = {}
    
    def get_database_id(self, domain: str) -> str:
        """Get database ID for the given domain."""
        db_id = self.DOMAIN_DATABASE_MAP.get(domain.lower())
        if not db_id:
            raise ValueError(
                f"No database ID configured for domain '{domain}'. "
                f"Please add 'notion_databases.{domain}' to your config file."
            )
        return db_id
    
    def _get_database_properties(self, database_id: str) -> Dict[str, str]:
        """Get database properties and their types using direct API call. Cached."""
        if database_id in self._db_properties_cache:
            return self._db_properties_cache[database_id]
        
        # Use direct httpx call to ensure we get properties
        # (notion-client may not return properties for some database types)
        url = f"https://api.notion.com/v1/databases/{database_id}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Notion-Version": "2022-06-28",
        }
        response = httpx.get(url, headers=headers)
        db = response.json()
        
        props = {}
        for name, prop in db.get("properties", {}).items():
            props[name] = prop.get("type")
        
        self._db_properties_cache[database_id] = props
        return props
    
    def _find_title_property(self, db_properties: Dict[str, str]) -> Optional[str]:
        """Find the title property name in database."""
        for name, prop_type in db_properties.items():
            if prop_type == "title":
                return name
        return None  # No title property found
    
    def _ensure_database_properties(self, database_id: str) -> str:
        """Ensure the database has required properties, create them if missing.
        Returns the title property name."""
        db_properties = self._get_database_properties(database_id)
        title_prop = self._find_title_property(db_properties)
        
        # Check if we need to add properties
        properties_to_add = {}
        
        # Title property is required - if missing, add "Name"
        if not title_prop:
            properties_to_add["Name"] = {"title": {}}
            title_prop = "Name"
        
        # Add properties for individual QA rows
        if "Domain" not in db_properties:
            properties_to_add["Domain"] = {"select": {}}
        
        if "Image" not in db_properties:
            properties_to_add["Image"] = {"rich_text": {}}
        
        if "Question" not in db_properties:
            properties_to_add["Question"] = {"rich_text": {}}
        
        if "Answer" not in db_properties:
            properties_to_add["Answer"] = {"rich_text": {}}
        
        if "Type" not in db_properties:
            properties_to_add["Type"] = {"select": {}}
        
        if "Count" not in db_properties:
            properties_to_add["Count"] = {"number": {}}
        
        if "Token" not in db_properties:
            properties_to_add["Token"] = {"number": {}}
        
        if "Provider" not in db_properties:
            properties_to_add["Provider"] = {"select": {}}
        
        if "reasoning_annotation" not in db_properties:
            properties_to_add["reasoning_annotation"] = {"rich_text": {}}
        
        if "context" not in db_properties:
            properties_to_add["context"] = {"rich_text": {}}
        
        if properties_to_add:
            print(f"  📝 Adding missing properties: {list(properties_to_add.keys())}")
            self.client.databases.update(
                database_id=database_id,
                properties=properties_to_add
            )
            # Clear cache to refresh
            if database_id in self._db_properties_cache:
                del self._db_properties_cache[database_id]
        
        return title_prop
    
    def upload_qa_result(
        self,
        domain: str,
        image_path: str,
        qa_results: List[Dict],
        table_summary: Optional[str] = None,
        additional_properties: Optional[Dict] = None,
        token_usage: int = 0,
        provider: str = "unknown",
    ) -> Dict[str, Any]:
        """
        Upload QA results to Notion database.
        Each QA pair is uploaded as a separate row.
        
        Args:
            domain: Domain name (public, insurance, etc.)
            image_path: Path to the source image
            qa_results: List of QA pairs
            table_summary: Optional table summary
            additional_properties: Optional additional properties to add
            token_usage: Total tokens used for QA generation
            provider: LLM provider used (openai, gemini, gemini_pool, claude, vllm)
            
        Returns:
            Summary of created pages
        """
        database_id = self.get_database_id(domain)
        
        # Ensure database has required properties and get title property name
        title_prop_name = self._ensure_database_properties(database_id)
        
        # Get current database properties to check types
        db_properties = self._get_database_properties(database_id)
        
        # Helper function to build property value based on actual type
        def build_property_value(prop_name: str, value: str, preferred_type: str = "select") -> Dict:
            """Build property value based on actual property type in database."""
            if prop_name not in db_properties:
                # Property doesn't exist, use preferred type
                if preferred_type == "select":
                    return {"select": {"name": value}}
                else:
                    return {"rich_text": [{"text": {"content": value[:2000]}}]}
            
            # db_properties stores type directly as string value
            actual_type = db_properties[prop_name]
            if actual_type == "select":
                return {"select": {"name": value}}
            elif actual_type == "multi_select":
                return {"multi_select": [{"name": value}]}
            else:
                # Default to rich_text for any other type
                return {"rich_text": [{"text": {"content": value[:2000]}}]}
        
        # Get just the filename (not full path)
        image_filename = Path(image_path).name
        
        # Calculate tokens per QA (distribute evenly)
        num_qa = len(qa_results)
        tokens_per_qa = token_usage // num_qa if num_qa > 0 and token_usage > 0 else 0
        
        created_pages = []
        
        # Create a separate row for each QA pair
        for i, qa in enumerate(qa_results, 1):
            question = qa.get("question", qa.get("Q", ""))
            answer = qa.get("answer", qa.get("A", ""))
            qa_type = qa.get("type", "unknown")
            reasoning_annotation = qa.get("reasoning_annotation", "")
            context = qa.get("context", "")
            
            # Build page properties for this QA
            properties = {
                title_prop_name: {
                    "title": [
                        {
                            "text": {
                                "content": Path(image_path).stem
                            }
                        }
                    ]
                },
                "Count": {
                    "number": i
                },
                "Domain": {
                    "select": {
                        "name": domain.capitalize()
                    }
                },
                "Image": {
                    "rich_text": [
                        {
                            "text": {
                                "content": image_filename
                            }
                        }
                    ]
                },
                "Question": {
                    "rich_text": [
                        {
                            "text": {
                                "content": question[:2000]  # Notion limit
                            }
                        }
                    ]
                },
                "Answer": {
                    "rich_text": [
                        {
                            "text": {
                                "content": answer[:2000]  # Notion limit
                            }
                        }
                    ]
                },
                "Type": build_property_value("Type", qa_type, "select"),
                "Token": {
                    "number": tokens_per_qa
                },
                "Provider": build_property_value("Provider", provider, "select"),
                "reasoning_annotation": {
                    "rich_text": [
                        {
                            "text": {
                                "content": reasoning_annotation[:2000] if reasoning_annotation else ""
                            }
                        }
                    ]
                },
                "context": {
                    "rich_text": [
                        {
                            "text": {
                                "content": context[:2000] if context else ""
                            }
                        }
                    ]
                },
            }
            
            # Create the page (row)
            response = self.client.pages.create(
                parent={"database_id": database_id},
                properties=properties,
            )
            created_pages.append(response)
        
        return {
            "created_count": len(created_pages),
            "pages": created_pages
        }
    
    def upload_batch_results(
        self,
        domain: str,
        results: List[Dict],
        verbose: bool = True,
        provider: str = "unknown",
    ) -> Dict[str, Any]:
        """
        Upload multiple QA results to Notion database.
        
        Args:
            domain: Domain name
            results: List of result dictionaries with image_path, qa_results, etc.
            verbose: Print progress messages
            provider: LLM provider used
            
        Returns:
            Summary of upload results
        """
        success_count = 0
        failed_count = 0
        total_qa_count = 0
        failed_items = []
        
        for i, result in enumerate(results, 1):
            image_path = result.get("image_path", result.get("name", f"unknown_{i}"))
            qa_results = result.get("qa_results", [])
            table_summary = result.get("table_summary")
            token_usage = result.get("token_usage", 0)
            
            if not qa_results:
                if verbose:
                    print(f"⏭️  Skipping {image_path} (no QA results)")
                continue
            
            try:
                upload_result = self.upload_qa_result(
                    domain=domain,
                    image_path=image_path,
                    qa_results=qa_results,
                    table_summary=table_summary,
                    token_usage=token_usage,
                    provider=provider,
                )
                created_count = upload_result.get("created_count", 0)
                total_qa_count += created_count
                success_count += 1
                if verbose:
                    print(f"✅ [{i}/{len(results)}] Uploaded: {image_path} ({created_count} QA rows)")
            except Exception as e:
                failed_count += 1
                failed_items.append({"path": image_path, "error": str(e)})
                if verbose:
                    print(f"❌ [{i}/{len(results)}] Failed: {image_path} - {e}")
        
        return {
            "total": len(results),
            "success": success_count,
            "failed": failed_count,
            "total_qa_rows": total_qa_count,
            "failed_items": failed_items,
        }


def upload_to_notion(
    domain: str,
    results: List[Dict],
    config_path: Optional[str] = None,
    verbose: bool = True,
    provider: str = "unknown",
) -> Dict[str, Any]:
    """
    Convenience function to upload results to Notion.
    
    Args:
        domain: Domain name (public, insurance, etc.)
        results: List of result dictionaries
        config_path: Optional path to config file
        verbose: Print progress messages
        provider: LLM provider used
        
    Returns:
        Upload summary
    """
    uploader = NotionUploader(config_path=config_path)
    return uploader.upload_batch_results(domain, results, verbose=verbose, provider=provider)
