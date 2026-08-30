"""
This is a roboust email extraction module for HTML text. 
It provides functions to extract email addresses from raw HTML, handling unicode-escape sequences and 
filtering out false positives based on TLDs and domain patterns. 
Additionally, it includes functionality to decode Cloudflare email obfuscation.

"""

import re

# --- Unicode-escape cleanup ---
UNICODE_ESCAPE_RE = re.compile(r'\\u([0-9a-fA-F]{4})')

def decode_unicode_escapes(text: str) -> str:
    """Turn literal '\\u003E'-style sequences back into real characters."""
    return UNICODE_ESCAPE_RE.sub(lambda m: chr(int(m.group(1), 16)), text)


# --- Filename false-positive filtering ---
NON_EMAIL_TLDS = {
    # images
    "png", "jpg", "jpeg", "gif", "svg", "webp", "ico", "bmp", "tiff", "tif", "avif", "heic",
    # fonts
    "woff", "woff2", "ttf", "eot", "otf",
    # other common web asset extensions that can precede a "domain-shaped" tail
    "css", "js", "map", "json", "xml", "webmanifest",
}

# --- Mock domain false-positive filtering ---
NON_EMAIL_DOMAINS = {
    "example", "company", "yourdomain", "test", "domain", "sentry.wixpress.com", "sentry-next.wixpress.com",
    "sentry-next.wixpress", "sentry.wixpress", "google.com", "sentry.io", "sentry", "google", "cssentry.creativesites.sk",
    "cssentry", "creativesites.sk", "doe.com", "ingest.sentry.io", "mysite.com"
}
DIMENSION_RE = re.compile(r'^\d+x\d*$', re.IGNORECASE)  # matches "2x", "3x", "144x144", etc.


# --- Core pattern (named groups so filtering can inspect the domain/tld separately) ---
EMAIL_RE = re.compile(
    r'(?P<local>[a-zA-Z0-9._%+-]+)@(?P<domain>[a-zA-Z0-9.-]+)\.(?P<tld>[a-zA-Z]{2,})'
)


def extractEmails(html_text: str, initSet: set = set()) -> list[str]:
    """
    Extract unique, valid-looking email addresses from raw HTML text.

    Applies unicode-escape cleanup first, then filters out matches whose
    "TLD" is actually a file extension or whose domain looks like image
    dimensions. Returns addresses deduped case-insensitively, keeping the
    first-seen casing, in order of first appearance.
    """
    text = decode_unicode_escapes(html_text)
    found = []

    for m in EMAIL_RE.finditer(text):
        tld = m.group('tld').lower()
        if tld in NON_EMAIL_TLDS:
            continue
        domain = m.group('domain').lower()
        if domain in NON_EMAIL_DOMAINS:
            continue
        first_label = m.group('domain').split('.')[0]
        if DIMENSION_RE.match(first_label):
            continue
        found.append(m.group(0))

    seen = set(email.lower() for email in initSet)  # start with any pre-seeded emails
    unique = []
    for email in found:
        key = email.lower()
        if key not in seen:
            seen.add(key)
            unique.append(email)
    return unique


# --- Cloudflare email-obfuscation decoding (separate mechanism, unaffected by the above) ---
CF_RE = re.compile(r'data-cfemail="([a-f0-9]+)"')

def decode_cfemail(encoded: str) -> str:
    r = int(encoded[:2], 16)
    return ''.join(chr(int(encoded[i:i + 2], 16) ^ r) for i in range(2, len(encoded), 2))

def extractCloudflareEmails(html_text: str) -> list[str]:
    return [decode_cfemail(m) for m in CF_RE.findall(html_text)]