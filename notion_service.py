"""
Notion Service Module - Notion AI Integration

This module provides comprehensive functionality for interacting with Notion API,
including page and database retrieval, content management, and error handling.
"""

import logging
from typing import List, Dict, Optional, Any
from notion_client import Client
from notion_client.errors import APIResponseError, RequestTimeoutError
import time
from config.ai_config import get_config
from config.errors import NotionServiceError, ConfigurationError

logger = logging.getLogger(__name__)


class NotionService:
    """Service class for Notion API operations with comprehensive functionality."""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize Notion service with API key."""
        if not api_key:
            config = get_config()
            api_key = config.get('notion_api_key')
            
        if not api_key:
            raise ConfigurationError("Notion API key not found in configuration")
            
        self.client = Client(auth=api_key)
        self.max_retries = 3
        self.retry_delay = 1  # seconds
    
    def _retry_on_failure(self, func, *args, **kwargs):
        """Retry wrapper for API calls with exponential backoff."""
        for attempt in range(self.max_retries):
            try:
                return func(*args, **kwargs)
            except (APIResponseError, RequestTimeoutError) as e:
                if attempt == self.max_retries - 1:
                    logger.error(f"Final attempt failed for {func.__name__}: {str(e)}")
                    raise NotionServiceError(f"Notion API error after {self.max_retries} attempts: {str(e)}")
                
                wait_time = self.retry_delay * (2 ** attempt)
                logger.warning(f"Attempt {attempt + 1} failed for {func.__name__}, retrying in {wait_time}s: {str(e)}")
                time.sleep(wait_time)
            except Exception as e:
                logger.error(f"Unexpected error in {func.__name__}: {str(e)}")
                raise NotionServiceError(f"Unexpected error: {str(e)}")
    
    def get_accessible_pages(self, page_size: int = 100) -> List[Dict[str, Any]]:
        """
        Retrieve all accessible pages with proper pagination.
        
        Args:
            page_size: Number of pages to retrieve per request (max 100)
            
        Returns:
            List of page dictionaries with id, title, last_edited_time, and url
        """
        def _search_pages(start_cursor=None):
            return self.client.search(
                filter={"property": "object", "value": "page"},
                page_size=min(page_size, 100),
                start_cursor=start_cursor
            )
        
        try:
            all_pages = []
            has_more = True
            next_cursor = None
            
            while has_more:
                response = self._retry_on_failure(_search_pages, next_cursor)
                
                for page in response.get('results', []):
                    # Extract page information
                    page_info = {
                        'id': page['id'],
                        'title': self._extract_page_title(page),
                        'last_edited_time': page.get('last_edited_time', ''),
                        'url': page.get('url', ''),
                        'created_time': page.get('created_time', ''),
                        'archived': page.get('archived', False)
                    }
                    all_pages.append(page_info)
                
                has_more = response.get('has_more', False)
                next_cursor = response.get('next_cursor')
                
                # Safety check to prevent infinite loops
                if len(all_pages) > 10000:
                    logger.warning("Retrieved over 10,000 pages, stopping pagination")
                    break
            
            logger.info(f"Retrieved {len(all_pages)} accessible pages")
            return all_pages
            
        except Exception as e:
            logger.error(f"Error retrieving accessible pages: {str(e)}")
            raise NotionServiceError(f"Failed to retrieve pages: {str(e)}")
    
    def get_accessible_databases(self, page_size: int = 100) -> List[Dict[str, Any]]:
        """
        Retrieve all accessible databases with metadata.
        
        Args:
            page_size: Number of databases to retrieve per request (max 100)
            
        Returns:
            List of database dictionaries with id, title, description, properties, and entry_count
        """
        def _search_databases(start_cursor=None):
            return self.client.search(
                filter={"property": "object", "value": "database"},
                page_size=min(page_size, 100),
                start_cursor=start_cursor
            )
        
        try:
            all_databases = []
            has_more = True
            next_cursor = None
            
            while has_more:
                response = self._retry_on_failure(_search_databases, next_cursor)
                
                for database in response.get('results', []):
                    # Get entry count for this database
                    entry_count = self._get_database_entry_count(database['id'])
                    
                    # Extract database information
                    db_info = {
                        'id': database['id'],
                        'title': self._extract_database_title(database),
                        'description': self._extract_database_description(database),
                        'properties': database.get('properties', {}),
                        'entry_count': entry_count,
                        'created_time': database.get('created_time', ''),
                        'last_edited_time': database.get('last_edited_time', ''),
                        'url': database.get('url', ''),
                        'archived': database.get('archived', False)
                    }
                    all_databases.append(db_info)
                
                has_more = response.get('has_more', False)
                next_cursor = response.get('next_cursor')
                
                # Safety check to prevent infinite loops
                if len(all_databases) > 1000:
                    logger.warning("Retrieved over 1,000 databases, stopping pagination")
                    break
            
            logger.info(f"Retrieved {len(all_databases)} accessible databases")
            return all_databases
            
        except Exception as e:
            logger.error(f"Error retrieving accessible databases: {str(e)}")
            raise NotionServiceError(f"Failed to retrieve databases: {str(e)}")
    
    def get_page_content(self, page_id: str, include_children: bool = True) -> str:
        """
        Retrieve complete page content with recursive block retrieval.
        
        Args:
            page_id: The ID of the page to retrieve
            include_children: Whether to recursively retrieve child blocks
            
        Returns:
            Complete page content as formatted text
        """
        try:
            # Get page metadata
            page = self._retry_on_failure(self.client.pages.retrieve, page_id)
            
            # Extract page title
            title = self._extract_page_title(page)
            content_parts = [f"# {title}\n"]
            
            # Get page blocks recursively
            if include_children:
                blocks_content = self._get_blocks_content(page_id)
                content_parts.append(blocks_content)
            
            full_content = "\n".join(content_parts)
            logger.info(f"Retrieved content for page {page_id} ({len(full_content)} characters)")
            return full_content
            
        except Exception as e:
            logger.error(f"Error retrieving page content for {page_id}: {str(e)}")
            raise NotionServiceError(f"Failed to retrieve page content: {str(e)}")
    
    def _get_blocks_content(self, block_id: str, level: int = 0) -> str:
        """
        Recursively retrieve and format block content.
        
        Args:
            block_id: The ID of the parent block/page
            level: Current nesting level for formatting
            
        Returns:
            Formatted text content of all blocks
        """
        def _list_blocks(start_cursor=None):
            return self.client.blocks.children.list(
                block_id=block_id,
                start_cursor=start_cursor,
                page_size=100
            )
        
        try:
            content_parts = []
            has_more = True
            next_cursor = None
            
            while has_more:
                response = self._retry_on_failure(_list_blocks, next_cursor)
                
                for block in response.get('results', []):
                    block_content = self._format_block_content(block, level)
                    if block_content:
                        content_parts.append(block_content)
                    
                    # Recursively get child blocks if they exist
                    if block.get('has_children', False):
                        child_content = self._get_blocks_content(block['id'], level + 1)
                        if child_content:
                            content_parts.append(child_content)
                
                has_more = response.get('has_more', False)
                next_cursor = response.get('next_cursor')
            
            return "\n".join(content_parts)
            
        except Exception as e:
            logger.error(f"Error retrieving blocks for {block_id}: {str(e)}")
            return f"[Error retrieving content: {str(e)}]"
    
    def _format_block_content(self, block: Dict[str, Any], level: int = 0) -> str:
        """
        Format individual block content based on block type.
        
        Args:
            block: Block object from Notion API
            level: Nesting level for indentation
            
        Returns:
            Formatted text representation of the block
        """
        block_type = block.get('type', 'unsupported')
        indent = "  " * level
        
        try:
            if block_type == 'paragraph':
                text = self._extract_rich_text(block['paragraph'].get('rich_text', []))
                return f"{indent}{text}" if text else ""
            
            elif block_type == 'heading_1':
                text = self._extract_rich_text(block['heading_1'].get('rich_text', []))
                return f"{indent}# {text}" if text else ""
            
            elif block_type == 'heading_2':
                text = self._extract_rich_text(block['heading_2'].get('rich_text', []))
                return f"{indent}## {text}" if text else ""
            
            elif block_type == 'heading_3':
                text = self._extract_rich_text(block['heading_3'].get('rich_text', []))
                return f"{indent}### {text}" if text else ""
            
            elif block_type == 'bulleted_list_item':
                text = self._extract_rich_text(block['bulleted_list_item'].get('rich_text', []))
                return f"{indent}- {text}" if text else ""
            
            elif block_type == 'numbered_list_item':
                text = self._extract_rich_text(block['numbered_list_item'].get('rich_text', []))
                return f"{indent}1. {text}" if text else ""
            
            elif block_type == 'to_do':
                text = self._extract_rich_text(block['to_do'].get('rich_text', []))
                checked = "✓" if block['to_do'].get('checked', False) else "☐"
                return f"{indent}{checked} {text}" if text else ""
            
            elif block_type == 'toggle':
                text = self._extract_rich_text(block['toggle'].get('rich_text', []))
                return f"{indent}▶ {text}" if text else ""
            
            elif block_type == 'code':
                text = self._extract_rich_text(block['code'].get('rich_text', []))
                language = block['code'].get('language', '')
                return f"{indent}```{language}\n{text}\n```" if text else ""
            
            elif block_type == 'quote':
                text = self._extract_rich_text(block['quote'].get('rich_text', []))
                return f"{indent}> {text}" if text else ""
            
            elif block_type == 'callout':
                text = self._extract_rich_text(block['callout'].get('rich_text', []))
                icon = block['callout'].get('icon', {})
                icon_text = ""
                if icon.get('type') == 'emoji':
                    icon_text = icon.get('emoji', '')
                return f"{indent}{icon_text} {text}" if text else ""
            
            elif block_type == 'divider':
                return f"{indent}---"
            
            else:
                # For unsupported block types, try to extract any text content
                for key in block.keys():
                    if isinstance(block[key], dict) and 'rich_text' in block[key]:
                        text = self._extract_rich_text(block[key]['rich_text'])
                        if text:
                            return f"{indent}[{block_type}] {text}"
                return f"{indent}[{block_type} block]"
                
        except Exception as e:
            logger.warning(f"Error formatting block {block.get('id', 'unknown')}: {str(e)}")
            return f"{indent}[Error formatting {block_type} block]"
    
    def _extract_rich_text(self, rich_text_array: List[Dict[str, Any]]) -> str:
        """
        Extract plain text from Notion rich text array.
        
        Args:
            rich_text_array: Array of rich text objects from Notion API
            
        Returns:
            Plain text string
        """
        if not rich_text_array:
            return ""
        
        text_parts = []
        for text_obj in rich_text_array:
            if text_obj.get('type') == 'text':
                text_parts.append(text_obj['text']['content'])
            elif text_obj.get('type') == 'mention':
                # Handle mentions (pages, users, etc.)
                mention = text_obj.get('mention', {})
                if mention.get('type') == 'page':
                    text_parts.append(f"[Page: {mention.get('page', {}).get('id', 'Unknown')}]")
                else:
                    text_parts.append(text_obj.get('plain_text', ''))
            else:
                text_parts.append(text_obj.get('plain_text', ''))
        
        return "".join(text_parts)
    
    def _extract_page_title(self, page: Dict[str, Any]) -> str:
        """Extract title from page object."""
        properties = page.get('properties', {})
        
        # Look for title property
        for prop_name, prop_value in properties.items():
            if prop_value.get('type') == 'title':
                title_array = prop_value.get('title', [])
                if title_array:
                    return self._extract_rich_text(title_array)
        
        # Fallback to page ID if no title found
        return f"Untitled Page ({page.get('id', 'Unknown')})"
    
    def _extract_database_title(self, database: Dict[str, Any]) -> str:
        """Extract title from database object."""
        title_array = database.get('title', [])
        if title_array:
            return self._extract_rich_text(title_array)
        return f"Untitled Database ({database.get('id', 'Unknown')})"
    
    def _extract_database_description(self, database: Dict[str, Any]) -> str:
        """Extract description from database object."""
        description_array = database.get('description', [])
        if description_array:
            return self._extract_rich_text(description_array)
        return ""
    
    def _get_database_entry_count(self, database_id: str) -> int:
        """
        Get the number of entries in a database.
        
        Args:
            database_id: The ID of the database
            
        Returns:
            Number of entries in the database
        """
        try:
            def _query_database():
                return self.client.databases.query(
                    database_id=database_id,
                    page_size=1  # We only need the count, not the actual data
                )
            
            response = self._retry_on_failure(_query_database)
            
            # If we can get the first page, we can estimate the total
            # Note: Notion API doesn't provide direct count, so we do a minimal query
            if response.get('has_more', False):
                # If there are more results, we need to paginate to get accurate count
                # For performance, we'll do a quick estimation
                return self._count_database_entries_full(database_id)
            else:
                # If no more results, count the current results
                return len(response.get('results', []))
                
        except Exception as e:
            logger.warning(f"Could not get entry count for database {database_id}: {str(e)}")
            return 0
    
    def _count_database_entries_full(self, database_id: str) -> int:
        """
        Get accurate count of database entries by paginating through all results.
        
        Args:
            database_id: The ID of the database
            
        Returns:
            Exact number of entries in the database
        """
        try:
            total_count = 0
            has_more = True
            next_cursor = None
            
            while has_more and total_count < 10000:  # Safety limit
                def _query_database(start_cursor=None):
                    return self.client.databases.query(
                        database_id=database_id,
                        start_cursor=start_cursor,
                        page_size=100
                    )
                
                response = self._retry_on_failure(_query_database, next_cursor)
                total_count += len(response.get('results', []))
                has_more = response.get('has_more', False)
                next_cursor = response.get('next_cursor')
            
            return total_count
            
        except Exception as e:
            logger.warning(f"Error counting database entries for {database_id}: {str(e)}")
            return 0
    
    def create_page_in_database(
        self, 
        database_id: str, 
        title: str, 
        content: str, 
        properties: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a new page in the specified database with rich text support.
        
        Args:
            database_id: The ID of the target database
            title: The title for the new page
            content: The content to add to the page (supports markdown-like formatting)
            properties: Additional properties to set on the page
            
        Returns:
            The ID of the created page
        """
        try:
            # Validate database exists and is accessible
            self._validate_database_exists(database_id)
            
            # Prepare page properties
            page_properties = self._prepare_page_properties(database_id, title, properties)
            
            # Create the page
            def _create_page():
                return self.client.pages.create(
                    parent={"database_id": database_id},
                    properties=page_properties
                )
            
            page = self._retry_on_failure(_create_page)
            page_id = page['id']
            
            # Add content to the page if provided
            if content and content.strip():
                self._add_content_to_page(page_id, content)
            
            logger.info(f"Successfully created page '{title}' in database {database_id}")
            return page_id
            
        except Exception as e:
            logger.error(f"Error creating page '{title}' in database {database_id}: {str(e)}")
            raise NotionServiceError(f"Failed to create page: {str(e)}")
    
    def update_page_content(self, page_id: str, content: str) -> None:
        """
        Update existing page content with content validation.
        
        Args:
            page_id: The ID of the page to update
            content: The new content for the page (supports markdown-like formatting)
        """
        try:
            # Validate page exists and is accessible
            self._validate_page_exists(page_id)
            
            # Clear existing content blocks (except title)
            self._clear_page_content(page_id)
            
            # Add new content
            if content and content.strip():
                self._add_content_to_page(page_id, content)
            
            logger.info(f"Successfully updated content for page {page_id}")
            
        except Exception as e:
            logger.error(f"Error updating page content for {page_id}: {str(e)}")
            raise NotionServiceError(f"Failed to update page content: {str(e)}")
    
    def update_page_properties(self, page_id: str, properties: Dict[str, Any]) -> None:
        """
        Update page properties (title, database fields, etc.).
        
        Args:
            page_id: The ID of the page to update
            properties: Dictionary of properties to update
        """
        try:
            # Validate page exists
            self._validate_page_exists(page_id)
            
            # Prepare properties for update
            formatted_properties = self._format_properties_for_update(properties)
            
            def _update_page():
                return self.client.pages.update(
                    page_id=page_id,
                    properties=formatted_properties
                )
            
            self._retry_on_failure(_update_page)
            logger.info(f"Successfully updated properties for page {page_id}")
            
        except Exception as e:
            logger.error(f"Error updating page properties for {page_id}: {str(e)}")
            raise NotionServiceError(f"Failed to update page properties: {str(e)}")
    
    def add_comment_to_page(self, page_id: str, comment: str) -> str:
        """
        Add a comment to a page.
        
        Args:
            page_id: The ID of the page to comment on
            comment: The comment text
            
        Returns:
            The ID of the created comment
        """
        try:
            # Validate page exists
            self._validate_page_exists(page_id)
            
            def _create_comment():
                return self.client.comments.create(
                    parent={"page_id": page_id},
                    rich_text=[{
                        "type": "text",
                        "text": {"content": comment}
                    }]
                )
            
            comment_obj = self._retry_on_failure(_create_comment)
            comment_id = comment_obj['id']
            
            logger.info(f"Successfully added comment to page {page_id}")
            return comment_id
            
        except Exception as e:
            logger.error(f"Error adding comment to page {page_id}: {str(e)}")
            raise NotionServiceError(f"Failed to add comment: {str(e)}")
    
    def _validate_database_exists(self, database_id: str) -> None:
        """Validate that a database exists and is accessible."""
        try:
            def _retrieve_database():
                return self.client.databases.retrieve(database_id)
            
            self._retry_on_failure(_retrieve_database)
        except Exception as e:
            raise NotionServiceError(f"Database {database_id} not found or not accessible: {str(e)}")
    
    def _validate_page_exists(self, page_id: str) -> None:
        """Validate that a page exists and is accessible."""
        try:
            def _retrieve_page():
                return self.client.pages.retrieve(page_id)
            
            self._retry_on_failure(_retrieve_page)
        except Exception as e:
            raise NotionServiceError(f"Page {page_id} not found or not accessible: {str(e)}")
    
    def _prepare_page_properties(
        self, 
        database_id: str, 
        title: str, 
        additional_properties: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Prepare page properties for creation based on database schema.
        
        Args:
            database_id: The target database ID
            title: The page title
            additional_properties: Additional properties to set
            
        Returns:
            Formatted properties dictionary
        """
        try:
            # Get database schema to understand required properties
            def _get_database():
                return self.client.databases.retrieve(database_id)
            
            database = self._retry_on_failure(_get_database)
            database_properties = database.get('properties', {})
            
            # Initialize properties with title
            properties = {}
            
            # Find the title property and set it
            title_property = None
            for prop_name, prop_config in database_properties.items():
                if prop_config.get('type') == 'title':
                    title_property = prop_name
                    break
            
            if title_property:
                properties[title_property] = {
                    "title": [{"type": "text", "text": {"content": title}}]
                }
            else:
                # If no title property found, use a default name
                properties["Name"] = {
                    "title": [{"type": "text", "text": {"content": title}}]
                }
            
            # Add additional properties if provided
            if additional_properties:
                for prop_name, prop_value in additional_properties.items():
                    if prop_name in database_properties:
                        prop_type = database_properties[prop_name].get('type')
                        formatted_value = self._format_property_value(prop_value, prop_type)
                        if formatted_value is not None:
                            properties[prop_name] = formatted_value
            
            return properties
            
        except Exception as e:
            logger.error(f"Error preparing page properties: {str(e)}")
            raise NotionServiceError(f"Failed to prepare page properties: {str(e)}")
    
    def _format_property_value(self, value: Any, property_type: str) -> Optional[Dict[str, Any]]:
        """
        Format a property value based on its type for Notion API.
        
        Args:
            value: The value to format
            property_type: The Notion property type
            
        Returns:
            Formatted property value or None if invalid
        """
        try:
            if property_type == 'rich_text':
                if isinstance(value, str):
                    return {"rich_text": [{"type": "text", "text": {"content": value}}]}
                elif isinstance(value, list):
                    return {"rich_text": value}
            
            elif property_type == 'number':
                if isinstance(value, (int, float)):
                    return {"number": value}
                elif isinstance(value, str) and value.replace('.', '').replace('-', '').isdigit():
                    return {"number": float(value)}
            
            elif property_type == 'select':
                if isinstance(value, str):
                    return {"select": {"name": value}}
                elif isinstance(value, dict) and 'name' in value:
                    return {"select": value}
            
            elif property_type == 'multi_select':
                if isinstance(value, list):
                    return {"multi_select": [{"name": item} if isinstance(item, str) else item for item in value]}
                elif isinstance(value, str):
                    return {"multi_select": [{"name": value}]}
            
            elif property_type == 'date':
                if isinstance(value, str):
                    return {"date": {"start": value}}
                elif isinstance(value, dict):
                    return {"date": value}
            
            elif property_type == 'checkbox':
                return {"checkbox": bool(value)}
            
            elif property_type == 'url':
                if isinstance(value, str) and (value.startswith('http') or value.startswith('https')):
                    return {"url": value}
            
            elif property_type == 'email':
                if isinstance(value, str) and '@' in value:
                    return {"email": value}
            
            elif property_type == 'phone_number':
                if isinstance(value, str):
                    return {"phone_number": value}
            
            # If we can't format the value, log a warning and return None
            logger.warning(f"Could not format value '{value}' for property type '{property_type}'")
            return None
            
        except Exception as e:
            logger.warning(f"Error formatting property value: {str(e)}")
            return None
    
    def _add_content_to_page(self, page_id: str, content: str) -> None:
        """
        Add formatted content to a page by parsing markdown-like text.
        
        Args:
            page_id: The ID of the page to add content to
            content: The content to add (supports basic markdown formatting)
        """
        try:
            # Parse content into blocks
            blocks = self._parse_content_to_blocks(content)
            
            # Add blocks to page in batches (Notion API has limits)
            batch_size = 100
            for i in range(0, len(blocks), batch_size):
                batch = blocks[i:i + batch_size]
                
                def _append_blocks():
                    return self.client.blocks.children.append(
                        block_id=page_id,
                        children=batch
                    )
                
                self._retry_on_failure(_append_blocks)
            
            logger.info(f"Added {len(blocks)} content blocks to page {page_id}")
            
        except Exception as e:
            logger.error(f"Error adding content to page {page_id}: {str(e)}")
            raise NotionServiceError(f"Failed to add content to page: {str(e)}")
    
    def _parse_content_to_blocks(self, content: str) -> List[Dict[str, Any]]:
        """
        Parse text content into Notion blocks with basic markdown support.
        
        Args:
            content: Text content with markdown-like formatting
            
        Returns:
            List of Notion block objects
        """
        blocks = []
        lines = content.split('\n')
        
        i = 0
        while i < len(lines):
            line = lines[i].rstrip()
            
            # Skip empty lines
            if not line:
                i += 1
                continue
            
            # Headers
            if line.startswith('### '):
                blocks.append({
                    "object": "block",
                    "type": "heading_3",
                    "heading_3": {
                        "rich_text": [{"type": "text", "text": {"content": line[4:]}}]
                    }
                })
            elif line.startswith('## '):
                blocks.append({
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {
                        "rich_text": [{"type": "text", "text": {"content": line[3:]}}]
                    }
                })
            elif line.startswith('# '):
                blocks.append({
                    "object": "block",
                    "type": "heading_1",
                    "heading_1": {
                        "rich_text": [{"type": "text", "text": {"content": line[2:]}}]
                    }
                })
            
            # Bullet points
            elif line.startswith('- ') or line.startswith('* '):
                blocks.append({
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {
                        "rich_text": [{"type": "text", "text": {"content": line[2:]}}]
                    }
                })
            
            # Numbered lists
            elif line.lstrip().startswith(('1. ', '2. ', '3. ', '4. ', '5. ', '6. ', '7. ', '8. ', '9. ')):
                text = line.lstrip()
                # Find the first space after the number and dot
                space_index = text.find(' ')
                if space_index > 0:
                    content_text = text[space_index + 1:]
                    blocks.append({
                        "object": "block",
                        "type": "numbered_list_item",
                        "numbered_list_item": {
                            "rich_text": [{"type": "text", "text": {"content": content_text}}]
                        }
                    })
                else:
                    # Fallback to paragraph if parsing fails
                    blocks.append({
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [{"type": "text", "text": {"content": line}}]
                        }
                    })
            
            # Code blocks
            elif line.startswith('```'):
                # Find the end of the code block
                code_lines = []
                language = line[3:].strip() if len(line) > 3 else ""
                i += 1
                
                while i < len(lines) and not lines[i].startswith('```'):
                    code_lines.append(lines[i])
                    i += 1
                
                code_content = '\n'.join(code_lines)
                blocks.append({
                    "object": "block",
                    "type": "code",
                    "code": {
                        "rich_text": [{"type": "text", "text": {"content": code_content}}],
                        "language": language if language else "plain text"
                    }
                })
            
            # Quotes
            elif line.startswith('> '):
                blocks.append({
                    "object": "block",
                    "type": "quote",
                    "quote": {
                        "rich_text": [{"type": "text", "text": {"content": line[2:]}}]
                    }
                })
            
            # Dividers
            elif line.strip() in ['---', '***', '___']:
                blocks.append({
                    "object": "block",
                    "type": "divider",
                    "divider": {}
                })
            
            # Regular paragraphs
            else:
                blocks.append({
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"type": "text", "text": {"content": line}}]
                    }
                })
            
            i += 1
        
        return blocks
    
    def _clear_page_content(self, page_id: str) -> None:
        """
        Clear all content blocks from a page (preserving the page itself).
        
        Args:
            page_id: The ID of the page to clear
        """
        try:
            # Get all blocks in the page
            def _list_blocks(start_cursor=None):
                return self.client.blocks.children.list(
                    block_id=page_id,
                    start_cursor=start_cursor,
                    page_size=100
                )
            
            has_more = True
            next_cursor = None
            blocks_to_delete = []
            
            while has_more:
                response = self._retry_on_failure(_list_blocks, next_cursor)
                
                for block in response.get('results', []):
                    blocks_to_delete.append(block['id'])
                
                has_more = response.get('has_more', False)
                next_cursor = response.get('next_cursor')
            
            # Delete blocks (Notion doesn't have batch delete, so we delete one by one)
            for block_id in blocks_to_delete:
                try:
                    def _delete_block():
                        return self.client.blocks.delete(block_id)
                    
                    self._retry_on_failure(_delete_block)
                except Exception as e:
                    logger.warning(f"Could not delete block {block_id}: {str(e)}")
            
            logger.info(f"Cleared {len(blocks_to_delete)} blocks from page {page_id}")
            
        except Exception as e:
            logger.warning(f"Error clearing page content for {page_id}: {str(e)}")
            # Don't raise an exception here as this is a cleanup operation
    
    def _format_properties_for_update(self, properties: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format properties for page update operations.
        
        Args:
            properties: Raw properties dictionary
            
        Returns:
            Formatted properties for Notion API
        """
        formatted = {}
        
        for prop_name, prop_value in properties.items():
            # If the value is already formatted for Notion API, use it as-is
            if isinstance(prop_value, dict) and any(key in prop_value for key in [
                'title', 'rich_text', 'number', 'select', 'multi_select', 
                'date', 'checkbox', 'url', 'email', 'phone_number'
            ]):
                formatted[prop_name] = prop_value
            else:
                # Try to auto-format based on value type
                if isinstance(prop_value, str):
                    # Assume rich text for string values
                    formatted[prop_name] = {
                        "rich_text": [{"type": "text", "text": {"content": prop_value}}]
                    }
                elif isinstance(prop_value, (int, float)):
                    formatted[prop_name] = {"number": prop_value}
                elif isinstance(prop_value, bool):
                    formatted[prop_name] = {"checkbox": prop_value}
                elif isinstance(prop_value, list):
                    # Assume multi-select for list values
                    formatted[prop_name] = {
                        "multi_select": [{"name": str(item)} for item in prop_value]
                    }
        
        return formatted


# Convenience functions for backward compatibility and ease of use
def get_accessible_pages() -> List[Dict[str, Any]]:
    """Get all accessible pages using default configuration."""
    service = NotionService()
    return service.get_accessible_pages()


def get_accessible_databases() -> List[Dict[str, Any]]:
    """Get all accessible databases using default configuration."""
    service = NotionService()
    return service.get_accessible_databases()


def get_page_content(page_id: str) -> str:
    """Get complete page content using default configuration."""
    service = NotionService()
    return service.get_page_content(page_id)


def create_page_in_database(database_id: str, title: str, content: str, properties: Optional[Dict[str, Any]] = None) -> str:
    """Create a new page in database using default configuration."""
    service = NotionService()
    return service.create_page_in_database(database_id, title, content, properties)


def update_page_content(page_id: str, content: str) -> None:
    """Update page content using default configuration."""
    service = NotionService()
    return service.update_page_content(page_id, content)