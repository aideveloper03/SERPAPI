"""
Contact Information Extractor
Extracts emails, phone numbers, social media links, and addresses
"""
import re
from typing import List, Dict, Set, Optional
import phonenumbers
from email_validator import validate_email, EmailNotValidError
from loguru import logger


class ContactExtractor:
    """Extract contact information from text and HTML"""
    
    def __init__(self):
        # Email regex
        self.email_pattern = re.compile(
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        )
        
        # Phone patterns for different formats
        self.phone_patterns = [
            # US formats
            re.compile(r'\+?1?[-.\s]?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})'),
            # International format
            re.compile(r'\+\d{1,3}[-.\s]?\d{1,4}[-.\s]?\d{1,4}[-.\s]?\d{1,9}'),
            # Generic
            re.compile(r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'),
        ]
        
        # Social media patterns
        self.social_patterns = {
            'facebook': re.compile(r'(?:https?://)?(?:www\.)?facebook\.com/[\w\-\.]+'),
            'twitter': re.compile(r'(?:https?://)?(?:www\.)?(?:twitter|x)\.com/[\w\-]+'),
            'linkedin': re.compile(r'(?:https?://)?(?:www\.)?linkedin\.com/(?:in|company)/[\w\-]+'),
            'instagram': re.compile(r'(?:https?://)?(?:www\.)?instagram\.com/[\w\-\.]+'),
            'youtube': re.compile(r'(?:https?://)?(?:www\.)?youtube\.com/(?:c|channel|user)/[\w\-]+'),
        }
        
        # Address pattern (basic)
        self.address_pattern = re.compile(
            r'\d+\s+[\w\s]+(?:street|st|avenue|ave|road|rd|highway|hwy|square|sq|trail|trl|drive|dr|court|ct|parkway|pkwy|circle|cir|boulevard|blvd)\b[,\s]+[\w\s]+[,\s]+[A-Z]{2}\s+\d{5}',
            re.IGNORECASE
        )
    
    def extract_all(self, text: str, html: str = "") -> Dict[str, any]:
        """
        Extract all contact information
        
        Returns:
            Dict with emails, phones, social_media, addresses
        """
        result = {
            'emails': self.extract_emails(text),
            'phones': self.extract_phones(text),
            'social_media': self.extract_social_media(text),
            'addresses': self.extract_addresses(text)
        }
        
        return result
    
    def extract_emails(self, text: str) -> List[str]:
        """Extract and validate email addresses"""
        emails = set()
        
        # Find all potential emails
        matches = self.email_pattern.findall(text)
        
        for email in matches:
            # Skip common false positives
            if any(ext in email.lower() for ext in ['.png', '.jpg', '.gif', '.css', '.js']):
                continue
            
            # Validate email
            try:
                valid = validate_email(email, check_deliverability=False)
                emails.add(valid.email)
            except EmailNotValidError:
                pass
        
        return sorted(list(emails))
    
    def extract_phones(self, text: str) -> List[str]:
        """Extract and validate phone numbers"""
        phones = set()
        
        # Try phonenumbers library for better extraction
        try:
            for match in phonenumbers.PhoneNumberMatcher(text, "US"):
                phones.add(phonenumbers.format_number(
                    match.number,
                    phonenumbers.PhoneNumberFormat.INTERNATIONAL
                ))
        except Exception as e:
            logger.debug(f"phonenumbers extraction error: {e}")
        
        # Fallback to regex patterns
        for pattern in self.phone_patterns:
            matches = pattern.findall(text)
            for match in matches:
                if isinstance(match, tuple):
                    phone = '-'.join(match)
                else:
                    phone = match
                
                # Basic validation
                digits = re.sub(r'\D', '', phone)
                if 10 <= len(digits) <= 15:
                    phones.add(phone)
        
        return sorted(list(phones))
    
    def extract_social_media(self, text: str) -> Dict[str, List[str]]:
        """Extract social media links"""
        social_media = {}
        
        for platform, pattern in self.social_patterns.items():
            matches = pattern.findall(text)
            if matches:
                social_media[platform] = list(set(matches))
        
        return social_media
    
    def extract_addresses(self, text: str) -> List[str]:
        """Extract physical addresses (US format)"""
        addresses = set()
        
        matches = self.address_pattern.findall(text)
        for match in matches:
            addresses.add(match.strip())
        
        return sorted(list(addresses))
    
    def extract_from_structured_data(self, structured_data: Dict) -> Dict[str, any]:
        """Extract contact info from structured data (JSON-LD, microdata)"""
        contacts = {
            'emails': [],
            'phones': [],
            'addresses': []
        }
        
        # Common structured data fields
        email_fields = ['email', 'contactEmail', 'emailAddress']
        phone_fields = ['telephone', 'phone', 'phoneNumber']
        address_fields = ['address', 'streetAddress', 'location']
        
        def search_dict(d, fields):
            """Recursively search dictionary for fields"""
            results = []
            if isinstance(d, dict):
                for key, value in d.items():
                    if key in fields:
                        if isinstance(value, str):
                            results.append(value)
                        elif isinstance(value, list):
                            results.extend([str(v) for v in value])
                    else:
                        results.extend(search_dict(value, fields))
            elif isinstance(d, list):
                for item in d:
                    results.extend(search_dict(item, fields))
            return results
        
        contacts['emails'] = search_dict(structured_data, email_fields)
        contacts['phones'] = search_dict(structured_data, phone_fields)
        contacts['addresses'] = search_dict(structured_data, address_fields)
        
        return contacts
