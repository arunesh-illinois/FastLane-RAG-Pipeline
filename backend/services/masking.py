'''
masked_text, mapping = mask_text(
    text: str,
    key: bytes,                 # secret for deterministic masking
    date_shift_days: int,       # shift all dates by a fixed offset
    doc_scope_id: str | None    # if provided, determinism is per-doc scope
)

restored_text = demask_text(
    masked_text: str,
    key: bytes,
    allow_categories: set[str]  # e.g., {"NAME"} — only these get restored
)
/<data>@$
dictionary input {
    Name,
    Phone,
    MRN,
    Email,
    Address
}
'''

import hmac
import re
import hashlib

hash_mapping = {}

deterministic_key = "this_is_my_secret_key".encode("utf-8")

PHONE_RE = re.compile(
    r"""(
        \(\d{3}\)\s?\d{3}[-]\d{4} |
        \d{3}[-]\d{3}[-]\d{4} |
        \+1\s\d{3}\s\d{3}\s\d{4}
    )""",
    re.VERBOSE
)

EMAIL_RE = re.compile(r"([A-Za-z0-9._+\-]+)@([A-Za-z0-9.\-]+\.[A-Za-z]{2,})")

def generate_deterministic_name_code(text):
    code_length = 6
    digest = hmac.new(deterministic_key, text.encode("utf-8"), hashlib.sha256).hexdigest().upper()
    masked_text = digest[:code_length]
    hash_mapping[masked_text] = text
    return f"{masked_text}"

def mask_phone(phone_str):
    digits = re.sub(r"\D", "", phone_str)  # remove non-digits
    masked_last4 = "0000"                  # or use HMAC to generate
    new_chars = list(phone_str)
    di = len(masked_last4) - 1
    for i in range(len(phone_str)-1, -1, -1):
        if di < 0:
            break
        if phone_str[i].isdigit():
            new_chars[i] = masked_last4[di]
            di -= 1
    masked_phone = "".join(new_chars)
    hash_mapping[masked_phone] = phone_str
    return masked_phone

def mask_name(name_str):
    return generate_deterministic_name_code(name_str)

def demask_name(masked_name_str):
    if masked_name_str in hash_mapping:
        return hash_mapping[masked_name_str]


def mask_email(email_str):
    match = EMAIL_RE.match(email_str)
    masked_email =""
    if match:
        email_name = match.group(1)
        email_domain = match.group(2)
        masked_email = generate_deterministic_name_code(email_name) + "@anon.example"
        hash_mapping[masked_email] = email_name
    return masked_email

if __name__ == '__main__':
    masked_name = mask_name("Arunesh")
    demasked_name = demask_name(masked_name)
    assert "Arunesh" == demasked_name

    print(mask_phone("(484) 982-0184"))
    print(mask_email("arunesh.kumar@gmail.com"))

